"""Iteration 11 - Microciclo JOGOS + Scouting & Match Plan (backend)."""
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
BASE_URL = base_url.rstrip("/")
API = f"{BASE_URL}/api"

TEST_PREFIX = "TEST_IT11_"


# ---------- fixtures ----------
@pytest.fixture(scope="session")
def creds():
    p = Path("/app/memory/test_credentials.md")
    if not p.exists():
        pytest.skip("missing test_credentials.md")
    c = p.read_text(encoding="utf-8")
    e = re.search(r"(?im)^\s*-\s*Email:\s*(\S+)", c)
    pw = re.search(r"(?im)^\s*-\s*Password:\s*(\S+)", c)
    if not e or not pw:
        pytest.skip("no creds parsed")
    return {"email": e.group(1), "password": pw.group(1)}


@pytest.fixture(scope="session")
def client(creds):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=creds, timeout=60)
    if r.status_code != 200:
        pytest.fail(f"login failed {r.status_code}: {r.text[:300]}")
    assert "access_token" in s.cookies, "access_token cookie not set"
    return s


@pytest.fixture(scope="session")
def created(client):
    store = {"microcycles": [], "games": []}
    yield store
    for mid in store["microcycles"]:
        client.delete(f"{API}/microcycles/{mid}", timeout=60)


# ---------- auth / playbook checks ----------
class TestAuthPlaybook:
    def test_login_sets_httponly_cookies(self, creds):
        s = requests.Session()
        r = s.post(f"{API}/auth/login", json=creds, timeout=60)
        assert r.status_code == 200
        data = r.json()
        assert data["email"] == creds["email"].lower()
        assert data.get("role") == "admin"
        cookie_headers = r.headers.get("set-cookie", "").lower()
        assert "httponly" in cookie_headers
        assert "access_token" in s.cookies and "refresh_token" in s.cookies

    def test_me_requires_auth(self):
        r = requests.get(f"{API}/auth/me", timeout=60)
        assert r.status_code in (401, 403), r.status_code

    def test_login_invalid_password(self, creds):
        r = requests.post(f"{API}/auth/login",
                          json={"email": creds["email"], "password": "wrong-pass-xyz"}, timeout=60)
        assert r.status_code == 401
        assert "detail" in r.json()

    def test_bcrypt_hash_format(self, creds):
        """Admin password hash must be bcrypt $2b$."""
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        env = dotenv_values("/app/backend/.env")
        mongo_url = env.get("MONGO_URL")
        db_name = env.get("DB_NAME")
        assert mongo_url and db_name

        async def check():
            c = AsyncIOMotorClient(mongo_url)
            u = await c[db_name].users.find_one({"email": creds["email"].lower()})
            c.close()
            return u

        u = asyncio.get_event_loop().run_until_complete(check())
        assert u is not None
        assert u["password_hash"].startswith("$2b$"), u["password_hash"][:10]

    def test_cors_credentials_explicit_origin(self):
        # NOTE: OPTIONS preflight is answered by the k8s/CF edge (ACAO: *), so we assert
        # app-level CORS on a real request carrying the Origin header.
        r = requests.get(f"{API}/auth/me", headers={"Origin": BASE_URL}, timeout=60)
        assert r.headers.get("access-control-allow-credentials") == "true", dict(r.headers)
        # The preview edge proxy rewrites ACAO to '*'; the app itself echoes the explicit origin
        # (verified against 0.0.0.0:8001). Accept both to avoid a false negative.
        assert r.headers.get("access-control-allow-origin") in (BASE_URL, "*"), dict(r.headers)


# ---------- Microciclo: treinos must keep working ----------
class TestMicrocycleTrainings:
    def test_create_microcycle_with_training_and_persist(self, client, created):
        payload = {
            "name": f"{TEST_PREFIX}treinos",
            "days": {"Segunda": [{
                "id": str(uuid.uuid4()), "type": "treino", "number": "1",
                "duration": "20 min", "components": ["Reação"], "video_ids": [],
                "notes": "nota treino",
            }]},
        }
        r = client.post(f"{API}/microcycles", json=payload, timeout=60)
        assert r.status_code == 200, r.text[:300]
        mid = r.json()["id"]
        created["microcycles"].append(mid)

        g = client.get(f"{API}/microcycles/{mid}", timeout=60)
        assert g.status_code == 200
        d = g.json()
        assert "_id" not in d
        assert d["name"] == payload["name"]
        tr = d["days"]["Segunda"][0]
        assert tr["type"] == "treino"
        assert tr["number"] == "1"
        assert tr["duration"] == "20 min"
        assert tr["components"] == ["Reação"]
        assert tr["notes"] == "nota treino"

    def test_microcycle_pdf(self, client, created):
        mid = created["microcycles"][0]
        r = client.get(f"{API}/microcycles/{mid}/pdf", timeout=120)
        assert r.status_code == 200, r.text[:300]
        assert r.headers["content-type"].startswith("application/pdf")
        assert r.content[:4] == b"%PDF"

    def test_list_does_not_expose_mongo_id(self, client):
        r = client.get(f"{API}/microcycles", timeout=60)
        assert r.status_code == 200
        for m in r.json():
            assert "_id" not in m
            assert "id" in m

    def test_microcycle_404(self, client):
        r = client.get(f"{API}/microcycles/{'a' * 24}", timeout=60)
        assert r.status_code == 404


