"""Iteration 8 backend tests:
- Sub-jogos cross metric (field2/value2 in AND)
- Manual benchmark GK (benchmark_gk_id)
- References CRUD (/api/references)
- Auth playbook checks (bcrypt, httpOnly cookies, CORS credentials, lockout)
"""
import os
import re
import uuid
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/") + "/api"

SUCCESS_EVALS = ("verde", "cinzenta")


@pytest.fixture(scope="session")
def creds():
    p = Path("/app/memory/test_credentials.md")
    if not p.exists():
        pytest.skip("missing credentials file")
    c = p.read_text(encoding="utf-8")
    e = re.search(r"(?im)^\s*(?:[-*]\s*)?(?:\*\*)?email(?:\*\*)?\s*:\s*`?([^`\s]+)", c)
    pw = re.search(r"(?im)^\s*(?:[-*]\s*)?(?:\*\*)?password(?:\*\*)?\s*:\s*`?([^`\s]+)", c)
    if not e or not pw:
        pytest.skip("no creds parsed")
    return {"email": e.group(1), "password": pw.group(1)}


@pytest.fixture(scope="session")
def client(creds):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/auth/login", json=creds, timeout=30)
    if r.status_code != 200:
        pytest.fail(f"login failed {r.status_code}: {r.text[:300]}")
    return s


# ---------- Auth / playbook ----------
class TestAuthPlaybook:
    def test_login_sets_httponly_cookies(self, creds):
        s = requests.Session()
        r = s.post(f"{BASE_URL}/auth/login", json=creds, timeout=30)
        assert r.status_code == 200
        raw = "; ".join(r.headers.get_all("set-cookie")) if hasattr(r.headers, "get_all") else r.headers.get("set-cookie", "")
        combined = raw.lower()
        assert "access_token" in combined
        assert "httponly" in combined
        me = s.get(f"{BASE_URL}/auth/me", timeout=30)
        assert me.status_code == 200
        assert me.json().get("email") == creds["email"]

    def test_login_invalid_password(self, creds):
        r = requests.post(f"{BASE_URL}/auth/login", json={"email": creds["email"], "password": "wrong-xyz"}, timeout=30)
        assert r.status_code in (400, 401, 423, 429), r.text[:200]

    def test_cors_allows_credentials(self):
        r = requests.options(
            f"{BASE_URL}/auth/me",
            headers={
                "Origin": base_url.rstrip("/"),
                "Access-Control-Request-Method": "GET",
            },
            timeout=30,
        )
        assert r.status_code < 400
        assert r.headers.get("access-control-allow-credentials") == "true"

    def test_protected_endpoints_require_auth(self):
        for path in ["/references", "/insights/squad", "/goalkeepers"]:
            r = requests.get(f"{BASE_URL}{path}", timeout=30)
            assert r.status_code == 401, f"{path} -> {r.status_code}"

    def test_bcrypt_hash_format(self):
        try:
            from pymongo import MongoClient
        except ImportError:
            pytest.skip("pymongo missing")
        env = dotenv_values("/app/backend/.env")
        mc = MongoClient(env["MONGO_URL"])
        u = mc[env["DB_NAME"]].users.find_one({"role": "admin"})
        assert u is not None
        assert u["password_hash"].startswith("$2b$"), u["password_hash"][:10]

    def test_brute_force_lockout(self, creds):
        """Playbook: account should lock after 5 failed attempts."""
        s = requests.Session()
        codes = []
        for _ in range(6):
            r = s.post(f"{BASE_URL}/auth/login", json={"email": creds["email"], "password": "bad-pass-1"}, timeout=30)
            codes.append(r.status_code)
        assert any(c in (423, 429) for c in codes), f"no lockout, codes={codes}"


# ---------- Deterministic GK fixture for metrics ----------
def _mk_action(situation, decisions, evaluation, technique=""):
    return {
        "situation": situation, "decisions": decisions, "evaluation": evaluation,
        "technique": technique, "zone": "", "distance": "", "followup": "", "finish_type": "",
    }


