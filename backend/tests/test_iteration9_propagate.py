"""Iteration 9: Sub-jogos topic propagation (POST /api/subgames/propagate-topic)."""
import os
import uuid

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")
API = f"{BASE_URL}/api"

EMAIL = "joaocoelhofutsal@gmail.com"
PASSWORD = "leoes2011"
SUBGAME = "Defesa da baliza"
PREFIX = "QATEST "


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=30)
    if r.status_code != 200:
        pytest.fail(f"Login failed {r.status_code}: {r.text[:300]}")
    assert "access_token" in s.cookies, f"httpOnly cookie missing: {s.cookies.get_dict()}"
    return s


@pytest.fixture(scope="module")
def gks(client):
    r = client.get(f"{API}/goalkeepers", timeout=30)
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) >= 2, "need at least 2 goalkeepers"
    return rows


CALC_KEYS = ("metric_result", "benchmark", "auto_eval")


def strip(t):
    return {k: v for k, v in t.items() if k not in CALC_KEYS}


def get_all(client, gid):
    """Full subgames dict (raw, calc fields stripped) - preserves other sub-games."""
    r = client.get(f"{API}/goalkeepers/{gid}/subgames", timeout=30)
    assert r.status_code == 200, r.text[:300]
    raw = r.json().get("subgames") or {}
    return {k: [strip(t) for t in (v or [])] for k, v in raw.items()}


def get_topics(client, gid, subgame=SUBGAME):
    r = client.get(f"{API}/goalkeepers/{gid}/subgames", timeout=30)
    assert r.status_code == 200, r.text[:300]
    return (r.json().get("subgames") or {}).get(subgame, []) or []


def put_subgame(client, gid, topics):
    """Replace only SUBGAME topics, keeping all other sub-games intact."""
    allsg = get_all(client, gid)
    allsg[SUBGAME] = topics
    r = client.put(f"{API}/goalkeepers/{gid}/subgames", json={"subgames": allsg}, timeout=30)
    assert r.status_code == 200, r.text[:300]


def cleanup(client, gks):
    for g in gks:
        allsg = get_all(client, g["id"])
        changed = False
        for sg, topics in allsg.items():
            kept = [t for t in topics if not (t.get("name") or "").upper().startswith(PREFIX)]
            if len(kept) != len(topics):
                allsg[sg] = kept
                changed = True
        if changed:
            r = client.put(f"{API}/goalkeepers/{g['id']}/subgames",
                           json={"subgames": allsg}, timeout=30)
            assert r.status_code == 200


@pytest.fixture(scope="module", autouse=True)
def _cleanup(client, gks):
    cleanup(client, gks)
    yield
    cleanup(client, gks)


