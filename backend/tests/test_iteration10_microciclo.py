"""Iteration 10 - Microciclo + Exercicios de Recurso modules.

Only deletes documents created by these tests (by returned id).
"""
import os
import re
import base64
import io
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

# 1x1 png
PNG_B64 = ("data:image/png;base64,"
           "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8AARAwMDAwMDAwMDAwMAA8AAv8B/1sAAAAASUVORK5CYII=")


@pytest.fixture(scope="session")
def credentials():
    p = Path("/app/memory/test_credentials.md")
    content = p.read_text(encoding="utf-8")
    email = re.search(r'(?im)^\s*[-*]?\s*(?:\*\*)?Email(?:\*\*)?\s*:\s*`?([^`\s]+)', content)
    pwd = re.search(r'(?im)^\s*[-*]?\s*(?:\*\*)?Password(?:\*\*)?\s*:\s*`?([^`\s]+)', content)
    if not email or not pwd:
        pytest.skip("credentials missing")
    return {"email": email.group(1), "password": pwd.group(1)}


@pytest.fixture(scope="session")
def client(credentials):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=credentials, timeout=30)
    if r.status_code != 200:
        pytest.fail(f"login failed {r.status_code}: {r.text[:300]}")
    cookies = r.cookies.get_dict()
    assert "access_token" in cookies, f"no httpOnly access_token cookie: {cookies}"
    return s


@pytest.fixture(scope="session")
def created():
    return {"mc": [], "rec": []}


@pytest.fixture(scope="session", autouse=True)
def cleanup(client, created):
    yield
    for mid in created["mc"]:
        client.delete(f"{API}/microcycles/{mid}", timeout=30)
    for rid in created["rec"]:
        client.delete(f"{API}/recurso-exercises/{rid}", timeout=30)


# ---------- Auth / security checks ----------
class TestAuthBasics:
    def test_me(self, client):
        r = client.get(f"{API}/auth/me", timeout=30)
        assert r.status_code == 200
        assert "email" in r.json()

    def test_microcycles_requires_auth(self):
        r = requests.get(f"{API}/microcycles", timeout=30)
        assert r.status_code in (401, 403), r.status_code

    def test_recurso_requires_auth(self):
        r = requests.get(f"{API}/recurso-exercises", timeout=30)
        assert r.status_code in (401, 403), r.status_code

    def test_bcrypt_hash_format(self, client, credentials):
        # verify stored admin hash format via mongo
        import subprocess
        out = subprocess.run(
            ["python", "-c",
             "import os,asyncio;from motor.motor_asyncio import AsyncIOMotorClient as C;"
             "from dotenv import dotenv_values as d;e=d('/app/backend/.env');"
             "c=C(e['MONGO_URL']);db=c[e['DB_NAME']];"
             "print(asyncio.get_event_loop().run_until_complete(db.users.find_one({},{'password_hash':1,'password':1})))"],
            capture_output=True, text=True)
        combined = out.stdout + out.stderr
        assert "$2b$" in combined or "$2a$" in combined, f"unexpected hash: {combined[:300]}"