@pytest.fixture(scope="class")
def two_gks(client):
    """Create 2 temp GKs with deterministic actions; cleanup after class."""
    made = {"gks": [], "reports": []}
    tag = uuid.uuid4().hex[:6]
    out = {}
    for label, spec in {
        # A: 4 Remate actions, 3 of which also 'Ocupar espaço' (2 success)
        "A": [
            _mk_action("Remate", ["Ocupar espaço"], "verde"),
            _mk_action("Remate", ["Ocupar espaço"], "cinzenta"),
            _mk_action("Remate", ["Ocupar espaço"], "vermelho"),
            _mk_action("Remate", ["Sair aos pés"], "verde"),
            _mk_action("1x1", ["Ocupar espaço"], "verde"),
        ],
        # B (benchmark): 2 Remate+Ocupar espaço, both success => 100%
        "B": [
            _mk_action("Remate", ["Ocupar espaço"], "verde"),
            _mk_action("Remate", ["Ocupar espaço"], "verde"),
            _mk_action("Remate", ["Sair aos pés"], "vermelho"),
        ],
    }.items():
        gk = client.post(f"{BASE_URL}/goalkeepers", json={"name": f"TEST_It8_{label}_{tag}", "team": "TEST"}, timeout=30)
        assert gk.status_code in (200, 201), gk.text[:300]
        gid = gk.json()["id"]
        made["gks"].append(gid)
        rep = client.post(f"{BASE_URL}/reports", json={
            "goalkeeper_id": gid, "goalkeeper_name": f"TEST_It8_{label}_{tag}",
            "session_number": "T1", "actions": spec,
            "offensive": {"passes_ok": 1, "passes_err": 1},
        }, timeout=30)
        assert rep.status_code in (200, 201), rep.text[:300]
        made["reports"].append(rep.json().get("id"))
        out[label] = gid
    yield out
    for rid in made["reports"]:
        if rid:
            client.delete(f"{BASE_URL}/reports/{rid}", timeout=30)
    for gid in made["gks"]:
        client.delete(f"{BASE_URL}/goalkeepers/{gid}", timeout=30)


class TestSubgamesCrossAndBenchmark:
    def test_cross_filter_and_benchmark(self, client, two_gks):
        a, b = two_gks["A"], two_gks["B"]
        topics = {
            "Defesa da baliza": [
                {"id": "t-single", "name": "TEST_single", "field": "situation", "value": "Remate",
                 "field2": "", "value2": "", "benchmark_gk_id": ""},
                {"id": "t-cross", "name": "TEST_cross", "field": "situation", "value": "Remate",
                 "field2": "decisions", "value2": "Ocupar espaço", "benchmark_gk_id": ""},
                {"id": "t-bench", "name": "TEST_bench", "field": "situation", "value": "Remate",
                 "field2": "decisions", "value2": "Ocupar espaço", "benchmark_gk_id": b},
                {"id": "t-self", "name": "TEST_self", "field": "situation", "value": "Remate",
                 "field2": "decisions", "value2": "Ocupar espaço", "benchmark_gk_id": a},
            ]
        }
        put = client.put(f"{BASE_URL}/goalkeepers/{a}/subgames", json={"subgames": topics}, timeout=30)
        assert put.status_code == 200, put.text[:300]

        got = client.get(f"{BASE_URL}/goalkeepers/{a}/subgames", timeout=30)
        assert got.status_code == 200
        arr = got.json()["subgames"]["Defesa da baliza"]
        by_id = {t["id"]: t for t in arr}
        assert set(by_id) == {"t-single", "t-cross", "t-bench", "t-self"}

        # persistence of new fields
        assert by_id["t-cross"]["field2"] == "decisions"
        assert by_id["t-cross"]["value2"] == "Ocupar espaço"
        assert by_id["t-bench"]["benchmark_gk_id"] == b

        single = by_id["t-single"]["metric_result"]
        cross = by_id["t-cross"]["metric_result"]
        assert single["count"] == 4, single
        assert cross["count"] == 3, cross
        assert cross["count"] <= single["count"]
        assert cross["success"] == 2 and cross["pct"] == 67, cross

        # no benchmark selected -> no benchmark block / auto_eval
        assert by_id["t-single"]["benchmark"] is None
        assert by_id["t-single"]["auto_eval"] is None
        assert by_id["t-cross"]["benchmark"] is None
        assert by_id["t-cross"]["auto_eval"] is None

        # manual benchmark uses the SAME 2 filters on the chosen GK
        bm = by_id["t-bench"]["benchmark"]
        assert bm is not None
        assert bm["best_count"] == 2, bm
        assert bm["best_pct"] == 100, bm
        assert bm["is_best"] is False
        assert "TEST_It8_B_" in bm["best_gk"]
        # ratio 67/100 = 0.67 -> vermelho
        assert by_id["t-bench"]["auto_eval"] == "vermelho", by_id["t-bench"]["auto_eval"]

        # benchmark == self -> is_best true, verde
        bs = by_id["t-self"]["benchmark"]
        assert bs["is_best"] is True
        assert bs["best_pct"] == cross["pct"]
        assert by_id["t-self"]["auto_eval"] == "verde"

    def test_offensive_ignores_second_filter(self, client, two_gks):
        a = two_gks["A"]
        topics = {"GR subido": [
            {"id": "o1", "name": "TEST_off", "field": "offensive", "value": "passes",
             "field2": "decisions", "value2": "Ocupar espaço", "benchmark_gk_id": ""},
        ]}
        assert client.put(f"{BASE_URL}/goalkeepers/{a}/subgames", json={"subgames": topics}, timeout=30).status_code == 200
        t = client.get(f"{BASE_URL}/goalkeepers/{a}/subgames", timeout=30).json()["subgames"]["GR subido"][0]
        assert t["metric_result"]["count"] == 2
        assert t["metric_result"]["pct"] == 50

    def test_invalid_benchmark_id_is_ignored(self, client, two_gks):
        a = two_gks["A"]
        topics = {"Bolas paradas": [
            {"id": "x1", "name": "TEST_badbench", "field": "situation", "value": "Remate",
             "field2": "", "value2": "", "benchmark_gk_id": "nonexistent-id-123"},
        ]}
        r = client.put(f"{BASE_URL}/goalkeepers/{a}/subgames", json={"subgames": topics}, timeout=30)
        assert r.status_code == 200
        t = client.get(f"{BASE_URL}/goalkeepers/{a}/subgames", timeout=30).json()["subgames"]["Bolas paradas"][0]
        assert t["benchmark"] is None
        assert t["auto_eval"] is None


