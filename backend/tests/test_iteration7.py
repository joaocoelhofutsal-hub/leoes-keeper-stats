"""Iteration 7 backend tests.

Covers:
 - GET /api/insights/squad (Dashboard KPIs + ranking data)
 - Loose actions shown in GK profile (do not count as reports)
 - Sub-jogos metric with field='offensive' (passes/shots/repos)
 - Sub-jogos benchmark (best_pct/best_gk) + auto_eval thresholds
 - SUCCESS_EVALS = verde + cinzenta
 - Regressions: general insights, goalkeepers, videos, training, auth guards
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
    raise RuntimeError("REACT_APP_BACKEND_URL is missing")
BASE_URL = base_url.rstrip("/")
API = f"{BASE_URL}/api"

SUCCESS_EVALS = ("verde", "cinzenta")


# ---------- fixtures ----------
@pytest.fixture(scope="session")
def creds():
    p = Path("/app/memory/test_credentials.md")
    if not p.exists():
        pytest.skip("missing test_credentials.md")
    c = p.read_text(encoding="utf-8")
    e = re.search(r'(?im)^\s*-\s*Email:\s*`?([^`\s]+)', c)
    pw = re.search(r'(?im)^\s*-\s*Password:\s*`?([^`\s]+)', c)
    if not e or not pw:
        pytest.skip("no credentials parsed")
    return {"email": e.group(1), "password": pw.group(1)}


@pytest.fixture(scope="session")
def client(creds):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=creds, timeout=30)
    if r.status_code != 200:
        pytest.fail(f"login failed {r.status_code}: {r.text[:300]}")
    return s


@pytest.fixture(scope="session")
def dump(client):
    r = client.get(f"{API}/export", timeout=60)
    assert r.status_code == 200
    return r.json()


def _metric(actions, off, field, value):
    OFF_MAP = {"passes": ("passes_ok", "passes_err"), "shots": ("shots_ok", "shots_err"),
               "repos": ("repos_ok", "repos_err")}
    if field == "offensive":
        okk, errk = OFF_MAP[value]
        ok = int(off.get(okk, 0) or 0)
        err = int(off.get(errk, 0) or 0)
        cnt = ok + err
        return {"count": cnt, "success": ok, "pct": round(ok / cnt * 100) if cnt else 0}
    if field == "decisions":
        m = [a for a in actions if value in (a.get("decisions") or [])]
    else:
        m = [a for a in actions if (a.get(field) or "") == value]
    succ = sum(1 for a in m if a.get("evaluation") in SUCCESS_EVALS)
    return {"count": len(m), "success": succ, "pct": round(succ / len(m) * 100) if m else 0}


def _squad_from_dump(d):
    out = {}
    for r in d["reports"]:
        gid = r.get("goalkeeper_id", "")
        e = out.setdefault(gid, {"actions": [], "off": {}})
        e["actions"].extend(r.get("actions") or [])
        o = r.get("offensive") or {}
        for k, v in o.items():
            e["off"][k] = e["off"].get(k, 0) + int(v or 0)
    return out


# ---------- auth ----------
class TestAuth:
    def test_login_sets_httponly_cookies(self, creds):
        s = requests.Session()
        r = s.post(f"{API}/auth/login", json=creds, timeout=30)
        assert r.status_code == 200
        raw = "; ".join(r.headers.get_all("set-cookie")) if hasattr(r.headers, "get_all") else r.headers.get("set-cookie", "")
        names = {c.name for c in s.cookies}
        assert "access_token" in names and "refresh_token" in names, names
        assert "httponly" in raw.lower()
        me = s.get(f"{API}/auth/me", timeout=30)
        assert me.status_code == 200
        assert me.json().get("email") == creds["email"]

    def test_squad_requires_auth(self):
        r = requests.get(f"{API}/insights/squad", timeout=30)
        assert r.status_code == 401

    def test_subgames_requires_auth(self):
        r = requests.get(f"{API}/goalkeepers/000000000000000000000000/subgames", timeout=30)
        assert r.status_code == 401


# ---------- Dashboard: /insights/squad ----------
class TestSquadInsights:
    def test_structure_and_totals(self, client, dump):
        r = client.get(f"{API}/insights/squad", timeout=60)
        assert r.status_code == 200
        body = r.json()
        assert set(["goalkeepers", "totals"]).issubset(body.keys())
        gks, totals = body["goalkeepers"], body["totals"]
        assert isinstance(gks, list) and len(gks) > 0
        for g in gks:
            for k in ["id", "name", "team", "games", "total_actions", "success_pct",
                      "best_reaction_ms", "avg_reaction_ms"]:
                assert k in g, f"missing {k}"
            assert "_id" not in g
            assert isinstance(g["total_actions"], int)
            assert 0 <= g["success_pct"] <= 100
        assert totals["goalkeepers"] == len(gks)
        assert totals["games"] == sum(g["games"] for g in gks)
        assert totals["total_actions"] == sum(g["total_actions"] for g in gks)

    def test_per_gk_success_matches_verde_plus_cinzenta(self, client, dump):
        r = client.get(f"{API}/insights/squad", timeout=60)
        squad = _squad_from_dump(dump)
        for g in r.json()["goalkeepers"]:
            acts = squad.get(g["id"], {"actions": []})["actions"]
            assert g["total_actions"] == len(acts), g["name"]
            if acts:
                succ = sum(1 for a in acts if a.get("evaluation") in SUCCESS_EVALS)
                assert g["success_pct"] == round(succ / len(acts) * 100), g["name"]
            else:
                assert g["success_pct"] == 0

    def test_games_excludes_loose_reports(self, client, dump):
        r = client.get(f"{API}/insights/squad", timeout=60)
        expected = {}
        for rep in dump["reports"]:
            if not rep.get("loose"):
                expected[rep.get("goalkeeper_id")] = expected.get(rep.get("goalkeeper_id"), 0) + 1
        for g in r.json()["goalkeepers"]:
            assert g["games"] == expected.get(g["id"], 0), g["name"]

    def test_general_reports_consistent_with_squad_games(self, client):
        gen = client.get(f"{API}/insights/general", timeout=60).json()
        squad = client.get(f"{API}/insights/squad", timeout=60).json()
        assert gen["reports"] == squad["totals"]["games"]
        assert gen["goalkeepers"] == squad["totals"]["goalkeepers"]
        assert gen["total_actions"] == squad["totals"]["total_actions"]


# ---------- deterministic GK for metric/benchmark/loose tests ----------
@pytest.fixture(scope="class")
def test_gk(client):
    r = client.post(f"{API}/goalkeepers", json={"name": f"TEST_It7_{uuid.uuid4().hex[:6]}", "team": "TEST"}, timeout=30)
    assert r.status_code == 200, r.text
    gid = r.json()["id"]
    yield gid
    client.delete(f"{API}/goalkeepers/{gid}", timeout=30)


class TestSubgameMetrics:
    """offensive source, cinzenta in success, benchmark + auto_eval"""

    @pytest.fixture(scope="class", autouse=True)
    def seeded(self, client, test_gk):
        actions = [
            {"situation": "Remate", "technique": "Blocking", "decisions": ["Ocupar espaço"], "evaluation": "verde"},
            {"situation": "Remate", "technique": "Blocking", "decisions": ["Ocupar espaço"], "evaluation": "cinzenta"},
            {"situation": "Remate", "technique": "Blocking", "decisions": ["Ocupar espaço"], "evaluation": "amarelo"},
            {"situation": "Remate", "technique": "Blocking", "decisions": ["Ocupar espaço"], "evaluation": "vermelho"},
            {"situation": "Balão", "decisions": ["Enquadramento"], "evaluation": "verde"},
        ]
        payload = {
            "goalkeeper_id": test_gk, "goalkeeper_name": "TEST_It7", "session_number": "TEST_1",
            "actions": actions,
            "offensive": {"passes_ok": 3, "passes_err": 1, "shots_ok": 1, "shots_err": 1,
                          "repos_ok": 0, "repos_err": 2},
        }
        r = client.post(f"{API}/reports", json=payload, timeout=30)
        assert r.status_code == 200, r.text
        rid = r.json()["id"]
        subgames = {
            "Defesa da baliza": [
                {"id": "t-pass", "name": "TEST passes", "field": "offensive", "value": "passes", "evaluation": "verde", "note": ""},
                {"id": "t-shots", "name": "TEST remates", "field": "offensive", "value": "shots", "evaluation": "", "note": ""},
                {"id": "t-repos", "name": "TEST reposicoes", "field": "offensive", "value": "repos", "evaluation": "", "note": ""},
                {"id": "t-dec", "name": "TEST ocupar espaco", "field": "decisions", "value": "Ocupar espaço", "evaluation": "", "note": ""},
                {"id": "t-none", "name": "TEST sem metrica", "field": "", "value": "", "evaluation": "amarelo", "note": "nota"},
                {"id": "t-empty", "name": "TEST sem dados", "field": "situation", "value": "Cobertura", "evaluation": "", "note": ""},
            ]
        }
        pr = client.put(f"{API}/goalkeepers/{test_gk}/subgames", json={"subgames": subgames}, timeout=30)
        assert pr.status_code == 200, pr.text
        yield
        client.delete(f"{API}/reports/{rid}", timeout=30)

    @pytest.fixture(scope="class")
    def topics(self, client, test_gk):
        r = client.get(f"{API}/goalkeepers/{test_gk}/subgames", timeout=60)
        assert r.status_code == 200, r.text
        tp = {t["id"]: t for t in r.json()["subgames"]["Defesa da baliza"]}
        assert len(tp) == 6
        return tp

    def test_offensive_passes_metric(self, topics):
        m = topics["t-pass"]["metric_result"]
        assert m == {"count": 4, "success": 3, "pct": 75}, m

    def test_offensive_shots_metric(self, topics):
        assert topics["t-shots"]["metric_result"] == {"count": 2, "success": 1, "pct": 50}

    def test_offensive_repos_metric(self, topics):
        assert topics["t-repos"]["metric_result"] == {"count": 2, "success": 0, "pct": 0}

    def test_success_includes_cinzenta(self, topics):
        m = topics["t-dec"]["metric_result"]
        # 4 actions with 'Ocupar espaço': verde, cinzenta, amarelo, vermelho
        assert m["count"] == 4
        assert m["success"] == 2, "success must count verde + cinzenta"
        assert m["pct"] == 50

    def test_no_metric_topic(self, topics):
        t = topics["t-none"]
        assert t["metric_result"] is None
        assert t["benchmark"] is None and t["auto_eval"] is None
        assert t["evaluation"] == "amarelo" and t["note"] == "nota"

    def test_zero_count_topic_has_no_benchmark(self, topics):
        t = topics["t-empty"]
        assert t["metric_result"] == {"count": 0, "success": 0, "pct": 0}
        assert t["benchmark"] is None and t["auto_eval"] is None

    def test_benchmark_is_best_of_all_gks(self, client, topics):
        d = client.get(f"{API}/export", timeout=60).json()
        squad = _squad_from_dump(d)
        names = {g["id"]: g["name"] for g in client.get(f"{API}/goalkeepers", timeout=30).json()}
        for tid, field, value in [("t-pass", "offensive", "passes"), ("t-dec", "decisions", "Ocupar espaço")]:
            t = topics[tid]
            assert t["benchmark"] is not None, tid
            best_pct, best_name = -1, None
            for gid, e in squad.items():
                m = _metric(e["actions"], e["off"], field, value)
                if m["count"] > 0 and m["pct"] > best_pct:
                    best_pct, best_name = m["pct"], names.get(gid, "—")
            assert t["benchmark"]["best_pct"] == best_pct, (tid, t["benchmark"], best_pct)
            assert t["benchmark"]["best_gk"] == best_name, (tid, t["benchmark"], best_name)

    def test_auto_eval_thresholds(self, topics):
        for tid in ["t-pass", "t-dec", "t-shots", "t-repos"]:
            t = topics[tid]
            m, b = t["metric_result"], t["benchmark"]
            assert b is not None, tid
            ratio = m["pct"] / b["best_pct"] if b["best_pct"] > 0 else 1
            expected = "verde" if ratio >= 0.9 else ("amarelo" if ratio >= 0.7 else "vermelho")
            assert t["auto_eval"] == expected, (tid, m, b, t["auto_eval"])

    def test_subgames_persist(self, client, test_gk):
        r = client.get(f"{API}/goalkeepers/{test_gk}/subgames", timeout=60).json()
        assert len(r["subgames"]["Defesa da baliza"]) == 6


# ---------- loose actions in profile ----------
class TestLooseActions:
    def test_loose_action_flow(self, client, test_gk):
        before_prof = client.get(f"{API}/goalkeepers/{test_gk}/profile", timeout=30).json()
        before_squad = {g["id"]: g for g in client.get(f"{API}/insights/squad", timeout=60).json()["goalkeepers"]}[test_gk]

        act = {"situation": "Remate", "technique": "Blocking", "distance": "Curta",
               "decisions": ["Encurtamento"], "evaluation": "verde"}
        r = client.post(f"{API}/goalkeepers/{test_gk}/loose-actions", json=act, timeout=30)
        assert r.status_code == 200, r.text
        created = r.json()
        assert created["id"] and created["created_at"]
        assert created["situation"] == "Remate"
        aid = created["id"]

        lst = client.get(f"{API}/goalkeepers/{test_gk}/loose-actions", timeout=30)
        assert lst.status_code == 200
        ids = [a["id"] for a in lst.json()]
        assert aid in ids

        after_prof = client.get(f"{API}/goalkeepers/{test_gk}/profile", timeout=30).json()
        assert "total_reports" in before_prof and "total_reports" in after_prof
        assert after_prof["total_reports"] == before_prof["total_reports"], "loose action must not add a report"
        assert after_prof["avg_actions_per_game"] == before_prof["avg_actions_per_game"]
        assert after_prof["total_actions"] == before_prof["total_actions"] + 1

        after_squad = {g["id"]: g for g in client.get(f"{API}/insights/squad", timeout=60).json()["goalkeepers"]}[test_gk]
        assert after_squad["games"] == before_squad["games"], "loose action must not add a game"
        assert after_squad["total_actions"] == before_squad["total_actions"] + 1

        # reports list for the GK must not include the loose doc
        reps = client.get(f"{API}/goalkeepers/{test_gk}/reports", timeout=30).json()
        assert all(not x.get("loose") for x in reps)
        assert all(x.get("session_number") != "Ações soltas" for x in reps)

        d = client.delete(f"{API}/goalkeepers/{test_gk}/loose-actions/{aid}", timeout=30)
        assert d.status_code == 200
        assert aid not in [a["id"] for a in client.get(f"{API}/goalkeepers/{test_gk}/loose-actions", timeout=30).json()]


# ---------- regressions ----------
class TestRegressions:
    def test_goalkeepers_list(self, client):
        r = client.get(f"{API}/goalkeepers", timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 8
        for g in data:
            assert "id" in g and "_id" not in g

    def test_general_insights(self, client):
        r = client.get(f"{API}/insights/general", timeout=60)
        assert r.status_code == 200
        b = r.json()
        assert b["total_actions"] > 0
        assert len(b["evaluation"]) == 4
        assert set(b["offensive_totals"].keys()) == {"passes_ok", "passes_err", "shots_ok",
                                                    "shots_err", "repos_ok", "repos_err"}

    def test_videos_list(self, client):
        r = client.get(f"{API}/videos", timeout=30)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_training_list(self, client):
        gks = client.get(f"{API}/goalkeepers", timeout=30).json()
        r = client.get(f"{API}/goalkeepers/{gks[0]['id']}/training", timeout=30)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_profile_shape(self, client):
        gks = client.get(f"{API}/goalkeepers", timeout=30).json()
        target = next((g for g in gks if g.get("report_count", 0) > 0), gks[0])
        r = client.get(f"{API}/goalkeepers/{target['id']}/profile", timeout=30)
        assert r.status_code == 200
        b = r.json()
        assert "total_reports" in b and "total_actions" in b

    def test_bad_goalkeeper_id_404(self, client):
        r = client.get(f"{API}/goalkeepers/000000000000000000000000/profile", timeout=30)
        assert r.status_code in (404, 200)