class TestPropagation:
    def test_create_and_propagate(self, client, gks):
        name = f"{PREFIX}Ocupacao {uuid.uuid4().hex[:6]}"
        owner = gks[0]
        topic = {
            "id": str(uuid.uuid4()), "name": name, "evaluation": "verde",
            "field": "decisions", "value": "Ocupar espaço",
            "field2": "", "value2": "", "benchmark_gk_id": "", "note": "observação X",
        }
        existing = [strip(t) for t in get_topics(client, owner["id"])]
        put_subgame(client, owner["id"], existing + [topic])

        r = client.post(f"{API}/subgames/propagate-topic",
                        json={"subgame": SUBGAME, "exclude_gk_id": owner["id"], "topic": topic},
                        timeout=60)
        assert r.status_code == 200, r.text[:300]
        added = r.json().get("added")
        assert added == len(gks) - 1, f"expected {len(gks)-1} added, got {added}"

        # owner keeps note + evaluation
        own = [t for t in get_topics(client, owner["id"]) if t["name"] == name]
        assert len(own) == 1
        assert own[0]["note"] == "observação X"
        assert own[0]["evaluation"] == "verde"
        assert own[0].get("metric_result") is not None

        # others: replicated without note/evaluation, metric definition preserved
        for g in gks[1:]:
            got = [t for t in get_topics(client, g["id"]) if t["name"] == name]
            assert len(got) == 1, f"{g['name']}: expected 1 topic got {len(got)}"
            t = got[0]
            assert t["note"] == "", f"{g['name']} note not empty: {t['note']!r}"
            assert t["evaluation"] == "", f"{g['name']} evaluation not empty: {t['evaluation']!r}"
            assert t["field"] == "decisions" and t["value"] == "Ocupar espaço"
            assert t["id"] != topic["id"], "propagated topic reuses same id"
            assert t.get("metric_result") is not None, f"{g['name']} missing metric_result"
            assert set(t["metric_result"]) >= {"count", "success", "pct"}

        TestPropagation.name = name

    def test_no_duplicate_on_repropagate(self, client, gks):
        name = TestPropagation.name
        topic = {
            "id": str(uuid.uuid4()), "name": name, "evaluation": "vermelho",
            "field": "decisions", "value": "Ocupar espaço",
            "field2": "", "value2": "", "benchmark_gk_id": "", "note": "nota nova",
        }
        r = client.post(f"{API}/subgames/propagate-topic",
                        json={"subgame": SUBGAME, "exclude_gk_id": gks[0]["id"], "topic": topic},
                        timeout=60)
        assert r.status_code == 200
        assert r.json().get("added") == 0, "duplicated topic on other GKs"
        for g in gks[1:]:
            got = [t for t in get_topics(client, g["id"]) if t["name"] == name]
            assert len(got) == 1, f"{g['name']} duplicated: {len(got)}"
            assert got[0]["note"] == ""
            assert got[0]["evaluation"] == ""

    def test_case_insensitive_dedup(self, client, gks):
        name = TestPropagation.name.upper()
        topic = {"id": str(uuid.uuid4()), "name": name, "evaluation": "", "field": "", "value": "",
                 "field2": "", "value2": "", "benchmark_gk_id": "", "note": ""}
        r = client.post(f"{API}/subgames/propagate-topic",
                        json={"subgame": SUBGAME, "exclude_gk_id": gks[0]["id"], "topic": topic},
                        timeout=60)
        assert r.status_code == 200
        assert r.json().get("added") == 0, "case-insensitive dedup failed"

    def test_edit_does_not_propagate(self, client, gks):
        name = TestPropagation.name
        target = gks[1]
        topics = [strip(t) for t in get_topics(client, target["id"])]
        for t in topics:
            if t["name"] == name:
                t["note"] = "editado no GR2"
                t["evaluation"] = "amarelo"
        put_subgame(client, target["id"], topics)
        edited = [t for t in get_topics(client, target["id"]) if t["name"] == name][0]
        assert edited["note"] == "editado no GR2"
        for g in gks:
            if g["id"] == target["id"] or g["id"] == gks[0]["id"]:
                continue
            got = [t for t in get_topics(client, g["id"]) if t["name"] == name]
            assert got and got[0]["note"] == "", f"{g['name']} received edit: {got[0]['note']!r}"

    def test_delete_does_not_propagate(self, client, gks):
        name = TestPropagation.name
        target = gks[1]
        topics = [strip(t) for t in get_topics(client, target["id"]) if t["name"] != name]
        put_subgame(client, target["id"], topics)
        assert not [t for t in get_topics(client, target["id"]) if t["name"] == name]
        for g in gks[2:]:
            got = [t for t in get_topics(client, g["id"]) if t["name"] == name]
            assert len(got) == 1, f"{g['name']} lost topic after delete on other GK"

    def test_empty_name_no_op(self, client, gks):
        r = client.post(f"{API}/subgames/propagate-topic",
                        json={"subgame": SUBGAME, "exclude_gk_id": gks[0]["id"],
                              "topic": {"name": "   "}}, timeout=30)
        assert r.status_code == 200
        assert r.json().get("added") == 0

    def test_requires_auth(self, gks):
        r = requests.post(f"{API}/subgames/propagate-topic",
                          json={"subgame": SUBGAME, "exclude_gk_id": gks[0]["id"],
                                "topic": {"name": f"{PREFIX}NoAuth"}}, timeout=30)
        assert r.status_code in (401, 403), f"unauthenticated propagate returned {r.status_code}"