class TestReferencesCRUD:
    created = []

    def test_create_list_delete(self, client):
        payload = {"subgame": "GR subido", "gk_id": "", "name": "TEST_Ref_Externo", "note": "TEST nota"}
        c = client.post(f"{BASE_URL}/references", json=payload, timeout=30)
        assert c.status_code in (200, 201), c.text[:300]
        body = c.json()
        rid = body["id"]
        TestReferencesCRUD.created.append(rid)
        assert body["subgame"] == payload["subgame"]
        assert body["name"] == payload["name"]

        lst = client.get(f"{BASE_URL}/references", timeout=30)
        assert lst.status_code == 200
        rows = lst.json()
        assert isinstance(rows, list)
        assert all("_id" not in r for r in rows), "MongoDB _id leaked"
        mine = [r for r in rows if r["id"] == rid]
        assert len(mine) == 1
        assert mine[0]["note"] == "TEST nota"
        assert mine[0]["subgame"] == "GR subido"

        d = client.delete(f"{BASE_URL}/references/{rid}", timeout=30)
        assert d.status_code in (200, 204)
        rows2 = client.get(f"{BASE_URL}/references", timeout=30).json()
        assert not [r for r in rows2 if r["id"] == rid]
        TestReferencesCRUD.created.remove(rid)

    def test_create_with_squad_gk(self, client):
        squad = client.get(f"{BASE_URL}/insights/squad", timeout=30)
        assert squad.status_code == 200
        gks = squad.json()["goalkeepers"]
        assert gks
        g = sorted(gks, key=lambda x: -x.get("total_actions", 0))[0]
        c = client.post(f"{BASE_URL}/references", json={
            "subgame": "Defesa da baliza", "gk_id": g["id"], "name": g["name"], "note": ""}, timeout=30)
        assert c.status_code in (200, 201)
        rid = c.json()["id"]
        TestReferencesCRUD.created.append(rid)
        row = [r for r in client.get(f"{BASE_URL}/references", timeout=30).json() if r["id"] == rid][0]
        assert row["gk_id"] == g["id"]
        assert g["total_actions"] > 0  # frontend bar needs this

    def test_delete_invalid_id(self, client):
        r = client.delete(f"{BASE_URL}/references/not-an-objectid", timeout=30)
        assert r.status_code in (200, 204, 400, 404, 422), r.status_code

    def test_missing_subgame_validation(self, client):
        r = client.post(f"{BASE_URL}/references", json={"name": "TEST_x"}, timeout=30)
        assert r.status_code == 422

    def test_references_require_auth(self):
        assert requests.post(f"{BASE_URL}/references", json={"subgame": "GR subido", "name": "x"}, timeout=30).status_code == 401


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    try:
        from pymongo import MongoClient
        env = dotenv_values("/app/backend/.env")
        mc = MongoClient(env["MONGO_URL"])
        dbc = mc[env["DB_NAME"]]
        dbc.references.delete_many({"name": {"$regex": "^TEST_"}})
        dbc.subgame_evals.delete_many({})
    except Exception as e:  # noqa: BLE001
        print(f"cleanup warning: {e}")


# ---------- Regression smoke ----------
class TestRegressions:
    @pytest.mark.parametrize("path", [
        "/goalkeepers", "/export", "/insights/general", "/insights/squad", "/videos", "/references",
    ])
    def test_endpoint_ok(self, client, path):
        r = client.get(f"{BASE_URL}{path}", timeout=60)
        assert r.status_code == 200, f"{path} -> {r.status_code} {r.text[:200]}"
        assert "_id" not in r.text, f"_id leaked in {path}"
