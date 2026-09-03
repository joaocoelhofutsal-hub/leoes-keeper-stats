from dotenv import load_dotenv
from pathlib import Path
import os

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import logging
import io
import uuid
import base64
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Annotated

import bcrypt
import jwt
import requests
from bson import ObjectId
from fastapi import FastAPI, APIRouter, Request, Response, HTTPException, Depends, UploadFile, File
from fastapi.responses import StreamingResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, BeforeValidator, ConfigDict

# ---------- DB ----------
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

JWT_ALGORITHM = "HS256"
JWT_SECRET = os.environ["JWT_SECRET"]

app = FastAPI()
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------- Helpers ----------
def _oid(v):
    if isinstance(v, ObjectId):
        return str(v)
    return v

PyObjectId = Annotated[str, BeforeValidator(_oid)]


def _as_oid(v: str) -> ObjectId:
    try:
        return ObjectId(v)
    except Exception:
        raise HTTPException(status_code=400, detail="Identificador inválido.")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def create_access_token(user_id: str, email: str) -> str:
    payload = {"sub": user_id, "email": email,
               "exp": datetime.now(timezone.utc) + timedelta(hours=12), "type": "access"}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    payload = {"sub": user_id, "exp": datetime.now(timezone.utc) + timedelta(days=7), "type": "refresh"}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def set_auth_cookies(response: Response, uid: str, email: str):
    response.set_cookie("access_token", create_access_token(uid, email), httponly=True,
                        secure=True, samesite="none", max_age=43200, path="/")
    response.set_cookie("refresh_token", create_refresh_token(uid), httponly=True,
                        secure=True, samesite="none", max_age=604800, path="/")


async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Não autenticado")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Token inválido")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="Utilizador não encontrado")
        user["_id"] = str(user["_id"])
        user.pop("password_hash", None)
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Sessão expirada")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")


# ---------- Models ----------
class RegisterIn(BaseModel):
    email: str
    password: str
    name: Optional[str] = ""


class LoginIn(BaseModel):
    email: str
    password: str


class PointItem(BaseModel):
    text: str
    source: Optional[str] = ""


class GoalkeeperIn(BaseModel):
    name: str
    team: Optional[str] = ""
    photo: Optional[str] = ""
    strong_points: List[PointItem] = []
    weak_points: List[PointItem] = []


class ImportPayload(BaseModel):
    goalkeepers: List[dict] = []
    reports: List[dict] = []


class TrainingIn(BaseModel):
    goalkeeper_id: Optional[str] = ""
    goalkeeper_name: Optional[str] = ""
    mode: str
    rounds: int = 0
    avg_ms: int = 0
    best_ms: int = 0
    too_soon: int = 0


class ExerciseIn(BaseModel):
    title: str
    description: Optional[str] = ""
    components: List[str] = []
    image: Optional[str] = ""


class BulkExItem(BaseModel):
    title: str
    description: Optional[str] = ""
    components: List[str] = []


class BulkExIn(BaseModel):
    items: List[BulkExItem] = []
    guess: bool = True


class VideoIn(BaseModel):
    title: str
    url: str
    description: Optional[str] = ""
    components: List[str] = []


class TrainingUnitIn(BaseModel):
    title: str
    date: Optional[str] = ""
    notes: Optional[str] = ""
    exercise_ids: List[str] = []


class Action(BaseModel):
    model_config = ConfigDict(extra="allow")
    situation: Optional[str] = ""
    zone: Optional[str] = ""
    distance: Optional[str] = ""
    finish_type: Optional[str] = ""
    technique: Optional[str] = ""
    decisions: List[str] = []
    followup: Optional[str] = ""
    evaluation: Optional[str] = ""
    feedback: Optional[str] = ""
    notes: Optional[str] = ""


class Offensive(BaseModel):
    passes_ok: int = 0
    passes_err: int = 0
    shots_ok: int = 0
    shots_err: int = 0
    repos_ok: int = 0
    repos_err: int = 0


class ReportIn(BaseModel):
    goalkeeper_id: str
    goalkeeper_name: str
    team: Optional[str] = ""
    session_number: Optional[str] = ""
    opponent: Optional[str] = ""
    date: Optional[str] = ""
    competition: Optional[str] = ""
    result: Optional[str] = ""
    coach_notes: Optional[str] = ""
    actions: List[Action] = []
    offensive: Offensive = Offensive()


class SubgameTopic(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: Optional[str] = ""
    name: str
    note: Optional[str] = ""
    evaluation: Optional[str] = ""
    field: Optional[str] = ""
    value: Optional[str] = ""


class SubgamesIn(BaseModel):
    subgames: dict = {}


class ReferenceIn(BaseModel):
    subgame: str
    gk_id: Optional[str] = ""
    name: Optional[str] = ""
    note: Optional[str] = ""


class PropagateTopicIn(BaseModel):
    subgame: str
    exclude_gk_id: Optional[str] = ""
    topic: dict = {}


class MicrocycleIn(BaseModel):
    name: str
    days: dict = {}


class ScoutingIn(BaseModel):
    model_config = ConfigDict(extra="allow")
    opponent: Optional[str] = ""
    competition: Optional[str] = ""
    round: Optional[str] = ""
    date: Optional[str] = ""
    time: Optional[str] = ""
    venue: Optional[str] = ""
    home_away: Optional[str] = ""
    opponent_logo: Optional[str] = ""
    called_gks: List[dict] = []
    set_pieces: dict = {}
    opposition_players: List[dict] = []
    match_notes: Optional[str] = ""


# ---------- Auth routes ----------
@api_router.post("/auth/register")
async def register(data: RegisterIn, response: Response):
    email = data.email.strip().lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email já registado")
    doc = {"email": email, "password_hash": hash_password(data.password),
           "name": data.name or email.split("@")[0], "role": "coach",
           "created_at": datetime.now(timezone.utc).isoformat()}
    res = await db.users.insert_one(doc)
    uid = str(res.inserted_id)
    set_auth_cookies(response, uid, email)
    return {"id": uid, "email": email, "name": doc["name"], "role": doc["role"]}


@api_router.post("/auth/login")
async def login(data: LoginIn, response: Response):
    email = data.email.strip().lower()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    uid = str(user["_id"])
    set_auth_cookies(response, uid, email)
    return {"id": uid, "email": email, "name": user.get("name"), "role": user.get("role")}


@api_router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"ok": True}


@api_router.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return {"id": user["_id"], "email": user["email"], "name": user.get("name"), "role": user.get("role")}


# ---------- Goalkeepers ----------
@api_router.get("/goalkeepers")
async def list_goalkeepers(user: dict = Depends(get_current_user)):
    gks = await db.goalkeepers.find().sort("name", 1).to_list(1000)
    out = []
    for g in gks:
        gid = str(g["_id"])
        count = await db.reports.count_documents({"goalkeeper_id": gid, "loose": {"$ne": True}})
        out.append({"id": gid, "name": g["name"], "team": g.get("team", ""),
                    "photo": g.get("photo", ""),
                    "strong_points": g.get("strong_points", []),
                    "weak_points": g.get("weak_points", []),
                    "report_count": count})
    return out


@api_router.post("/goalkeepers")
async def create_goalkeeper(data: GoalkeeperIn, user: dict = Depends(get_current_user)):
    doc = data.model_dump()
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    res = await db.goalkeepers.insert_one(doc)
    return {"id": str(res.inserted_id), **data.model_dump(), "report_count": 0}


@api_router.put("/goalkeepers/{gid}")
async def update_goalkeeper(gid: str, data: GoalkeeperIn, user: dict = Depends(get_current_user)):
    await db.goalkeepers.update_one({"_id": ObjectId(gid)}, {"$set": data.model_dump()})
    return {"id": gid, **data.model_dump()}


@api_router.delete("/goalkeepers/{gid}")
async def delete_goalkeeper(gid: str, user: dict = Depends(get_current_user)):
    await db.goalkeepers.delete_one({"_id": ObjectId(gid)})
    await db.reports.delete_many({"goalkeeper_id": gid})
    return {"ok": True}


