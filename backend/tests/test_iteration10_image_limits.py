"""Iteration 10 - size limits for base64 images stored inside microcycle docs."""
import base64
import io
import os
import re
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values
from PIL import Image

frontend_env = dotenv_values("/app/frontend/.env")
API = (os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")).rstrip("/") + "/api"


@pytest.fixture(scope="module")
def client():
    content = Path("/app/memory/test_credentials.md").read_text(encoding="utf-8")
    email = re.search(r'(?im)^\s*[-*]?\s*(?:\*\*)?Email(?:\*\*)?\s*:\s*`?([^`\s]+)', content).group(1)
    pwd = re.search(r'(?im)^\s*[-*]?\s*(?:\*\*)?Password(?:\*\*)?\s*:\s*`?([^`\s]+)', content).group(1)
    s = requests.Session()
    s.post(f"{API}/auth/login", json={"email": email, "password": pwd}, timeout=30).raise_for_status()
    return s


def _photo_b64(px):
    """JPEG noise image ~ realistic phone photo size."""
    import random
    im = Image.new("RGB", (px, px))
    im.putdata([(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
                for _ in range(px * px)])
    bio = io.BytesIO()
    im.save(bio, format="JPEG", quality=90)
    return "data:image/jpeg;base64," + base64.b64encode(bio.getvalue()).decode()


def test_large_photo_payload(client):
    """A handful of phone-sized photos must either save or fail gracefully (not 500)."""
    photo = _photo_b64(1800)  # ~ several MB base64
    size_mb = len(photo) / 1024 / 1024
    imgs = [photo] * 3
    payload = {"name": "TEST_big_images", "days": {"Segunda": [{
        "id": "b1", "number": "1", "duration": "20 min", "components": [],
        "video_ids": [], "images": imgs, "notes": "n"}]}}
    total = size_mb * len(imgs)
    print(f"\nsingle image base64 = {size_mb:.2f} MB; payload ~{total:.2f} MB")
    r = client.post(f"{API}/microcycles", json=payload, timeout=180)
    print(f"POST /microcycles status={r.status_code} body={r.text[:200]}")
    mid = None
    try:
        if r.status_code == 200:
            mid = r.json()["id"]
            g = client.get(f"{API}/microcycles/{mid}", timeout=180)
            assert g.status_code == 200
            assert len(g.json()["days"]["Segunda"][0]["images"]) == 3
            p = client.get(f"{API}/microcycles/{mid}/pdf", timeout=180)
            print(f"PDF status={p.status_code} size={len(p.content)}")
            assert p.status_code == 200, "PDF generation failed for large photos"
        else:
            assert r.status_code < 500, f"server error {r.status_code} for large image payload"
    finally:
        if mid:
            client.delete(f"{API}/microcycles/{mid}", timeout=60)