# ---------- Microcycles CRUD ----------
class TestMicrocycles:
    def test_create_get_list(self, client, created):
        payload = {
            "name": "TEST_Microciclo QA",
            "days": {
                "Segunda": [{
                    "id": "t1", "number": "1", "duration": "20 min",
                    "components": ["Jogo Aéreo"], "video_ids": [], "images": [PNG_B64],
                    "notes": "TEST notas",
                }],
                "Quarta": [],
            },
        }
        r = client.post(f"{API}/microcycles", json=payload, timeout=60)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert "id" in data and isinstance(data["id"], str)
        mid = data["id"]
        created["mc"].append(mid)
        assert data["name"] == payload["name"]

        g = client.get(f"{API}/microcycles/{mid}", timeout=30)
        assert g.status_code == 200
        gd = g.json()
        assert gd["name"] == payload["name"]
        assert gd["days"]["Segunda"][0]["number"] == "1"
        assert gd["days"]["Segunda"][0]["duration"] == "20 min"
        assert gd["days"]["Segunda"][0]["notes"] == "TEST notas"
        assert gd["days"]["Segunda"][0]["images"] == [PNG_B64]
        assert "_id" not in gd

        l = client.get(f"{API}/microcycles", timeout=30)
        assert l.status_code == 200
        ids = [x["id"] for x in l.json()]
        assert mid in ids
        assert all("_id" not in x for x in l.json())

    def test_update(self, client, created):
        r = client.post(f"{API}/microcycles", json={"name": "TEST_MC upd", "days": {}}, timeout=30)
        mid = r.json()["id"]
        created["mc"].append(mid)
        newp = {"name": "TEST_MC upd v2", "days": {"Sexta": [{"id": "x", "number": "3", "duration": "45 min",
                                                             "components": ["Reação"], "video_ids": [],
                                                             "images": [], "notes": "n2"}]}}
        u = client.put(f"{API}/microcycles/{mid}", json=newp, timeout=30)
        assert u.status_code == 200, u.text[:300]
        g = client.get(f"{API}/microcycles/{mid}", timeout=30).json()
        assert g["name"] == "TEST_MC upd v2"
        assert g["days"]["Sexta"][0]["number"] == "3"

    def test_get_404(self, client):
        r = client.get(f"{API}/microcycles/000000000000000000000000", timeout=30)
        assert r.status_code == 404

    def test_get_invalid_id(self, client):
        r = client.get(f"{API}/microcycles/not-an-oid", timeout=30)
        assert r.status_code in (400, 404, 422), f"got {r.status_code}: {r.text[:200]}"

    def test_put_404(self, client):
        r = client.put(f"{API}/microcycles/000000000000000000000000",
                       json={"name": "x", "days": {}}, timeout=30)
        assert r.status_code == 404

    def test_pdf(self, client, created):
        payload = {"name": "TEST_MC pdf", "days": {"Segunda": [{
            "id": "p1", "number": "1", "duration": "30 min", "components": ["Jogo Aéreo"],
            "video_ids": [], "images": [PNG_B64], "notes": "pdf notas"}]}}
        mid = client.post(f"{API}/microcycles", json=payload, timeout=60).json()["id"]
        created["mc"].append(mid)
        r = client.get(f"{API}/microcycles/{mid}/pdf", timeout=90)
        assert r.status_code == 200, r.text[:300]
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:4] == b"%PDF"
        assert len(r.content) > 1000

    def test_pdf_requires_auth(self, client, created):
        mid = client.post(f"{API}/microcycles", json={"name": "TEST_MC pdfauth", "days": {}}, timeout=30).json()["id"]
        created["mc"].append(mid)
        r = requests.get(f"{API}/microcycles/{mid}/pdf", timeout=30)
        assert r.status_code in (401, 403), r.status_code

    def test_delete(self, client):
        mid = client.post(f"{API}/microcycles", json={"name": "TEST_MC del", "days": {}}, timeout=30).json()["id"]
        d = client.delete(f"{API}/microcycles/{mid}", timeout=30)
        assert d.status_code == 200
        assert client.get(f"{API}/microcycles/{mid}", timeout=30).status_code == 404


# ---------- Recurso exercises CRUD ----------
class TestRecurso:
    def test_create_and_list(self, client, created):
        payload = {"title": "TEST_Recurso A", "url": "https://example.com/v",
                   "description": "desc A", "components": ["Jogo Aéreo"]}
        r = client.post(f"{API}/recurso-exercises", json=payload, timeout=30)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        rid = d["id"]
        created["rec"].append(rid)
        assert d["title"] == payload["title"]
        rows = client.get(f"{API}/recurso-exercises", timeout=30).json()
        row = next((x for x in rows if x["id"] == rid), None)
        assert row is not None
        assert row["description"] == "desc A"
        assert row["url"] == payload["url"]
        assert "_id" not in row

    def test_filter_by_component(self, client, created):
        p1 = {"title": "TEST_Rec comp1", "url": "", "description": "", "components": ["Reação"]}
        p2 = {"title": "TEST_Rec comp2", "url": "", "description": "", "components": ["Jogo Aéreo"]}
        id1 = client.post(f"{API}/recurso-exercises", json=p1, timeout=30).json()["id"]
        id2 = client.post(f"{API}/recurso-exercises", json=p2, timeout=30).json()["id"]
        created["rec"] += [id1, id2]
        rows = client.get(f"{API}/recurso-exercises", params={"component": "Reação"}, timeout=30)
        assert rows.status_code == 200
        ids = [x["id"] for x in rows.json()]
        assert id1 in ids
        assert id2 not in ids

    def test_update_and_delete(self, client):
        rid = client.post(f"{API}/recurso-exercises",
                          json={"title": "TEST_Rec upd", "url": "", "description": "old",
                                "components": []}, timeout=30).json()["id"]
        u = client.put(f"{API}/recurso-exercises/{rid}",
                       json={"title": "TEST_Rec upd2", "url": "https://x.pt",
                             "description": "new", "components": ["Reação"]}, timeout=30)
        assert u.status_code == 200, u.text[:300]
        rows = client.get(f"{API}/recurso-exercises", timeout=30).json()
        row = next(x for x in rows if x["id"] == rid)
        assert row["title"] == "TEST_Rec upd2"
        assert row["description"] == "new"
        assert row["components"] == ["Reação"]

        d = client.delete(f"{API}/recurso-exercises/{rid}", timeout=30)
        assert d.status_code == 200
        rows = client.get(f"{API}/recurso-exercises", timeout=30).json()
        assert all(x["id"] != rid for x in rows)

    def test_put_404(self, client):
        r = client.put(f"{API}/recurso-exercises/000000000000000000000000",
                       json={"title": "x", "url": "", "description": "", "components": []}, timeout=30)
        assert r.status_code == 404

    def test_missing_title_validation(self, client):
        r = client.post(f"{API}/recurso-exercises", json={"url": "", "description": "",
                                                          "components": []}, timeout=30)
        assert r.status_code in (400, 422), f"got {r.status_code}"