@api_router.post("/goalkeepers/{gid}/photo")
async def upload_gk_photo(gid: str, file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    data = await file.read()
    b64 = "data:" + (file.content_type or "image/png") + ";base64," + base64.b64encode(data).decode()
    await db.goalkeepers.update_one({"_id": ObjectId(gid)}, {"$set": {"photo": b64}})
    return {"photo": b64}


@api_router.post("/import")
async def import_data(payload: ImportPayload, user: dict = Depends(get_current_user)):
    now = datetime.now(timezone.utc).isoformat()
    id_map = {}
    gk_count = 0
    rep_count = 0
    for g in payload.goalkeepers:
        old = g.get("id") or str(g.get("_id", ""))
        doc = {"name": g.get("name", "GR"), "team": g.get("team", ""),
               "photo": g.get("photo", ""),
               "strong_points": g.get("strong_points", []),
               "weak_points": g.get("weak_points", []), "created_at": now}
        res = await db.goalkeepers.insert_one(doc)
        if old:
            id_map[old] = str(res.inserted_id)
        gk_count += 1
    for r in payload.reports:
        gid = id_map.get(r.get("goalkeeper_id"), r.get("goalkeeper_id", ""))
        doc = {k: v for k, v in r.items() if k not in ("id", "_id")}
        doc["goalkeeper_id"] = gid
        doc.setdefault("created_at", now)
        await db.reports.insert_one(doc)
        rep_count += 1
    return {"goalkeepers": gk_count, "reports": rep_count}


# ---------- Reports ----------
def serialize_report(r):
    r["id"] = str(r.pop("_id"))
    return r


@api_router.post("/reports")
async def create_report(data: ReportIn, user: dict = Depends(get_current_user)):
    doc = data.model_dump()
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    res = await db.reports.insert_one(doc)
    return {"id": str(res.inserted_id)}


@api_router.get("/goalkeepers/{gid}/reports")
async def gk_reports(gid: str, user: dict = Depends(get_current_user)):
    reports = await db.reports.find({"goalkeeper_id": gid, "loose": {"$ne": True}}).sort("created_at", -1).to_list(1000)
    return [serialize_report(r) for r in reports]


@api_router.get("/reports/{rid}")
async def get_report(rid: str, user: dict = Depends(get_current_user)):
    r = await db.reports.find_one({"_id": ObjectId(rid)})
    if not r:
        raise HTTPException(status_code=404, detail="Relatório não encontrado")
    return serialize_report(r)


@api_router.delete("/reports/{rid}")
async def delete_report(rid: str, user: dict = Depends(get_current_user)):
    await db.reports.delete_one({"_id": ObjectId(rid)})
    return {"ok": True}


# ---------- Profile / trends ----------
def _most_common(items):
    from collections import Counter
    items = [i for i in items if i]
    if not items:
        return None, 0
    c = Counter(items).most_common(1)[0]
    return c[0], c[1]


def compute_profile(reports):
    from collections import Counter
    game_reports = [r for r in reports if not r.get("loose")]
    total = len(game_reports)
    all_actions = []
    green_game = []
    game_action_count = 0
    off = {"passes_ok": 0, "passes_err": 0, "shots_ok": 0, "shots_err": 0, "repos_ok": 0, "repos_err": 0}
    for r in reports:
        acts = r.get("actions", []) or []
        all_actions.extend(acts)
        if not r.get("loose"):
            game_action_count += len(acts)
            green_game.append(sum(1 for a in acts if a.get("evaluation") == "verde"))
        o = r.get("offensive", {}) or {}
        for k in off:
            off[k] += int(o.get(k, 0) or 0)

    n_actions = len(all_actions)
    avg_actions = round(game_action_count / total, 1) if total else 0
    avg_green = round(sum(green_game) / total, 1) if total else 0

    techniques = [a.get("technique") for a in all_actions]
    decisions = [d for a in all_actions for d in (a.get("decisions") or [])]
    followups = [a.get("followup") for a in all_actions]

    top_tech, _ = _most_common(techniques)
    top_dec, _ = _most_common(decisions)
    top_follow, _ = _most_common(followups)

    # Style
    style = "Sem dados suficientes"
    if top_tech:
        if top_tech in ("Barreirista", "Aguardar em flexão", "Parede"):
            style = "Guarda-redes de bloqueio e ocupação de espaço"
        elif top_tech in ("Projeção no ar", "Queda lateral"):
            style = "Guarda-redes reativo e explosivo"
        elif top_tech in ("Saída de joelhos", "Defesa com as pernas"):
            style = "Guarda-redes de saída e redução de ângulo"
        elif top_tech == "Passe":
            style = "Guarda-redes participativo na construção"
        else:
            style = f"Predomínio de {top_tech}"

    # Trends (>=3 occurrences)
    trends = []

    if top_follow:
        fc = Counter(followups)[top_follow]
        if fc >= 3:
            trends.append(f"Seguimento mais frequente: {top_follow} ({fc}).")

    # distance -> technique + followup
    by_dist = {}
    for a in all_actions:
        d = a.get("distance")
        if not d:
            continue
        by_dist.setdefault(d, {"tech": [], "follow": []})
        if a.get("technique"):
            by_dist[d]["tech"].append(a["technique"])
        if a.get("followup"):
            by_dist[d]["follow"].append(a["followup"])
    for d, vals in by_dist.items():
        t, tc = _most_common(vals["tech"])
        f, fc = _most_common(vals["follow"])
        if t and tc >= 3:
            extra = f" e a bola termina mais em {f}" if (f and fc >= 3) else ""
            trends.append(f"Nos remates a {d}, usa mais {t}{extra} ({tc}).")

    # zone -> technique
    by_zone = {}
    for a in all_actions:
        z = a.get("zone")
        if z and a.get("technique"):
            by_zone.setdefault(z, []).append(a["technique"])
    for z, techs in by_zone.items():
        t, tc = _most_common(techs)
        if t and tc >= 3:
            trends.append(f"No {z.lower()}, maior tendência para usar {t} ({tc}).")

    # zone -> followup
    by_zone_f = {}
    for a in all_actions:
        z = a.get("zone")
        f = a.get("followup")
        if z and f:
            by_zone_f.setdefault(z, []).append(f)
    for z, fs in by_zone_f.items():
        f, fc = _most_common(fs)
        if f and fc >= 3:
            trends.append(f"No {z.lower()}, a bola termina mais em {f} ({fc}).")

    # decision (avoid Enquadramento as main)
    dec_counter = Counter([d for d in decisions if d])
    for dec, cnt in dec_counter.most_common():
        if dec == "Enquadramento":
            continue
        if cnt >= 3:
            trends.append(f"Tomada de decisão frequente: {dec} ({cnt}).")
            break

    # Offensive fails (only with >=3 errors, with fraction)
    def _off_trend(err, ok, label):
        tot = ok + err
        if tot > 0 and err >= 3:
            pct = round(err / tot * 100)
            trends.append(f"Falhou {pct}% {label} ({err}/{tot}).")
    _off_trend(off["passes_err"], off["passes_ok"], "dos passes em geral")
    _off_trend(off["shots_err"], off["shots_ok"], "dos remates")
    _off_trend(off["repos_err"], off["repos_ok"], "das reposições")

    def dist(items):
        c = Counter([i for i in items if i])
        return [{"name": k, "value": v} for k, v in c.most_common()]

    evals = [a.get("evaluation") for a in all_actions]
    eval_dist = []
    for key in ["verde", "amarelo", "vermelho", "cinzenta"]:
        eval_dist.append({"name": key, "value": Counter([e for e in evals if e])[key]})

    distributions = {
        "evaluation": eval_dist,
        "technique": dist(techniques),
        "followup": dist(followups),
        "zone": dist([a.get("zone") for a in all_actions]),
        "distance": dist([a.get("distance") for a in all_actions]),
    }

    return {
        "total_reports": total,
        "total_actions": n_actions,
        "avg_actions_per_game": avg_actions,
        "avg_green_per_report": avg_green,
        "style": style,
        "top_decision": top_dec,
        "top_technique": top_tech,
        "top_followup": top_follow,
        "trends": trends,
        "offensive_totals": off,
        "distributions": distributions,
    }


@api_router.get("/goalkeepers/{gid}/profile")
async def gk_profile(gid: str, user: dict = Depends(get_current_user)):
    reports = await db.reports.find({"goalkeeper_id": gid}).to_list(1000)
    return compute_profile(reports)


# ---------- Loose actions (ações soltas) ----------
async def _all_gk_actions(gid: str):
    reports = await db.reports.find({"goalkeeper_id": gid}).to_list(1000)
    acts = []
    for r in reports:
        acts.extend(r.get("actions", []) or [])
    return acts


OFF_KEYS = ["passes_ok", "passes_err", "shots_ok", "shots_err", "repos_ok", "repos_err"]
SUCCESS_EVALS = ("verde", "cinzenta")
OFF_MAP = {"passes": ("passes_ok", "passes_err"), "shots": ("shots_ok", "shots_err"), "repos": ("repos_ok", "repos_err")}


def _match_action(a, field, value):
    if field == "decisions":
        return value in (a.get("decisions") or [])
    return (a.get(field) or "") == value


def _metric_from(actions, off, field, value, field2="", value2=""):
    if not field or not value:
        return None
    if field == "offensive":
        vals = [value] + ([value2] if field2 == "offensive" and value2 else [])
        ok = 0
        err = 0
        for v in vals:
            if v in OFF_MAP:
                okk, errk = OFF_MAP[v]
                ok += int(off.get(okk, 0) or 0)
                err += int(off.get(errk, 0) or 0)
        count = ok + err
        pct = round(ok / count * 100) if count else 0
        return {"count": count, "success": ok, "pct": pct}
    cross = bool(field2) and bool(value2) and field2 != "offensive"
    matching = [a for a in actions if _match_action(a, field, value) and (not cross or _match_action(a, field2, value2))]
    count = len(matching)
    success = sum(1 for a in matching if a.get("evaluation") in SUCCESS_EVALS)
    pct = round(success / count * 100) if count else 0
    return {"count": count, "success": success, "pct": pct}


async def _squad_data():
    reports = await db.reports.find().to_list(5000)
    data = {}
    for r in reports:
        gid = r.get("goalkeeper_id", "")
        d = data.setdefault(gid, {"actions": [], "off": {k: 0 for k in OFF_KEYS}})
        d["actions"].extend(r.get("actions", []) or [])
        o = r.get("offensive", {}) or {}
        for k in OFF_KEYS:
            d["off"][k] += int(o.get(k, 0) or 0)
    return data


@api_router.get("/goalkeepers/{gid}/loose-actions")
async def get_loose_actions(gid: str, user: dict = Depends(get_current_user)):
    rep = await db.reports.find_one({"goalkeeper_id": gid, "loose": True})
    return (rep or {}).get("actions", [])


@api_router.post("/goalkeepers/{gid}/loose-actions")
async def add_loose_action(gid: str, data: Action, user: dict = Depends(get_current_user)):
    act = data.model_dump()
    now = datetime.now(timezone.utc).isoformat()
    act["id"] = str(uuid.uuid4())
    act["created_at"] = now
    await db.reports.update_one(
        {"goalkeeper_id": gid, "loose": True},
        {"$push": {"actions": act},
         "$setOnInsert": {"goalkeeper_id": gid, "loose": True,
                          "session_number": "Ações soltas", "created_at": now, "offensive": {}}},
        upsert=True,
    )
    return act


@api_router.delete("/goalkeepers/{gid}/loose-actions/{aid}")
async def del_loose_action(gid: str, aid: str, user: dict = Depends(get_current_user)):
    await db.reports.update_one({"goalkeeper_id": gid, "loose": True}, {"$pull": {"actions": {"id": aid}}})
    return {"ok": True}


# ---------- Sub-jogos (sub-game evaluations) ----------
@api_router.get("/goalkeepers/{gid}/subgames")
async def get_subgames(gid: str, user: dict = Depends(get_current_user)):
    doc = await db.subgame_evals.find_one({"goalkeeper_id": gid})
    subgames = (doc or {}).get("subgames", {})
    data = await _squad_data()
    gks = await db.goalkeepers.find().to_list(1000)
    name_by_id = {str(g["_id"]): g["name"] for g in gks}
    me = data.get(gid, {"actions": [], "off": {k: 0 for k in OFF_KEYS}})
    for sg, topics in subgames.items():
        for t in topics:
            f, v = t.get("field"), t.get("value")
            f2, v2 = t.get("field2"), t.get("value2")
            mr = _metric_from(me["actions"], me["off"], f, v, f2, v2)
            t["metric_result"] = mr
            t["benchmark"] = None
            t["auto_eval"] = None
            bid = t.get("benchmark_gk_id")
            if mr and mr["count"] > 0 and bid and bid in data:
                bm = _metric_from(data[bid]["actions"], data[bid]["off"], f, v, f2, v2)
                if bm and bm["count"] > 0:
                    is_best = (bid == gid)
                    ratio = mr["pct"] / bm["pct"] if bm["pct"] > 0 else 1
                    t["benchmark"] = {"best_pct": bm["pct"], "best_gk": name_by_id.get(bid, "—"), "best_count": bm["count"], "is_best": is_best}
                    t["auto_eval"] = "verde" if (is_best or ratio >= 0.9) else ("amarelo" if ratio >= 0.7 else "vermelho")
    return {"subgames": subgames}


@api_router.put("/goalkeepers/{gid}/subgames")
async def save_subgames(gid: str, data: SubgamesIn, user: dict = Depends(get_current_user)):
    await db.subgame_evals.update_one(
        {"goalkeeper_id": gid},
        {"$set": {"goalkeeper_id": gid, "subgames": data.subgames}},
        upsert=True,
    )
    return {"ok": True}


@api_router.post("/subgames/propagate-topic")
async def propagate_topic(data: PropagateTopicIn, user: dict = Depends(get_current_user)):
    name = (data.topic.get("name") or "").strip()
    if not name:
        return {"added": 0}
    base = {
        "name": name, "evaluation": "", "note": "",
        "field": data.topic.get("field", ""), "value": data.topic.get("value", ""),
        "field2": data.topic.get("field2", ""), "value2": data.topic.get("value2", ""),
        "benchmark_gk_id": data.topic.get("benchmark_gk_id", ""),
    }
    lname = name.lower()
    gks = await db.goalkeepers.find().to_list(1000)
    added = 0
    for g in gks:
        gid = str(g["_id"])
        if gid == data.exclude_gk_id:
            continue
        doc = await db.subgame_evals.find_one({"goalkeeper_id": gid})
        subgames = (doc or {}).get("subgames", {}) or {}
        topics = subgames.get(data.subgame, []) or []
        if any((t.get("name", "").strip().lower() == lname) for t in topics):
            continue
        topics.append({"id": str(uuid.uuid4()), **base})
        subgames[data.subgame] = topics
        await db.subgame_evals.update_one(
            {"goalkeeper_id": gid},
            {"$set": {"goalkeeper_id": gid, "subgames": subgames}},
            upsert=True,
        )
        added += 1
    return {"added": added}


# ---------- Logo settings ----------
@api_router.get("/references")
async def list_references(user: dict = Depends(get_current_user)):
    rows = await db.references.find().sort("created_at", -1).to_list(1000)
    for r in rows:
        r["id"] = str(r.pop("_id"))
    return rows


@api_router.post("/references")
async def create_reference(data: ReferenceIn, user: dict = Depends(get_current_user)):
    doc = data.model_dump()
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    res = await db.references.insert_one(doc)
    return {"id": str(res.inserted_id), **data.model_dump()}


@api_router.delete("/references/{rid}")
async def delete_reference(rid: str, user: dict = Depends(get_current_user)):
    await db.references.delete_one({"_id": _as_oid(rid)})
    return {"ok": True}


# ---------- Microcycles (microciclos) ----------
@api_router.get("/microcycles")
async def list_microcycles(user: dict = Depends(get_current_user)):
    import re
    rows = await db.microcycles.find().to_list(500)

    def _key(r):
        name = (r.get("name", "") or "")
        return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", name)]

    rows.sort(key=_key)
    return [{"id": str(r["_id"]), "name": r.get("name", "")} for r in rows]


@api_router.get("/microcycles/{mid}")
async def get_microcycle(mid: str, user: dict = Depends(get_current_user)):
    m = await db.microcycles.find_one({"_id": _as_oid(mid)})
    if not m:
        raise HTTPException(status_code=404, detail="Microciclo não encontrado.")
    return {"id": str(m["_id"]), "name": m.get("name", ""), "days": m.get("days", {})}


@api_router.post("/microcycles")
async def create_microcycle(data: MicrocycleIn, user: dict = Depends(get_current_user)):
    doc = data.model_dump()
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    res = await db.microcycles.insert_one(doc)
    return {"id": str(res.inserted_id), "name": data.name, "days": data.days}


@api_router.put("/microcycles/{mid}")
async def update_microcycle(mid: str, data: MicrocycleIn, user: dict = Depends(get_current_user)):
    res = await db.microcycles.update_one({"_id": _as_oid(mid)}, {"$set": data.model_dump()})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Microciclo não encontrado.")
    return {"id": mid, "name": data.name, "days": data.days}


@api_router.delete("/microcycles/{mid}")
async def delete_microcycle(mid: str, user: dict = Depends(get_current_user)):
    m = await db.microcycles.find_one({"_id": _as_oid(mid)})
    if m:
        gids = [ev.get("id") for day in (m.get("days") or {}).values()
                for ev in (day or []) if ev.get("type") == "jogo" and ev.get("id")]
        if gids:
            await db.scouting_plans.delete_many({"game_id": {"$in": gids}})
    await db.microcycles.delete_one({"_id": _as_oid(mid)})
    return {"ok": True}


# ---------- Scouting & Match Plan ----------
@api_router.get("/scouting/{game_id}")
async def get_scouting(game_id: str, user: dict = Depends(get_current_user)):
    doc = await db.scouting_plans.find_one({"game_id": game_id})
    if not doc:
        return {"game_id": game_id, "exists": False}
    doc["id"] = str(doc.pop("_id"))
    doc["exists"] = True
    return doc


@api_router.put("/scouting/{game_id}")
async def save_scouting(game_id: str, data: ScoutingIn, user: dict = Depends(get_current_user)):
    payload = data.model_dump()
    payload["game_id"] = game_id
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.scouting_plans.update_one({"game_id": game_id}, {"$set": payload}, upsert=True)
    return {"ok": True}


@api_router.delete("/scouting/{game_id}")
async def delete_scouting(game_id: str, user: dict = Depends(get_current_user)):
    await db.scouting_plans.delete_one({"game_id": game_id})
    return {"ok": True}


@api_router.get("/settings/logo")
async def get_logo(user: dict = Depends(get_current_user)):
    s = await db.settings.find_one({"key": "logo"})
    return {"logo": s["value"] if s else None}


@api_router.post("/settings/logo")
async def upload_logo(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    data = await file.read()
    b64 = "data:" + (file.content_type or "image/png") + ";base64," + base64.b64encode(data).decode()
    await db.settings.update_one({"key": "logo"}, {"$set": {"value": b64}}, upsert=True)
    return {"logo": b64}


# ---------- Export ----------
@api_router.get("/export")
async def export_data(user: dict = Depends(get_current_user)):
    gks = await db.goalkeepers.find().to_list(1000)
    reports = await db.reports.find().to_list(5000)
    for g in gks:
        g["id"] = str(g.pop("_id"))
    for r in reports:
        r["id"] = str(r.pop("_id"))
    return {"goalkeepers": gks, "reports": reports}


# ---------- Insights (dados gerais) ----------
@api_router.get("/insights/general")
async def insights_general(user: dict = Depends(get_current_user)):
    from collections import Counter
    reports = await db.reports.find().to_list(5000)
    gk_count = await db.goalkeepers.count_documents({})
    total_actions = 0
    eval_counter = Counter()
    sit_counter = Counter()
    by_sit = {}
    off = {"passes_ok": 0, "passes_err": 0, "shots_ok": 0, "shots_err": 0, "repos_ok": 0, "repos_err": 0}
    for r in reports:
        o = r.get("offensive", {}) or {}
        for k in off:
            off[k] += int(o.get(k, 0) or 0)
        for a in r.get("actions", []):
            total_actions += 1
            ev = a.get("evaluation")
            if ev:
                eval_counter[ev] += 1
            s = a.get("situation")
            if s:
                sit_counter[s] += 1
                c = by_sit.setdefault(s, Counter())
                for d in (a.get("decisions") or []):
                    c[d] += 1
    decisions_by_situation = []
    for s, c in sorted(by_sit.items(), key=lambda kv: -sit_counter[kv[0]]):
        tot = sum(c.values())
        items = [{"name": d, "count": n, "pct": round(n / tot * 100) if tot else 0} for d, n in c.most_common()]
        decisions_by_situation.append({"situation": s, "total": sit_counter[s], "decisions": items})
    return {
        "goalkeepers": gk_count,
        "reports": sum(1 for r in reports if not r.get("loose")),
        "total_actions": total_actions,
        "evaluation": [{"name": k, "value": eval_counter.get(k, 0)} for k in ["verde", "amarelo", "vermelho", "cinzenta"]],
        "offensive_totals": off,
        "decisions_by_situation": decisions_by_situation,
    }


# ---------- Training (jogo de reação) ----------
@api_router.get("/insights/squad")
async def insights_squad(user: dict = Depends(get_current_user)):
    gks = await db.goalkeepers.find().sort("name", 1).to_list(1000)
    reports = await db.reports.find().to_list(5000)
    training = await db.training.find().to_list(5000)
    out = []
    tot_games = 0
    tot_actions = 0
    tot_success = 0
    for g in gks:
        gid = str(g["_id"])
        greps = [r for r in reports if r.get("goalkeeper_id") == gid]
        games = sum(1 for r in greps if not r.get("loose"))
        acts = [a for r in greps for a in (r.get("actions") or [])]
        n = len(acts)
        succ = sum(1 for a in acts if a.get("evaluation") in SUCCESS_EVALS)
        pct = round(succ / n * 100) if n else 0
        tr = [t for t in training if t.get("goalkeeper_id") == gid]
        bests = [t.get("best_ms") for t in tr if t.get("best_ms")]
        avgs = [t.get("avg_ms") for t in tr if t.get("avg_ms")]
        out.append({
            "id": gid, "name": g.get("name", ""), "team": g.get("team", ""),
            "photo": g.get("photo", ""),
            "games": games, "total_actions": n, "success_pct": pct,
            "best_reaction_ms": min(bests) if bests else None,
            "avg_reaction_ms": round(sum(avgs) / len(avgs)) if avgs else None,
        })
        tot_games += games
        tot_actions += n
        tot_success += succ
    totals = {
        "goalkeepers": len(gks),
        "games": tot_games,
        "total_actions": tot_actions,
        "success_pct": round(tot_success / tot_actions * 100) if tot_actions else 0,
    }
    return {"goalkeepers": out, "totals": totals}


@api_router.post("/training")
async def save_training(data: TrainingIn, user: dict = Depends(get_current_user)):
    doc = data.model_dump()
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    res = await db.training.insert_one(doc)
    return {"id": str(res.inserted_id)}


@api_router.get("/goalkeepers/{gid}/training")
async def gk_training(gid: str, user: dict = Depends(get_current_user)):
    rows = await db.training.find({"goalkeeper_id": gid}).sort("created_at", -1).to_list(200)
    for r in rows:
        r["id"] = str(r.pop("_id"))
    return rows


# ---------- Exercises (caderno) ----------
@api_router.get("/exercises")
async def list_exercises(component: Optional[str] = None, user: dict = Depends(get_current_user)):
    q = {"components": component} if component else {}
    rows = await db.exercises.find(q).sort("title", 1).to_list(1000)
    for r in rows:
        r["id"] = str(r.pop("_id"))
    return rows


@api_router.get("/exercises/components")
async def exercise_components(user: dict = Depends(get_current_user)):
    vals = await db.exercises.distinct("components")
    return sorted([v for v in vals if v])


@api_router.post("/exercises")
async def create_exercise(data: ExerciseIn, user: dict = Depends(get_current_user)):
    doc = data.model_dump()
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    res = await db.exercises.insert_one(doc)
    return {"id": str(res.inserted_id), **data.model_dump()}


@api_router.put("/exercises/{eid}")
async def update_exercise(eid: str, data: ExerciseIn, user: dict = Depends(get_current_user)):
    res = await db.exercises.update_one({"_id": _as_oid(eid)}, {"$set": data.model_dump()})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Exercício não encontrado.")
    return {"id": eid, **data.model_dump()}


@api_router.delete("/exercises/{eid}")
async def delete_exercise(eid: str, user: dict = Depends(get_current_user)):
    await db.exercises.delete_one({"_id": _as_oid(eid)})
    return {"ok": True}


COMPONENT_KEYWORDS = {
    "Potência": ["potência", "potencia", "explosiv", "salto", "pliom", "impulsão", "impulsao"],
    "Agilidade": ["agilidade", "mudança de direção", "mudanca de direcao", "escada", "skipping", "deslocament"],
    "Força": ["força", "forca", "core", "abdominal", "agachament", "resistência", "resistencia"],
    "Velocidade de reação": ["reação", "reacao", "reflexo", "estímulo", "estimulo", "sinal", "luz", "cores", "reativ", "resposta"],
    "Mobilidade": ["mobilidade", "alongament", "flexibilidade", "amplitude"],
    "Ativação": ["ativação", "ativacao", "aqueciment", "warm", "ativaç"],
    "Coordenação": ["coordenação", "coordenacao", "óculo", "oculo", "manual", "ritmo", "malabar"],
}


def guess_components(text: str) -> List[str]:
    t = (text or "").lower()
    out = []
    for comp, kws in COMPONENT_KEYWORDS.items():
        if any(k in t for k in kws):
            out.append(comp)
    return out


@api_router.post("/exercises/bulk")
async def bulk_exercises(data: BulkExIn, user: dict = Depends(get_current_user)):
    now = datetime.now(timezone.utc).isoformat()
    created = 0
    for it in data.items:
        title = (it.title or "").strip()
        if not title:
            continue
        comps = it.components or (guess_components(f"{title} {it.description or ''}") if data.guess else [])
        await db.exercises.insert_one({
            "title": title[:120], "description": it.description or "",
            "components": comps, "image": "", "created_at": now,
        })
        created += 1
    return {"created": created}


@api_router.post("/exercises/import-doc")
async def import_doc(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    import subprocess
    import tempfile
    import shutil
    from shutil import which as shutil_which
    import pymupdf

    raw = await file.read()
    name = (file.filename or "").lower()
    tmpdir = tempfile.mkdtemp()
    titles = []
    pdf_path = None

    try:
        if name.endswith(".pdf"):
            pdf_path = os.path.join(tmpdir, "in.pdf")
            with open(pdf_path, "wb") as f:
                f.write(raw)
        elif name.endswith(".pptx"):
            pptx_path = os.path.join(tmpdir, "in.pptx")
            with open(pptx_path, "wb") as f:
                f.write(raw)
            # slide titles via python-pptx
            try:
                from pptx import Presentation
                prs = Presentation(pptx_path)
                for slide in prs.slides:
                    t = ""
                    try:
                        if slide.shapes.title and slide.shapes.title.text.strip():
                            t = slide.shapes.title.text.strip()
                    except Exception:
                        t = ""
                    if not t:
                        for sh in slide.shapes:
                            if sh.has_text_frame and sh.text_frame.text.strip():
                                t = sh.text_frame.text.strip().split("\n")[0]
                                break
                    titles.append(t)
            except Exception as e:
                logger.warning(f"pptx title extraction failed: {e}")
                titles = []
            # render via LibreOffice if available
            soffice_bin = shutil_which("soffice") or shutil_which("libreoffice")
            if not soffice_bin:
                raise HTTPException(status_code=400, detail="Para importar .pptx exporta primeiro como PDF no PowerPoint (Ficheiro > Exportar > PDF) e carrega o PDF.")
            try:
                subprocess.run([soffice_bin, "--headless", "--convert-to", "pdf", "--outdir", tmpdir, pptx_path],
                               check=True, timeout=180)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Falha a converter PPTX: {e}. Exporta como PDF e tenta novamente.")
            pdfs = [f for f in os.listdir(tmpdir) if f.lower().endswith(".pdf")]
            if not pdfs:
                raise HTTPException(status_code=400, detail="Não foi possível renderizar o PPTX. Exporta como PDF e tenta novamente.")
            pdf_path = os.path.join(tmpdir, pdfs[0])
        else:
            raise HTTPException(status_code=400, detail="Formato não suportado. Carrega um PDF ou um .pptx.")

        doc = pymupdf.open(pdf_path)
        now = datetime.now(timezone.utc).isoformat()
        created = 0
        for i in range(doc.page_count):
            pix = doc[i].get_pixmap(dpi=110)
            img = "data:image/png;base64," + base64.b64encode(pix.tobytes("png")).decode()
            title = (titles[i] if i < len(titles) and titles[i] else f"Exercício {i + 1}")[:120]
            comps = guess_components(title)
            await db.exercises.insert_one({
                "title": title, "description": "", "components": comps,
                "image": img, "created_at": now,
            })
            created += 1
        doc.close()
        return {"created": created}
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ---------- Training videos ----------
@api_router.get("/videos")
async def list_videos(component: Optional[str] = None, user: dict = Depends(get_current_user)):
    q = {"components": component} if component else {}
    rows = await db.videos.find(q).sort("created_at", -1).to_list(1000)
    for r in rows:
        r["id"] = str(r.pop("_id"))
    return rows


@api_router.post("/videos")
async def create_video(data: VideoIn, user: dict = Depends(get_current_user)):
    doc = data.model_dump()
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    res = await db.videos.insert_one(doc)
    return {"id": str(res.inserted_id), **data.model_dump()}


@api_router.put("/videos/{vid}")
async def update_video(vid: str, data: VideoIn, user: dict = Depends(get_current_user)):
    res = await db.videos.update_one({"_id": _as_oid(vid)}, {"$set": data.model_dump()})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Vídeo não encontrado.")
    return {"id": vid, **data.model_dump()}


@api_router.delete("/videos/{vid}")
async def delete_video(vid: str, user: dict = Depends(get_current_user)):
    await db.videos.delete_one({"_id": _as_oid(vid)})
    return {"ok": True}


# ---------- Training units ----------
@api_router.post("/training-units")
async def create_unit(data: TrainingUnitIn, user: dict = Depends(get_current_user)):
    doc = data.model_dump()
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    res = await db.training_units.insert_one(doc)
    return {"id": str(res.inserted_id)}


@api_router.get("/training-units")
async def list_units(user: dict = Depends(get_current_user)):
    rows = await db.training_units.find().sort("created_at", -1).to_list(500)
    for r in rows:
        r["id"] = str(r.pop("_id"))
    return rows


@api_router.delete("/training-units/{uid}")
async def delete_unit(uid: str, user: dict = Depends(get_current_user)):
    await db.training_units.delete_one({"_id": ObjectId(uid)})
    return {"ok": True}


# ---------- PDF ----------
EVAL_COLORS = {"cinzenta": "#9CA3AF", "verde": "#22C55E", "amarelo": "#EAB308", "vermelho": "#EF4444"}


async def _logo_bytes():
    s = await db.settings.find_one({"key": "logo"})
    if not s:
        return None
    val = s["value"]
    if val.startswith("data:"):
        val = val.split(",", 1)[1]
    try:
        return io.BytesIO(base64.b64decode(val))
    except Exception:
        return None


@api_router.get("/reports/{rid}/pdf")
async def report_pdf(rid: str, request: Request):
    # auth via cookie/header
    await get_current_user(request)
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle, Paragraph,
                                    Spacer, Image as RLImage)

    r = await db.reports.find_one({"_id": ObjectId(rid)})
    if not r:
        raise HTTPException(status_code=404, detail="Relatório não encontrado")

    reports_gk = await db.reports.find({"goalkeeper_id": r["goalkeeper_id"]}).to_list(1000)
    profile = compute_profile(reports_gk)

    DARK_GREEN = colors.HexColor("#0C3B1E")
    PETROL = colors.HexColor("#0F3B43")
    LGREY = colors.HexColor("#F3F4F6")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=15 * mm, bottomMargin=15 * mm,
                            leftMargin=14 * mm, rightMargin=14 * mm)
    styles = getSampleStyleSheet()
    base_font = "Helvetica-BoldOblique"
    title_style = ParagraphStyle("t", parent=styles["Title"], fontName=base_font,
                                 textColor=DARK_GREEN, fontSize=20, spaceAfter=2)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontName=base_font,
                        textColor=PETROL, fontSize=13, spaceBefore=10, spaceAfter=4)
    normal = ParagraphStyle("n", parent=styles["Normal"], fontName="Helvetica", fontSize=9)
    small = ParagraphStyle("s", parent=styles["Normal"], fontName="Helvetica-Oblique", fontSize=8)

    elems = []
    logo = await _logo_bytes()
    logo_img = None
    if logo:
        try:
            logo_img = RLImage(logo, width=18 * mm, height=18 * mm)
        except Exception:
            logo_img = None
    title_block = [Paragraph("RELATÓRIO INDIVIDUAL", title_style),
                   Paragraph("Leões de Porto Salvo", small)]
    htbl = Table([[title_block, logo_img or ""]], colWidths=[None, 22 * mm])
    htbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
    ]))
    elems.append(htbl)
    elems.append(Spacer(1, 4))

    info = [
        ["Guarda-redes", r.get("goalkeeper_name", ""), "Escalão/Equipa", r.get("team", "")],
        ["Nº treino/jogo", r.get("session_number", ""), "Adversário", r.get("opponent", "")],
        ["Data", r.get("date", ""), "Competição", r.get("competition", "")],
        ["Resultado", r.get("result", ""), "Ações", str(len(r.get("actions", [])))],
    ]
    it = Table(info, colWidths=[32 * mm, None, 32 * mm, None])
    it.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (0, -1), LGREY),
        ("BACKGROUND", (2, 0), (2, -1), LGREY),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elems.append(it)

    # Actions table
    elems.append(Paragraph("AÇÕES DE JOGO", h2))
    head = ["#", "Situação", "Zona", "Dist.", "Finalização", "Técnica", "Decisão", "Seguimento", "Aval."]
    data = [head]
    eval_cells = []
    for i, a in enumerate(r.get("actions", []), 1):
        data.append([
            str(i),
            Paragraph(a.get("situation", "") or "", small),
            Paragraph(a.get("zone", "") or "", small),
            Paragraph(a.get("distance", "") or "", small),
            Paragraph(a.get("finish_type", "") or "", small),
            Paragraph(a.get("technique", "") or "", small),
            Paragraph(", ".join(a.get("decisions", []) or []), small),
            Paragraph(a.get("followup", "") or "", small),
            "",
        ])
        eval_cells.append((i, a.get("evaluation")))
    if len(data) == 1:
        data.append(["—"] * len(head))
    at = Table(data, colWidths=[7 * mm, 22 * mm, 24 * mm, 12 * mm, 24 * mm, 24 * mm, 26 * mm, 24 * mm, 12 * mm],
               repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), DARK_GREEN),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D1D5DB")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LGREY]),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    for i, ev in eval_cells:
        if ev in EVAL_COLORS:
            style.append(("BACKGROUND", (8, i), (8, i), colors.HexColor(EVAL_COLORS[ev])))
    at.setStyle(TableStyle(style))
    elems.append(at)

    # Offensive grouped (only non-zero)
    elems.append(Paragraph("AÇÕES OFENSIVAS", h2))
    o = r.get("offensive", {}) or {}
    off_map = [
        ("Passe certo", o.get("passes_ok", 0)), ("Passe errado", o.get("passes_err", 0)),
        ("Remate certo", o.get("shots_ok", 0)), ("Remate errado", o.get("shots_err", 0)),
        ("Reposição certa", o.get("repos_ok", 0)), ("Reposição errada", o.get("repos_err", 0)),
    ]
    off_rows = [[Paragraph(f"<b>{lbl}</b>", normal), str(v)] for lbl, v in off_map if v]
    if off_rows:
        otbl = Table(off_rows, colWidths=[60 * mm, 20 * mm])
        otbl.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D1D5DB")),
            ("BACKGROUND", (0, 0), (0, -1), LGREY),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        elems.append(otbl)
    else:
        elems.append(Paragraph("Sem ações ofensivas registadas.", small))

    # Profile / trends
    elems.append(Paragraph("PERFIL E TENDÊNCIAS", h2))
    elems.append(Paragraph(f"<b>Estilo:</b> {profile['style']}", normal))
    if profile.get("top_technique"):
        elems.append(Paragraph(f"<b>Técnica mais usada:</b> {profile['top_technique']}", normal))
    if profile.get("top_followup"):
        elems.append(Paragraph(f"<b>Seguimento mais frequente:</b> {profile['top_followup']}", normal))
    for t in profile.get("trends", []):
        elems.append(Paragraph("• " + t, normal))
    if not profile.get("trends"):
        elems.append(Paragraph("Sem tendências com base estatística suficiente (mín. 3 ocorrências).", small))

    # Coach notes
    if r.get("coach_notes"):
        elems.append(Paragraph("NOTAS GERAIS DO TREINADOR", h2))
        elems.append(Paragraph(r["coach_notes"], normal))

    doc.build(elems)
    buf.seek(0)

    name = (r.get("goalkeeper_name", "GR") or "GR").strip()
    session = (r.get("session_number", "") or "").strip()
    filename = f"RI {name} {session}".strip() + ".pdf"
    return StreamingResponse(buf, media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@api_router.get("/training-units/{uid}/pdf")
async def unit_pdf(uid: str, request: Request):
    await get_current_user(request)
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle, Paragraph,
                                    Spacer, Image as RLImage)

    u = await db.training_units.find_one({"_id": ObjectId(uid)})
    if not u:
        raise HTTPException(status_code=404, detail="Unidade não encontrada")
    ex_docs = []
    for eid in u.get("exercise_ids", []):
        try:
            e = await db.exercises.find_one({"_id": ObjectId(eid)})
        except Exception:
            e = None
        if e:
            ex_docs.append(e)

    DARK_GREEN = colors.HexColor("#0C3B1E")
    PETROL = colors.HexColor("#0F3B43")
    LGREY = colors.HexColor("#F3F4F6")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=15 * mm, bottomMargin=15 * mm,
                            leftMargin=14 * mm, rightMargin=14 * mm)
    styles = getSampleStyleSheet()
    bf = "Helvetica-BoldOblique"
    title_style = ParagraphStyle("t", parent=styles["Title"], fontName=bf, textColor=DARK_GREEN, fontSize=20, spaceAfter=2)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontName=bf, textColor=PETROL, fontSize=12, spaceBefore=8, spaceAfter=2)
    normal = ParagraphStyle("n", parent=styles["Normal"], fontName="Helvetica", fontSize=9)
    small = ParagraphStyle("s", parent=styles["Normal"], fontName="Helvetica-Oblique", fontSize=8)

    elems = []
    logo = await _logo_bytes()
    logo_img = None
    if logo:
        try:
            logo_img = RLImage(logo, width=18 * mm, height=18 * mm)
        except Exception:
            logo_img = None
    title_block = [Paragraph("UNIDADE DE TREINO", title_style),
                   Paragraph("Leões de Porto Salvo · Guarda-Redes", small)]
    htbl = Table([[title_block, logo_img or ""]], colWidths=[None, 22 * mm])
    htbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (1, 0), (1, 0), "RIGHT")]))
    elems.append(htbl)
    elems.append(Spacer(1, 4))

    info = [["Título", u.get("title", ""), "Data", u.get("date", "")],
            ["Nº de exercícios", str(len(ex_docs)), "", ""]]
    it = Table(info, colWidths=[34 * mm, None, 22 * mm, 40 * mm])
    it.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"), ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (0, -1), LGREY), ("BACKGROUND", (2, 0), (2, -1), LGREY),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"), ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elems.append(it)

    elems.append(Paragraph("EXERCÍCIOS", h2))
    from PIL import Image as PILImage

    def img_flow(b64):
        try:
            raw = b64.split(",", 1)[1] if b64.startswith("data:") else b64
            data = base64.b64decode(raw)
            bio = io.BytesIO(data)
            pil = PILImage.open(bio)
            w, h = pil.size
            ratio = (h / w) if w else 0.6
            bio.seek(0)
            iw = 78 * mm
            ih = min(iw * ratio, 62 * mm)
            return RLImage(bio, width=iw, height=ih)
        except Exception:
            return None

    for i, e in enumerate(ex_docs, 1):
        comps = ", ".join(e.get("components", []) or [])
        elems.append(Paragraph(f"<b>{i}. {e.get('title','')}</b>", normal))
        if comps:
            elems.append(Paragraph(f"<font color='#0F3B43'>Componentes:</font> {comps}", small))
        if e.get("description"):
            elems.append(Paragraph(e["description"], normal))
        if e.get("image"):
            fl = img_flow(e["image"])
            if fl:
                elems.append(Spacer(1, 2))
                elems.append(fl)
        elems.append(Spacer(1, 6))
    if not ex_docs:
        elems.append(Paragraph("Sem exercícios nesta unidade.", small))

    if u.get("notes"):
        elems.append(Paragraph("NOTAS", h2))
        elems.append(Paragraph(u["notes"], normal))

    doc.build(elems)
    buf.seek(0)
    filename = ("UT " + (u.get("title", "") or "treino").strip()).strip() + ".pdf"
    return StreamingResponse(buf, media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@api_router.get("/microcycles/{mid}/pdf")
async def microcycle_pdf(mid: str, request: Request):
    await get_current_user(request)
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle, Paragraph,
                                    Spacer, Image as RLImage, KeepTogether)

    m = await db.microcycles.find_one({"_id": _as_oid(mid)})
    if not m:
        raise HTTPException(status_code=404, detail="Microciclo não encontrado.")

    vids = await db.videos.find().to_list(1000)
    title_by_id = {str(v["_id"]): v.get("title", "") for v in vids}
    desc_by_id = {str(v["_id"]): v.get("description", "") for v in vids}

    DARK_GREEN = colors.HexColor("#0C3B1E")
    PETROL = colors.HexColor("#0F3B43")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=15 * mm, bottomMargin=15 * mm,
                            leftMargin=14 * mm, rightMargin=14 * mm)
    styles = getSampleStyleSheet()
    bf = "Helvetica-BoldOblique"
    title_style = ParagraphStyle("t", parent=styles["Title"], fontName=bf, textColor=DARK_GREEN, fontSize=20, spaceAfter=2)
    day_style = ParagraphStyle("d", parent=styles["Heading2"], fontName=bf, textColor=colors.white, fontSize=12, spaceBefore=0, spaceAfter=0)
    h3 = ParagraphStyle("h3", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10, textColor=PETROL, spaceBefore=4)
    normal = ParagraphStyle("n", parent=styles["Normal"], fontName="Helvetica", fontSize=9)
    small = ParagraphStyle("s", parent=styles["Normal"], fontName="Helvetica-Oblique", fontSize=8)

    elems = []
    logo = await _logo_bytes()
    logo_img = None
    if logo:
        try:
            logo_img = RLImage(logo, width=18 * mm, height=18 * mm)
        except Exception:
            logo_img = None
    title_block = [Paragraph("MICROCICLO SEMANAL", title_style),
                   Paragraph(f"Leões de Porto Salvo · {m.get('name','')}", small)]
    htbl = Table([[title_block, logo_img or ""]], colWidths=[None, 22 * mm])
    htbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (1, 0), (1, 0), "RIGHT")]))
    elems.append(htbl)
    elems.append(Spacer(1, 6))

    week_order = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
    days = m.get("days", {}) or {}
    any_content = False
    for day in week_order:
        trainings = days.get(day, []) or []
        if not trainings:
            continue
        any_content = True
        day_hdr = Table([[Paragraph(day.upper(), day_style)]], colWidths=[None])
        day_hdr.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), DARK_GREEN),
            ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        elems.append(Spacer(1, 4))
        elems.append(day_hdr)
        for tr in trainings:
            block = []
            hdr = f"Treino Nº {tr.get('number','') or '—'}"
            if tr.get("duration"):
                hdr += f" · {tr['duration']}"
            block.append(Paragraph(hdr, h3))
            comps = ", ".join(tr.get("components", []) or [])
            if comps:
                block.append(Paragraph(f"<font color='#0F3B43'><b>Componentes:</b></font> {comps}", small))
            for vid in (tr.get("video_ids", []) or []):
                t = title_by_id.get(vid)
                if not t:
                    continue
                block.append(Paragraph(f"<b>Exercício:</b> {t}", normal))
                d = desc_by_id.get(vid, "")
                if d:
                    block.append(Paragraph(d, small))
            if tr.get("notes"):
                block.append(Paragraph(f"<b>Notas:</b> {tr['notes']}", normal))
            block.append(Spacer(1, 6))
            elems.append(KeepTogether(block))
    if not any_content:
        elems.append(Paragraph("Microciclo sem treinos definidos.", small))

    doc.build(elems)
    buf.seek(0)
    filename = ("Microciclo " + (m.get("name", "") or "semana").strip()).strip() + ".pdf"
    return StreamingResponse(buf, media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@api_router.get("/scouting/{game_id}/pdf")
async def scouting_pdf(game_id: str, request: Request):
    await get_current_user(request)
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle, Paragraph,
                                    Spacer, Image as RLImage, PageBreak, KeepTogether)
    from PIL import Image as PILImage

    s = await db.scouting_plans.find_one({"game_id": game_id})
    if not s:
        raise HTTPException(status_code=404, detail="Scouting não encontrado. Cria e guarda primeiro.")

    DARK = colors.HexColor("#0C3B1E")
    PETROL = colors.HexColor("#0F3B43")
    GOLD = colors.HexColor("#C8A24B")
    LGREY = colors.HexColor("#F3F4F6")
    MGREY = colors.HexColor("#8A8F98")

    def esc(t):
        return (t or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def safe_img(b64, w, h):
        if not b64:
            return None
        try:
            raw = b64.split(",", 1)[1] if b64.startswith("data:") else b64
            pil = PILImage.open(io.BytesIO(base64.b64decode(raw)))
            pil.load()
            if pil.mode not in ("RGB", "L"):
                pil = pil.convert("RGB")
            out = io.BytesIO()
            pil.save(out, format="PNG")
            out.seek(0)
            return RLImage(out, width=w, height=h)
        except Exception:
            return None

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=13 * mm, bottomMargin=13 * mm,
                            leftMargin=13 * mm, rightMargin=13 * mm)
    styles = getSampleStyleSheet()
    bf = "Helvetica-BoldOblique"
    white_title = ParagraphStyle("wt", parent=styles["Title"], fontName=bf, textColor=colors.white, fontSize=20, spaceAfter=0, alignment=0)
    white_sub = ParagraphStyle("ws", parent=styles["Normal"], fontName="Helvetica", textColor=colors.HexColor("#CFE3D6"), fontSize=8, alignment=0)
    sec = ParagraphStyle("sec", parent=styles["Heading2"], fontName=bf, textColor=colors.white, fontSize=13)
    opp_name = ParagraphStyle("opp", parent=styles["Title"], fontName=bf, textColor=DARK, fontSize=24, spaceAfter=0, alignment=0)
    normal = ParagraphStyle("n", parent=styles["Normal"], fontName="Helvetica", fontSize=9)
    gkname = ParagraphStyle("gk", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8, alignment=1, textColor=DARK)
    small = ParagraphStyle("s", parent=styles["Normal"], fontName="Helvetica-Oblique", fontSize=8, textColor=MGREY)

    def section_title(text):
        t = Table([[Paragraph(esc(text), sec)]], colWidths=[doc.width])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), DARK),
            ("LINEBELOW", (0, 0), (-1, -1), 2.5, GOLD),
            ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))
        return t

    elems = []
    ha = (s.get("home_away") or "").upper()

    # ---- Header band ----
    club_logo_b = await _logo_bytes()
    club_img = None
    if club_logo_b:
        try:
            club_img = RLImage(club_logo_b, width=16 * mm, height=16 * mm)
        except Exception:
            club_img = None
    band = Table([[[Paragraph("SCOUTING &amp; MATCH PLAN", white_title),
                    Paragraph("Leões de Porto Salvo · Guarda-Redes", white_sub)], club_img or ""]],
                 colWidths=[None, 20 * mm])
    band.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), DARK),
        ("LINEBELOW", (0, 0), (-1, -1), 3, GOLD),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (0, 0), 12), ("TOPPADDING", (0, 0), (-1, -1), 12), ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (1, 0), (1, 0), 12),
    ]))
    elems.append(band)
    elems.append(Spacer(1, 8))

    # ---- Opponent block ----
    opp_logo = safe_img(s.get("opponent_logo"), 26 * mm, 26 * mm)
    ha_badge = ""
    if ha:
        ha_badge = Table([[Paragraph(f"<font color='white'><b>{esc(ha)}</b></font>", normal)]], colWidths=[24 * mm])
        ha_badge.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), GOLD if ha == "CASA" else PETROL),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
    opp_right = [Paragraph("<font size=8 color='#8A8F98'>ADVERSÁRIO</font>", normal),
                 Paragraph(esc(s.get("opponent") or "—"), opp_name)]
    if ha_badge:
        opp_right.append(Spacer(1, 3))
        opp_right.append(ha_badge)
    opp_block = Table([[opp_logo or "", opp_right]], colWidths=[30 * mm, None])
    opp_block.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, -1), LGREY),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 10), ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    elems.append(opp_block)
    elems.append(Spacer(1, 8))

    # ---- Info grid ----
    def chip(label, value):
        return Paragraph(f"<font size=7 color='#8A8F98'>{esc(label.upper())}</font><br/><font size=11><b>{esc(value or '—')}</b></font>", normal)
    info = [
        [chip("Competição", s.get("competition")), chip("Jornada", s.get("round")), chip("Data", s.get("date"))],
        [chip("Hora", s.get("time")), chip("Local", s.get("venue")), chip("Casa/Fora", s.get("home_away"))],
    ]
    it = Table(info, colWidths=[doc.width / 3] * 3)
    it.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
    ]))
    elems.append(it)
    elems.append(Spacer(1, 10))

    # ---- Called GKs ----
    elems.append(section_title("GUARDA-REDES CONVOCADOS"))
    elems.append(Spacer(1, 6))
    called = [g for g in (s.get("called_gks") or []) if g.get("name")]
    if called:
        cells = []
        for g in called:
            ph = safe_img(g.get("photo"), 20 * mm, 20 * mm)
            if not ph:
                ph = Table([[Paragraph("<font color='white'><b>GR</b></font>", gkname)]], colWidths=[20 * mm], rowHeights=[20 * mm])
                ph.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), PETROL), ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
            inner = Table([[ph], [Paragraph(esc(g.get("name", "")), gkname)]], colWidths=[26 * mm])
            inner.setStyle(TableStyle([
                ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("BOX", (0, 0), (-1, -1), 1, GOLD),
                ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            cells.append(inner)
        rows = [cells[i:i + 4] for i in range(0, len(cells), 4)]
        for r in rows:
            while len(r) < 4:
                r.append("")
        grid = Table(rows, colWidths=[doc.width / 4] * 4)
        grid.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                                  ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]))
        elems.append(grid)
    else:
        elems.append(Paragraph("Sem guarda-redes convocados.", small))

    # ---- Page 2: Set-piece plan ----
    elems.append(PageBreak())
    elems.append(section_title("GOALKEEPER SET-PIECE PLAN"))
    elems.append(Spacer(1, 8))
    photo_by_name = {g.get("name"): g.get("photo") for g in called}
    sp = s.get("set_pieces") or {}
    sp_defs = [("penalti", "PENÁLTI"), ("livre", "LIVRE"), ("livre10", "LIVRE DE 10 METROS")]
    for key, label in sp_defs:
        d = sp.get(key) or {}
        campo = d.get("mode") == "campo"
        gkn = d.get("gk") or ""
        if campo:
            val_par = Paragraph("<font color='#0C3B1E'><b>GR QUE ESTIVER EM CAMPO</b></font>", ParagraphStyle("v", parent=normal, fontSize=13))
            ph = ""
        else:
            val_par = Paragraph(f"<b>{esc(gkn or '—')}</b>", ParagraphStyle("v", parent=normal, fontSize=15, textColor=DARK))
            ph = safe_img(photo_by_name.get(gkn), 16 * mm, 16 * mm) or ""
        card = Table([[Paragraph(f"<font color='white'><b>{esc(label)}</b></font>", ParagraphStyle("l", parent=normal, fontSize=12, textColor=colors.white)),
                       val_par, ph]], colWidths=[52 * mm, None, 18 * mm])
        card.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), DARK),
            ("BACKGROUND", (1, 0), (-1, -1), colors.white if not campo else colors.HexColor("#EAF3EC")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
            ("LINEAFTER", (0, 0), (0, 0), 3, GOLD),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (2, 0), (2, 0), "RIGHT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 12), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 12), ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ]))
        elems.append(card)
        elems.append(Spacer(1, 8))

    # ---- Page 3+: Opposition key players ----
    elems.append(PageBreak())
    elems.append(section_title("OPPOSITION KEY PLAYERS"))
    elems.append(Spacer(1, 8))
    players = s.get("opposition_players") or []
    if players:
        pcards = []
        for p in players:
            ph = safe_img(p.get("photo"), 24 * mm, 24 * mm)
            if not ph:
                ph = Table([[Paragraph("<font color='white' size=7><b>SEM FOTO</b></font>", normal)]], colWidths=[24 * mm], rowHeights=[24 * mm])
                ph.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), MGREY), ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
            num = p.get("number") or ""
            head = f"<font color='#C8A24B'><b>#{esc(str(num))}</b></font> <b>{esc(p.get('name') or '—')}</b>"
            meta = " · ".join([x for x in [esc(p.get("position") or ""), (("Pé " + esc(p.get("foot"))) if p.get("foot") else "")] if x])
            info_par = [Paragraph(head, ParagraphStyle("ph", parent=normal, fontSize=11)),
                        Paragraph(meta, small)]
            if p.get("notes"):
                info_par.append(Spacer(1, 3))
                info_par.append(Paragraph(esc(p.get("notes")), normal))
            card = Table([[ph, info_par]], colWidths=[27 * mm, None])
            card.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
                ("LINEBEFORE", (0, 0), (0, 0), 3, GOLD),
                ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]))
            pcards.append(card)
        rows = [pcards[i:i + 2] for i in range(0, len(pcards), 2)]
        for r in rows:
            while len(r) < 2:
                r.append("")
            grid = Table([r], colWidths=[doc.width / 2] * 2)
            grid.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                      ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                                      ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
            elems.append(KeepTogether(grid))
    else:
        elems.append(Paragraph("Sem jogadores adversários adicionados.", small))

    # ---- Last page: Match notes ----
    elems.append(PageBreak())
    elems.append(section_title("MATCH NOTES"))
    elems.append(Spacer(1, 8))
    notes = s.get("match_notes") or ""
    if notes.strip():
        for para in notes.split("\n"):
            if para.strip():
                elems.append(Paragraph(esc(para), ParagraphStyle("mn", parent=normal, fontSize=10, spaceAfter=5, leading=14)))
            else:
                elems.append(Spacer(1, 5))
    else:
        elems.append(Paragraph("Sem notas.", small))

    doc.build(elems)
    buf.seek(0)
    opp = (s.get("opponent") or "adversario").strip()
    dt = (s.get("date") or "").strip()
    filename = f"Scouting & Match Plan - {opp}" + (f" - {dt}" if dt else "") + ".pdf"
    return StreamingResponse(buf, media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="{filename}"'})


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    admin_email = os.environ.get("ADMIN_EMAIL")
    admin_pw = os.environ.get("ADMIN_PASSWORD")
    if admin_email and admin_pw:
        existing = await db.users.find_one({"email": admin_email.lower()})
        if not existing:
            await db.users.insert_one({"email": admin_email.lower(),
                                       "password_hash": hash_password(admin_pw),
                                       "name": "João Coelho", "role": "admin",
                                       "created_at": datetime.now(timezone.utc).isoformat()})
        elif not verify_password(admin_pw, existing["password_hash"]):
            await db.users.update_one({"email": admin_email.lower()},
                                      {"$set": {"password_hash": hash_password(admin_pw)}})
    # seed logo
    if not await db.settings.find_one({"key": "logo"}):
        url = os.environ.get("LOGO_SEED_URL")
        if url:
            try:
                resp = requests.get(url, timeout=15)
                if resp.ok:
                    b64 = "data:image/jpeg;base64," + base64.b64encode(resp.content).decode()
                    await db.settings.update_one({"key": "logo"}, {"$set": {"value": b64}}, upsert=True)
            except Exception as e:
                logger.warning(f"logo seed failed: {e}")


@app.on_event("shutdown")
async def shutdown():
    client.close()