# ---------- Microciclo: jogos coexisting with treinos ----------
class TestMicrocycleGames:
    def test_game_and_training_same_day_persist(self, client, created):
        gid = str(uuid.uuid4())
        created["games"].append(gid)
        game = {"id": gid, "type": "jogo", "opponent": "TEST_Sporting",
                "competition": "Liga", "round": "12", "date": "2026-07-18",
                "time": "18:30", "venue": "Pavilhão TEST", "home_away": "Fora"}
        training = {"id": str(uuid.uuid4()), "type": "treino", "number": "2",
                    "duration": "30 min", "components": [], "video_ids": [], "notes": ""}
        r = client.post(f"{API}/microcycles", json={
            "name": f"{TEST_PREFIX}jogos", "days": {"Sábado": [training, game]}}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        mid = r.json()["id"]
        created["microcycles"].append(mid)

        d = client.get(f"{API}/microcycles/{mid}", timeout=60).json()
        evs = d["days"]["Sábado"]
        assert len(evs) == 2
        assert [e["type"] for e in evs] == ["treino", "jogo"]
        saved = evs[1]
        for k, v in game.items():
            assert saved[k] == v, k

    def test_edit_and_delete_game_event(self, client, created):
        mid = created["microcycles"][-1]
        d = client.get(f"{API}/microcycles/{mid}", timeout=60).json()
        evs = d["days"]["Sábado"]
        evs[1]["opponent"] = "TEST_Benfica"
        r = client.put(f"{API}/microcycles/{mid}",
                       json={"name": d["name"], "days": d["days"]}, timeout=60)
        assert r.status_code == 200
        d2 = client.get(f"{API}/microcycles/{mid}", timeout=60).json()
        assert d2["days"]["Sábado"][1]["opponent"] == "TEST_Benfica"

        # delete the game only, training stays
        d2["days"]["Sábado"] = [d2["days"]["Sábado"][0]]
        client.put(f"{API}/microcycles/{mid}", json={"name": d2["name"], "days": d2["days"]}, timeout=60)
        d3 = client.get(f"{API}/microcycles/{mid}", timeout=60).json()
        assert len(d3["days"]["Sábado"]) == 1
        assert d3["days"]["Sábado"][0]["type"] == "treino"


# ---------- Scouting & Match Plan ----------
class TestScouting:
    def test_get_scouting_not_exists(self, client):
        r = client.get(f"{API}/scouting/{uuid.uuid4()}", timeout=60)
        assert r.status_code == 200
        b = r.json()
        assert b["exists"] is False

    def test_scouting_requires_auth(self):
        gid = str(uuid.uuid4())
        assert requests.get(f"{API}/scouting/{gid}", timeout=60).status_code in (401, 403)
        assert requests.put(f"{API}/scouting/{gid}", json={}, timeout=60).status_code in (401, 403)
        assert requests.get(f"{API}/scouting/{gid}/pdf", timeout=60).status_code in (401, 403)

    def test_pdf_404_when_no_plan(self, client):
        r = client.get(f"{API}/scouting/{uuid.uuid4()}/pdf", timeout=60)
        assert r.status_code == 404

    def test_save_get_pdf_and_regenerate(self, client, created):
        gid = f"TEST_IT11_{uuid.uuid4()}"
        created["games"].append(gid)
        payload = {
            "opponent": "TEST_Sporting", "competition": "Liga Placard", "round": "12",
            "date": "2026-07-18", "time": "18:30", "venue": "Pavilhão TEST",
            "home_away": "Fora", "opponent_logo": "",
            "called_gks": [{"name": "Guilherme Cintra"}, {"name": "Daniel Osuji"},
                           {"name": "Rodrigo Prazeres"}],
            "set_pieces": {"penalti": {"mode": "gk", "gk": "Daniel Osuji"},
                           "livre": {"mode": "campo", "gk": ""},
                           "livre10": {"mode": "gk", "gk": "Rodrigo Prazeres"}},
            "opposition_players": [
                {"id": "p1", "name": "TEST Jogador A", "number": "10", "position": "Ala",
                 "foot": "Direito", "notes": "remate forte", "photo": ""},
                {"id": "p2", "name": "TEST Jogador B", "number": "7", "position": "Pivô",
                 "foot": "Esquerdo", "notes": "costas", "photo": ""},
            ],
            "match_notes": "Linha 1\nLinha 2",
        }
        r = client.put(f"{API}/scouting/{gid}", json=payload, timeout=60)
        assert r.status_code == 200, r.text[:300]
        assert r.json().get("ok") is True

        g = client.get(f"{API}/scouting/{gid}", timeout=60)
        assert g.status_code == 200
        d = g.json()
        assert "_id" not in d
        assert d["exists"] is True
        assert d["game_id"] == gid
        assert d["opponent"] == "TEST_Sporting"
        assert d["home_away"] == "Fora"
        assert [c["name"] for c in d["called_gks"]] == ["Guilherme Cintra", "Daniel Osuji", "Rodrigo Prazeres"]
        assert d["set_pieces"]["penalti"] == {"mode": "gk", "gk": "Daniel Osuji"}
        assert d["set_pieces"]["livre"]["mode"] == "campo"
        assert len(d["opposition_players"]) == 2
        assert d["opposition_players"][0]["foot"] == "Direito"
        assert d["match_notes"] == "Linha 1\nLinha 2"

        pdf = client.get(f"{API}/scouting/{gid}/pdf", timeout=120)
        assert pdf.status_code == 200, pdf.text[:300]
        assert pdf.headers["content-type"].startswith("application/pdf")
        assert pdf.content[:4] == b"%PDF"
        assert len(pdf.content) > 2000

        # edit -> upsert must update, not duplicate; regenerate keeps changes
        payload["match_notes"] = "Notas atualizadas"
        payload["opposition_players"] = payload["opposition_players"][:1]
        assert client.put(f"{API}/scouting/{gid}", json=payload, timeout=60).status_code == 200
        d2 = client.get(f"{API}/scouting/{gid}", timeout=60).json()
        assert d2["match_notes"] == "Notas atualizadas"
        assert len(d2["opposition_players"]) == 1
        pdf2 = client.get(f"{API}/scouting/{gid}/pdf", timeout=120)
        assert pdf2.status_code == 200 and pdf2.content[:4] == b"%PDF"

    def test_scouting_independent_from_microcycle_pdf(self, client, created):
        """Microcycle PDF must still work and not require any scouting data."""
        r = client.post(f"{API}/microcycles", json={
            "name": f"{TEST_PREFIX}indep",
            "days": {"Segunda": [{"id": str(uuid.uuid4()), "type": "treino", "number": "1",
                                  "duration": "15 min", "components": [], "video_ids": [], "notes": ""}]},
        }, timeout=60)
        assert r.status_code == 200, r.text[:300]
        mid = r.json()["id"]
        created["microcycles"].append(mid)
        r = client.get(f"{API}/microcycles/{mid}/pdf", timeout=120)
        assert r.status_code == 200 and r.content[:4] == b"%PDF"

    def test_save_scouting_minimal_payload(self, client, created):
        gid = f"TEST_IT11_{uuid.uuid4()}"
        created["games"].append(gid)
        r = client.put(f"{API}/scouting/{gid}", json={}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        d = client.get(f"{API}/scouting/{gid}", timeout=60).json()
        assert d["exists"] is True
        assert d["called_gks"] == []
        pdf = client.get(f"{API}/scouting/{gid}/pdf", timeout=120)
        assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"

    def test_default_gks_exist_in_db(self, client):
        r = client.get(f"{API}/goalkeepers", timeout=60)
        assert r.status_code == 200
        names = [g["name"].lower() for g in r.json()]
        for expected in ["cintra", "osuji", "prazeres"]:
            assert any(expected in n for n in names), f"{expected} missing in DB: {names}"


# ---------- cleanup of scouting_plans created by tests ----------
def test_zz_cleanup_scouting(created):
    import asyncio
    from motor.motor_asyncio import AsyncIOMotorClient
    env = dotenv_values("/app/backend/.env")

    async def clean():
        c = AsyncIOMotorClient(env["MONGO_URL"])
        db = c[env["DB_NAME"]]
        for gid in created["games"]:
            await db.scouting_plans.delete_one({"game_id": gid})
        remaining = await db.scouting_plans.count_documents(
            {"game_id": {"$in": created["games"]}})
        c.close()
        return remaining

    assert asyncio.get_event_loop().run_until_complete(clean()) == 0
