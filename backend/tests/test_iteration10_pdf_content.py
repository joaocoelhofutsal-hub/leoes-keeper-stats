"""Iteration 10 - verify microcycle PDF content (text + embedded image)."""
import os
import re
import zlib
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")).rstrip("/")
API = f"{BASE_URL}/api"

# valid 640x480 png generated at runtime
def _make_png_b64():
    import base64 as _b64
    import io as _io
    from PIL import Image as _Img
    im = _Img.new("RGB", (640, 480), (230, 235, 230))
    bio = _io.BytesIO()
    im.save(bio, format="PNG")
    return "data:image/png;base64," + _b64.b64encode(bio.getvalue()).decode()


PNG_B64 = _make_png_b64()
CORRUPT_PNG_B64 = ("data:image/png;base64,"
                   "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAAOUlEQVR42u3NMQEAAAgDoJnc/6dGhx6Q"
                   "gLYnAgQIECBAgAABAgQIECBAgAABAgQIECBAgAABAj4WHFcAAWzYNQEAAAAASUVORK5CYII=")


@pytest.fixture(scope="module")
def client():
    content = Path("/app/memory/test_credentials.md").read_text(encoding="utf-8")
    email = re.search(r'(?im)^\s*[-*]?\s*(?:\*\*)?Email(?:\*\*)?\s*:\s*`?([^`\s]+)', content).group(1)
    pwd = re.search(r'(?im)^\s*[-*]?\s*(?:\*\*)?Password(?:\*\*)?\s*:\s*`?([^`\s]+)', content).group(1)
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": pwd}, timeout=30)
    assert r.status_code == 200, r.text[:200]
    return s


def _pdf_text(content: bytes) -> str:
    out = []
    import base64 as _b64
    for m in re.finditer(rb"stream\r?\n(.*?)endstream", content, re.S):
        raw = m.group(1)
        candidates = [raw]
        # reportlab default: ASCII85 + Flate
        a85 = raw.strip()
        if a85.endswith(b"~>"):
            try:
                candidates.append(_b64.a85decode(a85, adobe=True))
            except Exception:
                pass
        for c in candidates:
            try:
                out.append(zlib.decompress(c).decode("latin-1", "ignore"))
                break
            except Exception:
                continue
        else:
            out.append(raw.decode("latin-1", "ignore"))
    return "\n".join(out)


def test_pdf_contains_day_notes_video_and_image(client):
    videos = client.get(f"{API}/videos", timeout=30).json()
    assert isinstance(videos, list) and videos, "no videos available to link"
    vid = videos[0]
    payload = {"name": "TEST_PDF_CONTENT", "days": {"Quarta": [{
        "id": "c1", "number": "7", "duration": "42 min",
        "components": ["Agilidade"], "video_ids": [vid["id"]],
        "images": [PNG_B64], "notes": "NotasPdfQa"}]}}
    mid = client.post(f"{API}/microcycles", json=payload, timeout=60).json()["id"]
    try:
        r = client.get(f"{API}/microcycles/{mid}/pdf", timeout=90)
        assert r.status_code == 200
        assert r.content[:4] == b"%PDF"
        txt = _pdf_text(r.content)
        assert "QUARTA" in txt, "day header missing in PDF"
        assert "42 min" in txt, "duration missing in PDF"
        assert "NotasPdfQa" in txt, "notes missing in PDF"
        assert "Agilidade" in txt, "component missing in PDF"
        # embedded image object present
        assert b"/Image" in r.content or b"/DCTDecode" in r.content or b"/FlateDecode" in r.content
        assert b"/Subtype /Image" in r.content or b"/Subtype/Image" in r.content, "no image XObject in PDF"
    finally:
        client.delete(f"{API}/microcycles/{mid}", timeout=30)


def test_pdf_with_corrupt_image_should_not_500(client):
    """Robustness: a corrupt/unsupported user-attached image must not break the whole PDF."""
    payload = {"name": "TEST_PDF_CORRUPT_IMG", "days": {"Segunda": [{
        "id": "c1", "number": "1", "duration": "10 min", "components": [],
        "video_ids": [], "images": [CORRUPT_PNG_B64], "notes": "n"}]}}
    mid = client.post(f"{API}/microcycles", json=payload, timeout=60).json()["id"]
    try:
        r = client.get(f"{API}/microcycles/{mid}/pdf", timeout=90)
        assert r.status_code == 200, f"PDF generation failed ({r.status_code}) due to one bad image"
        assert r.content[:4] == b"%PDF"
    finally:
        client.delete(f"{API}/microcycles/{mid}", timeout=30)
