from dotenv import load_dotenv
from pathlib import Path
import os

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import logging
import io
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
        count = await db.reports.count_documents({"goalkeeper_id": gid})
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
    reports = await db.reports.find({"goalkeeper_id": gid}).sort("created_at", -1).to_list(1000)
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
    total = len(reports)
    all_actions = []
    green_counts = []
    off = {"passes_ok": 0, "passes_err": 0, "shots_ok": 0, "shots_err": 0, "repos_ok": 0, "repos_err": 0}
    for r in reports:
        acts = r.get("actions", [])
        all_actions.extend(acts)
        green_counts.append(sum(1 for a in acts if a.get("evaluation") == "verde"))
        o = r.get("offensive", {}) or {}
        for k in off:
            off[k] += int(o.get(k, 0) or 0)

    n_actions = len(all_actions)
    avg_actions = round(n_actions / total, 1) if total else 0
    avg_green = round(sum(green_counts) / total, 1) if total else 0

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


# ---------- Logo settings ----------
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
        "reports": len(reports),
        "total_actions": total_actions,
        "evaluation": [{"name": k, "value": eval_counter.get(k, 0)} for k in ["verde", "amarelo", "vermelho", "cinzenta"]],
        "offensive_totals": off,
        "decisions_by_situation": decisions_by_situation,
    }


# ---------- Training (jogo de reação) ----------
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
