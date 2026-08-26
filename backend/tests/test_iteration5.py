"""Iteration 5 backend tests: /api/videos CRUD + auth playbook checks."""
import os
import re
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="session")
def creds():
    p = Path("/app/memory/test_credentials.md")
    if not p.exists():
        pytest.skip("missing test_credentials.md")
    c = p.read_text(encoding="utf-8")
    e = re.search(r'(?im)^\s*[-*]?\s*(?:\*\*)?Email(?:\*\*)?\s*:\s*`?([^`\s]+)', c)
    pw = re.search(r'(?im)^\s*[-*]?\s*(?:\*\*)?Password(?:\*\*)?\s*:\s*`?([^`\s]+)', c)
    if not e or not pw:
        pytest.skip("no creds")
    return {"email": e.group(1), "password": pw.group(1)}


@pytest.fixture(scope="session")
def client(creds):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=creds, timeout=30)
    if r.status_code != 200:
        pytest.fail(f"login failed {r.status_code}: {r.text[:300]}")
    assert "access_token" in s.cookies.get_dict(), f"cookies: {s.cookies.get_dict()}"
    return s


@pytest.fixture(scope="session")
def created_ids():
    return []


@pytest.fixture(scope="session", autouse=True)
def cleanup(client, created_ids):
    yield
    for vid in created_ids:
        client.delete(f"{API}/videos/{vid}", timeout=30)


# ---------- Auth ----------
class TestAuth:
    def test_login_sets_httponly_cookies(self, creds):
        s = requests.Session()
        r = s.post(f"{API}/auth/login", json=creds, timeout=30)
        assert r.status_code == 200
        raw = r.headers.get("set-cookie", "")
        assert "access_token" in raw and "HttpOnly" in raw, raw[:300]

    def test_me(self, client):
        r = client.get(f"{API}/auth/me", timeout=30)
        assert r.status_code == 200
        assert "email" in r.json()

    def test_videos_requires_auth(self):
        r = requests.get(f"{API}/videos", timeout=30)
        assert r.status_code in (401, 403), r.status_code


# ---------- Videos CRUD ----------
class TestVideos:
    def test_create_and_persist(self, client, created_ids):
        payload = {
            "title": "TEST_Reacao YouTube",
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "description": "TEST descricao",
            "components": ["Velocidade de reação", "Agilidade"],
        }
        r = client.post(f"{API}/videos", json=payload, timeout=30)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert isinstance(d.get("id"), str) and d["id"]
        created_ids.append(d["id"])
        assert d["title"] == payload["title"]
        assert d["components"] == payload["components"]

        g = client.get(f"{API}/videos", timeout=30)
        assert g.status_code == 200
        rows = g.json()
        assert all("_id" not in x for x in rows)
        match = [x for x in rows if x["id"] == d["id"]]
        assert len(match) == 1
        assert match[0]["url"] == payload["url"]
        assert match[0]["description"] == payload["description"]

    def test_filter_by_component(self, client, created_ids):
        vid = created_ids[0]
        r = client.get(f"{API}/videos", params={"component": "Velocidade de reação"}, timeout=30)
        assert r.status_code == 200
        assert vid in [x["id"] for x in r.json()]
        r2 = client.get(f"{API}/videos", params={"component": "Tático"}, timeout=30)
        assert r2.status_code == 200
        assert vid not in [x["id"] for x in r2.json()]

    def test_update_and_persist(self, client, created_ids):
        vid = created_ids[0]
        payload = {
            "title": "TEST_Atualizado",
            "url": "https://vimeo.com/76979871",
            "description": "TEST nova",
            "components": ["Tático"],
        }
        r = client.put(f"{API}/videos/{vid}", json=payload, timeout=30)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["title"] == "TEST_Atualizado"
        rows = client.get(f"{API}/videos", timeout=30).json()
        row = [x for x in rows if x["id"] == vid][0]
        assert row["title"] == "TEST_Atualizado"
        assert row["url"] == payload["url"]
        assert row["components"] == ["Tático"]

    def test_invalid_id_400(self, client):
        assert client.put(f"{API}/videos/not-an-oid", json={"title": "a", "url": "b"}, timeout=30).status_code == 400
        assert client.delete(f"{API}/videos/not-an-oid", timeout=30).status_code == 400

    def test_missing_id_404(self, client):
        r = client.put(f"{API}/videos/000000000000000000000000", json={"title": "a", "url": "b"}, timeout=30)
        assert r.status_code == 404

    def test_validation_422(self, client):
        r = client.post(f"{API}/videos", json={"title": "x"}, timeout=30)
        assert r.status_code == 422

    def test_delete_and_verify(self, client, created_ids):
        vid = created_ids.pop(0)
        r = client.delete(f"{API}/videos/{vid}", timeout=30)
        assert r.status_code == 200
        rows = client.get(f"{API}/videos", timeout=30).json()
        assert vid not in [x["id"] for x in rows]


# ---------- Reaction training data (BaseDados summary source) ----------
class TestReactionTraining:
    def test_rodrigo_has_sessions(self, client):
        gks = client.get(f"{API}/goalkeepers", timeout=30).json()
        rod = [g for g in gks if "Rodrigo" in g.get("name", "")]
        assert rod, "Rodrigo Prazeres not seeded"
        gid = rod[0]["id"]
        r = client.get(f"{API}/goalkeepers/{gid}/training", timeout=30)
        assert r.status_code == 200, r.text[:200]
        rows = r.json()
        assert len(rows) > 0
        assert all("best_ms" in x and "avg_ms" in x for x in rows)
