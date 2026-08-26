"""Tests for iteration 4 - bulk exercises import, import-doc, PWA assets."""
import os
import io
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
ADMIN_EMAIL = "joaocoelhofutsal@gmail.com"
ADMIN_PASSWORD = "leoes2011"


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    return s


# ---------- Bulk exercises ----------
def test_bulk_exercises_with_components_and_guess(client):
    payload = {
        "items": [
            {"title": "TEST_bulk_A - Reação com luzes", "description": "estímulo visual reativo", "components": []},
            {"title": "TEST_bulk_B - Escada de agilidade", "description": "", "components": ["Agilidade"]},
            {"title": "TEST_bulk_C - Aquecimento dinâmico", "description": "", "components": []},
        ],
        "guess": True,
    }
    r = client.post(f"{API}/exercises/bulk", json=payload)
    assert r.status_code == 200, r.text
    assert r.json()["created"] == 3

    # Verify persistence + component guessing
    lst = client.get(f"{API}/exercises").json()
    by_title = {e["title"]: e for e in lst}
    assert "TEST_bulk_A - Reação com luzes" in by_title
    a = by_title["TEST_bulk_A - Reação com luzes"]
    assert "Velocidade de reação" in a["components"], a["components"]
    b = by_title["TEST_bulk_B - Escada de agilidade"]
    assert b["components"] == ["Agilidade"]  # explicit stays
    c = by_title["TEST_bulk_C - Aquecimento dinâmico"]
    assert "Ativação" in c["components"], c["components"]

    # Cleanup
    for t in ["TEST_bulk_A - Reação com luzes", "TEST_bulk_B - Escada de agilidade", "TEST_bulk_C - Aquecimento dinâmico"]:
        ex = by_title.get(t)
        if ex:
            client.delete(f"{API}/exercises/{ex['id']}")


def test_bulk_empty_titles_skipped(client):
    r = client.post(f"{API}/exercises/bulk", json={"items": [{"title": "  ", "description": "x"}], "guess": True})
    assert r.status_code == 200
    assert r.json()["created"] == 0


# ---------- import-doc ----------
def test_import_doc_pptx_without_libreoffice_returns_friendly_error(client):
    # Minimal fake pptx (not a valid ppt but python-pptx will fail; the ordering: python-pptx
    # runs first inside try/except and returns titles=[]; then checks soffice → since not installed → 400.
    # Build a real tiny pptx via python-pptx to reach the soffice check reliably.
    try:
        from pptx import Presentation
        prs = Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[0])
        slide.shapes.title.text = "TEST_slide_1"
        buf = io.BytesIO()
        prs.save(buf)
        buf.seek(0)
        files = {"file": ("test.pptx", buf.read(), "application/vnd.openxmlformats-officedocument.presentationml.presentation")}
    except Exception as e:
        pytest.skip(f"python-pptx not available: {e}")
    r = client.post(f"{API}/exercises/import-doc", files=files)
    # LibreOffice not installed -> friendly 400 in PT
    assert r.status_code == 400, r.text
    detail = r.json().get("detail", "")
    assert ".pptx" in detail or "PDF" in detail or "PowerPoint" in detail


def test_import_doc_pdf_creates_exercises(client):
    try:
        import pymupdf
    except Exception as e:
        pytest.skip(f"pymupdf missing: {e}")
    doc = pymupdf.open()
    for i in range(2):
        page = doc.new_page()
        page.insert_text((72, 72), f"TEST_pdf_ex_{i+1}", fontsize=20)
    pdf_bytes = doc.tobytes()
    doc.close()
    files = {"file": ("test.pdf", pdf_bytes, "application/pdf")}
    r = client.post(f"{API}/exercises/import-doc", files=files)
    assert r.status_code == 200, r.text
    assert r.json()["created"] == 2

    # Cleanup imported items (they'll have title like "Exercício N" since insert_text isn't a slide title)
    lst = client.get(f"{API}/exercises").json()
    for e in lst:
        if e["title"].startswith("Exercício ") and e.get("image", "").startswith("data:image/png"):
            # Only cleanup the two most recent
            client.delete(f"{API}/exercises/{e['id']}")


def test_import_doc_unsupported_format(client):
    files = {"file": ("bad.txt", b"hello", "text/plain")}
    r = client.post(f"{API}/exercises/import-doc", files=files)
    assert r.status_code == 400
    assert "PDF" in r.json().get("detail", "")


# ---------- PWA assets ----------
def test_manifest_json():
    r = requests.get(f"{BASE_URL}/manifest.json")
    assert r.status_code == 200, r.status_code
    j = r.json()
    assert j.get("theme_color", "").upper() == "#0C3B1E"
    icons = j.get("icons", [])
    assert any("192" in (i.get("sizes") or "") for i in icons)
    assert any("512" in (i.get("sizes") or "") for i in icons)


@pytest.mark.parametrize("path", ["/apple-touch-icon.png", "/icon-192.png", "/icon-512.png", "/sw.js"])
def test_pwa_static_assets(path):
    r = requests.get(f"{BASE_URL}{path}")
    assert r.status_code == 200, f"{path} -> {r.status_code}"
    assert len(r.content) > 0
