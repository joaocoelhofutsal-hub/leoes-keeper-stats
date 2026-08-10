"""Backend API tests for Leões Guarda-Redes app"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://leoes-keeper-stats.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "joaocoelhofutsal@gmail.com"
ADMIN_PASSWORD = "leoes2011"


@pytest.fixture(scope="session")
def client():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return s


# ---------- Auth ----------
def test_login_ok(client):
    r = client.get(f"{API}/auth/me")
    assert r.status_code == 200
    assert r.json()["email"] == ADMIN_EMAIL


def test_login_invalid():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong"})
    assert r.status_code == 401


def test_protected_no_cookie():
    r = requests.get(f"{API}/goalkeepers")
    assert r.status_code == 401


# ---------- Goalkeepers CRUD ----------
@pytest.fixture(scope="module")
def gk_id(client):
    r = client.post(f"{API}/goalkeepers", json={"name": "TEST_GK_Auto", "team": "Sub-15"})
    assert r.status_code == 200
    gid = r.json()["id"]
    yield gid
    client.delete(f"{API}/goalkeepers/{gid}")


def test_list_goalkeepers(client, gk_id):
    r = client.get(f"{API}/goalkeepers")
    assert r.status_code == 200
    names = [g["name"] for g in r.json()]
    assert "TEST_GK_Auto" in names


def test_update_goalkeeper(client, gk_id):
    r = client.put(f"{API}/goalkeepers/{gk_id}",
                   json={"name": "TEST_GK_Auto", "team": "Sub-17",
                         "strengths": "reflexos", "weaknesses": "saidas", "source": "Obs J4"})
    assert r.status_code == 200
    lst = client.get(f"{API}/goalkeepers").json()
    g = next(x for x in lst if x["id"] == gk_id)
    assert g["team"] == "Sub-17"
    assert g["strengths"] == "reflexos"


# ---------- Reports ----------
def _make_action(evaluation="verde", tech="Queda lateral", dist="3-6 m", zone="Corredor central"):
    return {
        "situation": "Remate", "zone": zone, "distance": dist, "finish_type": "Meia altura central",
        "technique": tech, "decisions": ["Encurtamento", "Enquadramento"], "followup": "GR recuperou",
        "evaluation": evaluation, "feedback": "", "notes": ""
    }


@pytest.fixture(scope="module")
def report_id(client, gk_id):
    payload = {
        "goalkeeper_id": gk_id, "goalkeeper_name": "TEST_GK_Auto", "team": "Sub-17",
        "session_number": "UT2", "opponent": "Benfica", "date": "2026-01-10",
        "competition": "Nacional", "result": "3-2", "coach_notes": "Bom jogo",
        "actions": [_make_action() for _ in range(4)],
        "offensive": {"passes_ok": 5, "passes_err": 2, "shots_ok": 1, "shots_err": 0, "repos_ok": 3, "repos_err": 1}
    }
    r = client.post(f"{API}/reports", json=payload)
    assert r.status_code == 200, r.text
    rid = r.json()["id"]
    yield rid
    client.delete(f"{API}/reports/{rid}")


def test_get_report_persisted(client, report_id):
    r = client.get(f"{API}/reports/{report_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["session_number"] == "UT2"
    assert len(data["actions"]) == 4
    assert data["offensive"]["passes_ok"] == 5


def test_gk_reports_list(client, gk_id, report_id):
    r = client.get(f"{API}/goalkeepers/{gk_id}/reports")
    assert r.status_code == 200
    ids = [x["id"] for x in r.json()]
    assert report_id in ids


# ---------- Profile / trends ----------
def test_profile_trends(client, gk_id, report_id):
    r = client.get(f"{API}/goalkeepers/{gk_id}/profile")
    assert r.status_code == 200
    p = r.json()
    assert p["total_reports"] >= 1
    assert p["total_actions"] >= 4
    assert p["top_technique"] == "Queda lateral"
    # 4 actions of same followup >= 3 -> trend exists
    assert isinstance(p["trends"], list)
    assert any("Seguimento" in t or "GR recuperou" in t for t in p["trends"])


# ---------- PDF ----------
def test_pdf_endpoint(client, report_id):
    r = client.get(f"{API}/reports/{report_id}/pdf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    cd = r.headers.get("content-disposition", "")
    assert "RI " in cd and ".pdf" in cd
    assert r.content[:4] == b"%PDF"


# ---------- Export ----------
def test_export(client):
    r = client.get(f"{API}/export")
    assert r.status_code == 200
    j = r.json()
    assert "goalkeepers" in j and "reports" in j
    # Ensure no _id
    for g in j["goalkeepers"]:
        assert "_id" not in g


# ---------- Logo ----------
def test_logo_get(client):
    r = client.get(f"{API}/settings/logo")
    assert r.status_code == 200
    assert "logo" in r.json()


def test_delete_report(client, gk_id):
    payload = {
        "goalkeeper_id": gk_id, "goalkeeper_name": "TEST_GK_Auto",
        "session_number": "DEL", "date": "2026-01-11", "actions": [], "offensive": {}
    }
    rid = client.post(f"{API}/reports", json=payload).json()["id"]
    r = client.delete(f"{API}/reports/{rid}")
    assert r.status_code == 200
    r2 = client.get(f"{API}/reports/{rid}")
    assert r2.status_code == 404
