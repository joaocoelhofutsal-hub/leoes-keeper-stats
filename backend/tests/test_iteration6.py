"""Iteration 6: Ações Soltas (loose actions) + Sub-jogos (subgames)."""
import os

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/") + "/api"

CREDS = {"email": "joaocoelhofutsal@gmail.com", "password": "leoes2011"}


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/auth/login", json=CREDS, timeout=30)
    if r.status_code != 200:
        pytest.fail(f"login failed {r.status_code}: {r.text[:300]}")
    assert "access_token" in s.cookies, f"no httpOnly cookie set: {s.cookies.get_dict()}"
    return s


@pytest.fixture(scope="module")
def gk(client):
    r = client.get(f"{BASE_URL}/goalkeepers", timeout=30)
    assert r.status_code == 200
    gks = r.json()
    assert len(gks) > 0
    target = next((g for g in gks if g["name"].lower().startswith("cintra")), gks[0])
    return target


# ---------- Auth basics ----------
class TestAuth:
    def test_me(self, client):
        r = client.get(f"{BASE_URL}/auth/me", timeout=30)
        assert r.status_code == 200
        assert r.json()["email"] == CREDS["email"]

    def test_unauthenticated_blocked(self):
        r = requests.get(f"{BASE_URL}/goalkeepers", timeout=30)
        assert r.status_code in (401, 403), r.status_code

    def test_bad_password(self):
        r = requests.post(f"{BASE_URL}/auth/login", json={"email": CREDS["email"], "password": "wrong-xyz"}, timeout=30)
        assert r.status_code in (401, 429), r.text[:200]


# ---------- Loose actions ----------
class TestLooseActions:
    created = []

    def test_list_initially(self, client, gk):
        r = client.get(f"{BASE_URL}/goalkeepers/{gk['id']}/loose-actions", timeout=30)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_add_loose_action_does_not_count_as_game(self, client, gk):
        gid = gk["id"]
        before = client.get(f"{BASE_URL}/goalkeepers/{gid}/profile", timeout=30).json()
        payload = {
            "situation": "Finalização de 1x1", "technique": "Barreirista",
            "distance": "6-9m", "decisions": ["Ocupar espaço"], "evaluation": "verde",
            "notes": "TEST_loose",
        }
        r = client.post(f"{BASE_URL}/goalkeepers/{gid}/loose-actions", json=payload, timeout=30)
        assert r.status_code == 200, r.text[:300]
        act = r.json()
        assert act.get("id")
        assert act["evaluation"] == "verde"
        assert act["decisions"] == ["Ocupar espaço"]
        type(self).created.append(act["id"])

        # persisted
        lst = client.get(f"{BASE_URL}/goalkeepers/{gid}/loose-actions", timeout=30).json()
        assert any(a["id"] == act["id"] for a in lst)

        after = client.get(f"{BASE_URL}/goalkeepers/{gid}/profile", timeout=30).json()
        assert after["total_actions"] == before["total_actions"] + 1, (before, after)
        assert after["total_reports"] == before["total_reports"], "loose action inflated report count"
        assert after["avg_actions_per_game"] == before["avg_actions_per_game"], "loose action changed avg actions/game"

    def test_loose_report_hidden_from_reports_list(self, client, gk):
        r = client.get(f"{BASE_URL}/goalkeepers/{gk['id']}/reports", timeout=30)
        assert r.status_code == 200
        assert all(not rep.get("loose") for rep in r.json())
        assert all(rep.get("session_number") != "Ações soltas" for rep in r.json())

    def test_goalkeeper_list_report_count_excludes_loose(self, client, gk):
        r = client.get(f"{BASE_URL}/goalkeepers", timeout=30)
        cur = next(g for g in r.json() if g["id"] == gk["id"])
        reports = client.get(f"{BASE_URL}/goalkeepers/{gk['id']}/reports", timeout=30).json()
        assert cur["report_count"] == len(reports)

    def test_delete_loose_action(self, client, gk):
        gid = gk["id"]
        payload = {"situation": "Finalização de 1x1", "technique": "Parede", "notes": "TEST_del"}
        aid = client.post(f"{BASE_URL}/goalkeepers/{gid}/loose-actions", json=payload, timeout=30).json()["id"]
        d = client.delete(f"{BASE_URL}/goalkeepers/{gid}/loose-actions/{aid}", timeout=30)
        assert d.status_code == 200
        lst = client.get(f"{BASE_URL}/goalkeepers/{gid}/loose-actions", timeout=30).json()
        assert not any(a["id"] == aid for a in lst)

    def test_delete_nonexistent_action_is_safe(self, client, gk):
        d = client.delete(f"{BASE_URL}/goalkeepers/{gk['id']}/loose-actions/does-not-exist", timeout=30)
        assert d.status_code in (200, 404)


