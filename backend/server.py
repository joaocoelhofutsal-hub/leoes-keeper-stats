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


class GoalkeeperIn(BaseModel):
    name: str
    team: Optional[str] = ""
    strengths: Optional[str] = ""
    weaknesses: Optional[str] = ""
    source: Optional[str] = ""


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
                    "strengths": g.get("strengths", ""), "weaknesses": g.get("weaknesses", ""),
                    "source": g.get("source", ""), "report_count": count})
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

    # decision (avoid Enquadramento as main)
    dec_counter = Counter([d for d in decisions if d])
    for dec, cnt in dec_counter.most_common():
        if dec == "Enquadramento":
            continue
        if cnt >= 3:
            trends.append(f"Tomada de decisão frequente: {dec} ({cnt}).")
            break

    # Offensive pass fail %
    total_pass = off["passes_ok"] + off["passes_err"]
    if total_pass > 0:
        fail_pct = round(off["passes_err"] / total_pass * 100)
        if fail_pct > 0:
            trends.append(f"Falhou {fail_pct}% dos passes em geral.")

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
    header_left = []
    if logo:
        try:
            img = RLImage(logo, width=26 * mm, height=26 * mm)
            header_left.append(img)
        except Exception:
            pass
    title_block = [Paragraph("RELATÓRIO INDIVIDUAL", title_style),
                   Paragraph("Leões de Porto Salvo · Análise de Guarda-Redes", small)]
    if header_left:
        htbl = Table([[header_left[0], title_block]], colWidths=[30 * mm, None])
    else:
        htbl = Table([[title_block]], colWidths=[None])
    htbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    elems.append(htbl)
    elems.append(Spacer(1, 6))

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

    # Offensive table
    elems.append(Paragraph("AÇÕES OFENSIVAS", h2))
    o = r.get("offensive", {}) or {}
    otbl = Table([
        ["", "Certo", "Errado"],
        ["Passe", str(o.get("passes_ok", 0)), str(o.get("passes_err", 0))],
        ["Remate", str(o.get("shots_ok", 0)), str(o.get("shots_err", 0))],
        ["Reposição", str(o.get("repos_ok", 0)), str(o.get("repos_err", 0))],
    ], colWidths=[40 * mm, 30 * mm, 30 * mm])
    otbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PETROL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D1D5DB")),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elems.append(otbl)

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