# ---------- Subgames ----------
class TestSubgames:
    def test_get_empty_or_dict(self, client, gk):
        r = client.get(f"{BASE_URL}/goalkeepers/{gk['id']}/subgames", timeout=30)
        assert r.status_code == 200
        assert isinstance(r.json().get("subgames"), dict)

    def test_put_and_metric_computation(self, client, gk):
        gid = gk["id"]
        topic = {"id": "TEST-topic-1", "name": "TEST_Ocupação de espaço", "evaluation": "verde",
                 "field": "decisions", "value": "Ocupar espaço", "note": "n"}
        body = {"subgames": {"Defesa da baliza": [topic], "GR subido": []}}
        p = client.put(f"{BASE_URL}/goalkeepers/{gid}/subgames", json=body, timeout=30)
        assert p.status_code == 200, p.text[:300]

        g = client.get(f"{BASE_URL}/goalkeepers/{gid}/subgames", timeout=30)
        assert g.status_code == 200
        sg = g.json()["subgames"]
        assert "Defesa da baliza" in sg
        t = sg["Defesa da baliza"][0]
        assert t["name"] == topic["name"]
        assert t["evaluation"] == "verde"
        m = t["metric_result"]
        assert set(m) == {"count", "success", "pct"}
        assert m["count"] > 0, "expected real actions for 'Ocupar espaço'"
        assert 0 <= m["pct"] <= 100
        assert m["success"] <= m["count"]


    def test_metric_matches_real_actions_on_dedicated_gk(self, client):
        """Deterministic check: new GK + known loose actions -> exact metric."""
        gid = client.post(f"{BASE_URL}/goalkeepers", json={"name": "TEST_MetricGK", "team": "TEST"}, timeout=30).json()["id"]
        try:
            for ev in ["verde", "verde", "vermelho"]:
                client.post(f"{BASE_URL}/goalkeepers/{gid}/loose-actions",
                            json={"situation": "Remate", "decisions": ["Ocupar espaço"], "evaluation": ev}, timeout=30)
            client.post(f"{BASE_URL}/goalkeepers/{gid}/loose-actions",
                        json={"situation": "Remate", "decisions": ["Enquadramento"], "evaluation": "verde"}, timeout=30)
            body = {"subgames": {"Defesa da baliza": [
                {"id": "TEST-t1", "name": "TEST_dec", "field": "decisions", "value": "Ocupar espaço"},
                {"id": "TEST-t2", "name": "TEST_sit", "field": "situation", "value": "Remate"}]}}
            assert client.put(f"{BASE_URL}/goalkeepers/{gid}/subgames", json=body, timeout=30).status_code == 200
            sg = client.get(f"{BASE_URL}/goalkeepers/{gid}/subgames", timeout=30).json()["subgames"]
            m1 = sg["Defesa da baliza"][0]["metric_result"]
            assert m1 == {"count": 3, "success": 2, "pct": 67}, m1
            m2 = sg["Defesa da baliza"][1]["metric_result"]
            assert m2 == {"count": 4, "success": 3, "pct": 75}, m2
            # profile: loose-only GK must have 0 games but 4 actions
            prof = client.get(f"{BASE_URL}/goalkeepers/{gid}/profile", timeout=30).json()
            assert prof["total_reports"] == 0
            assert prof["total_actions"] == 4
            assert prof["avg_actions_per_game"] == 0
        finally:
            client.delete(f"{BASE_URL}/goalkeepers/{gid}", timeout=30)

    def test_topic_without_metric_returns_none(self, client, gk):
        gid = gk["id"]
        body = {"subgames": {"Bolas paradas": [{"id": "TEST-topic-2", "name": "TEST_sem metrica",
                                                "evaluation": "amarelo", "field": "", "value": ""}]}}
        assert client.put(f"{BASE_URL}/goalkeepers/{gid}/subgames", json=body, timeout=30).status_code == 200
        sg = client.get(f"{BASE_URL}/goalkeepers/{gid}/subgames", timeout=30).json()["subgames"]
        assert sg["Bolas paradas"][0]["metric_result"] is None

    def test_no_mongo_id_leak(self, client, gk):
        r = client.get(f"{BASE_URL}/goalkeepers/{gk['id']}/subgames", timeout=30)
        assert "_id" not in r.text

    def test_overwrite_replaces(self, client, gk):
        gid = gk["id"]
        assert client.put(f"{BASE_URL}/goalkeepers/{gid}/subgames", json={"subgames": {}}, timeout=30).status_code == 200
        sg = client.get(f"{BASE_URL}/goalkeepers/{gid}/subgames", timeout=30).json()["subgames"]
        assert sg == {}

    def test_unauthenticated_subgames_blocked(self, gk):
        r = requests.get(f"{BASE_URL}/goalkeepers/{gk['id']}/subgames", timeout=30)
        assert r.status_code in (401, 403)


# ---------- Regression on existing modules ----------
class TestRegressions:
    @pytest.mark.parametrize("path", [
        "/insights/general", "/videos", "/training-units", "/settings/logo", "/export",
    ])
    def test_endpoints_ok(self, client, path):
        r = client.get(f"{BASE_URL}{path}", timeout=60)
        assert r.status_code == 200, f"{path} -> {r.status_code} {r.text[:200]}"

    def test_profile_shape(self, client, gk):
        r = client.get(f"{BASE_URL}/goalkeepers/{gk['id']}/profile", timeout=30)
        assert r.status_code == 200
        d = r.json()
        for k in ["total_reports", "total_actions", "avg_actions_per_game", "style", "trends"]:
            assert k in d, k
