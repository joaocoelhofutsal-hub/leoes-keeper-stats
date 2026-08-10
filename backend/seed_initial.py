"""One-off seed of initial goalkeepers + reports recovered from the old LPS app.
Idempotent: skips goalkeepers that already exist by name.
Actions are reconstructed from the provided aggregate tops so the app's
auto profile/charts populate. Run: python /app/backend/seed_initial.py
"""
import os
from datetime import datetime, timezone
import pymongo
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
db = pymongo.MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
NOW = datetime.now(timezone.utc).isoformat()

SIT = ["Balão", "Remate", "Remate após 1x1", "Passe ao 2º poste", "Cobertura"]
ZONE = ["Corredor lateral esquerdo", "Entre corredores esquerdo", "Corredor central",
        "Entre corredores direito", "Corredor lateral direito"]
DIST = ["0-2 m", "3-6 m", "7-10 m", "12 m+", "Meio-campo +"]
FIN = ["Canto superior esquerdo", "Canto superior direito", "Canto inferior esquerdo",
       "Canto inferior direito", "Meia altura esquerda", "Meia altura central",
       "Meia altura direita", "Central alta", "Central rasteira"]
TECH = ["Defesa com as pernas", "Defesa com os tornozelos", "Defesa com os braços",
        "Encaixe", "Parede", "Barreirista", "Aguardar em flexão", "Saída de joelhos",
        "Projeção no ar", "Queda lateral", "Limpar a bola", "Passe"]
FOL = ["Bola saiu pela lateral", "Bola saiu pela linha final", "GR recuperou",
       "Equipa recuperou", "Sobrou no corredor central", "Bola no adversário", "Golo do adversário"]


def flist(n, known, pool):
    arr = []
    kv = set()
    for v, c in known:
        arr += [v] * c
        kv.add(v)
    others = [x for x in pool if x not in kv] or [""]
    i = 0
    while len(arr) < n:
        arr.append(others[i % len(others)]); i += 1
    return arr[:n]


def build_actions(n, evals, sit, zone, dist, fin, tech, fol, decs):
    S = flist(n, sit, SIT); Z = flist(n, zone, ZONE); D = flist(n, dist, DIST)
    F = flist(n, fin, FIN); T = flist(n, tech, TECH); FO = flist(n, fol, FOL)
    EV = flist(n, evals, [])
    acts = []
    for i in range(n):
        acts.append({
            "situation": S[i], "zone": Z[i], "distance": D[i], "finish_type": F[i],
            "technique": T[i], "followup": FO[i],
            "decisions": [d for (d, c) in decs if i < c],
            "evaluation": EV[i], "feedback": "", "notes": "",
        })
    return acts


def chunk(acts, sizes):
    out = []; i = 0
    for s in sizes:
        out.append(acts[i:i + s]); i += s
    return out


PLAYERS = [
    {
        "name": "Guilherme Cintra", "team": "LPS",
        "reports": [{"session_number": "J6", "opponent": "Valpaços", "date": "2026-03-28",
                     "competition": "Ap. Campeão", "result": "8-5",
                     "off": {"passes_ok": 0, "passes_err": 0, "shots_ok": 0, "shots_err": 0, "repos_ok": 0, "repos_err": 0}}],
        "n": 22,
        "evals": [("verde", 8), ("amarelo", 3), ("cinzenta", 11)],
        "sit": [("Remate", 15)], "zone": [("Corredor central", 10)], "dist": [("7-10 m", 10)],
        "fin": [("Central rasteira", 6)],
        "tech": [("Barreirista", 5), ("Parede", 5), ("Encaixe", 3), ("Defesa com os braços", 3)],
        "fol": [("Golo do adversário", 5), ("GR recuperou", 5), ("Bola no adversário", 4), ("Equipa recuperou", 4)],
        "decs": [("Ocupar espaço", 8), ("Defesa de reação", 7), ("Encurtamento", 5)],
    },
    {
        "name": "Daniel Osuji", "team": "LPS",
        "reports": [{"session_number": "", "opponent": "Caxinas", "date": "2026-03-21",
                     "competition": "Liga Placard", "result": "7-3",
                     "off": {"passes_ok": 6, "passes_err": 6, "shots_ok": 0, "shots_err": 1, "repos_ok": 4, "repos_err": 0}}],
        "n": 24,
        "evals": [("verde", 10), ("amarelo", 2), ("cinzenta", 12)],
        "sit": [("Remate", 17)], "zone": [("Corredor central", 13)], "dist": [("7-10 m", 12)],
        "fin": [("Meia altura central", 8)],
        "tech": [("Barreirista", 10)],
        "fol": [("Golo do adversário", 6), ("Sobrou no corredor central", 6)],
        "decs": [("Ocupar espaço", 12), ("Encurtamento", 10), ("Defesa de reação", 9), ("Técnica de recurso", 5)],
    },
    {
        "name": "Jaime Arthur", "team": "Fundão",
        "reports": [{"session_number": "J22", "opponent": "Famalicão", "date": "2026-05-02",
                     "competition": "Liga Placard", "result": "2-1",
                     "off": {"passes_ok": 14, "passes_err": 6, "shots_ok": 2, "shots_err": 4, "repos_ok": 5, "repos_err": 2}}],
        "n": 29,
        "evals": [("verde", 8), ("amarelo", 4), ("cinzenta", 17)],
        "sit": [("Remate", 15)], "zone": [("Corredor central", 11)], "dist": [("7-10 m", 12)],
        "fin": [("Central rasteira", 7)],
        "tech": [("Defesa com as pernas", 7)],
        "fol": [("Bola saiu pela lateral", 6)],
        "decs": [("Ocupar espaço", 11), ("Defesa de reação", 8), ("Encurtamento", 6)],
    },
    {
        "name": "Pedro Martinho", "team": "SC Ferreira do Zêzere",
        "reports": [
            {"session_number": "", "opponent": "Famalicão", "date": "2026-07-31", "competition": "Liga Placard", "result": "9-2",
             "off": {"passes_ok": 2, "passes_err": 4, "shots_ok": 0, "shots_err": 0, "repos_ok": 1, "repos_err": 0}},
            {"session_number": "", "opponent": "Braga", "date": "2026-05-02", "competition": "Liga Placard", "result": "",
             "off": {"passes_ok": 4, "passes_err": 7, "shots_ok": 0, "shots_err": 1, "repos_ok": 1, "repos_err": 1}},
        ],
        "sizes": [8, 9], "n": 17,
        "evals": [("verde", 6), ("amarelo", 2), ("cinzenta", 9)],
        "sit": [("Remate", 10)], "zone": [("Corredor central", 7)], "dist": [("7-10 m", 11)],
        "fin": [("Canto inferior direito", 4), ("Meia altura central", 4)],
        "tech": [("Parede", 4)],
        "fol": [("Bola saiu pela lateral", 5)],
        "decs": [("Atacar a bola", 6), ("Ocupar espaço", 6), ("Defesa de reação", 5), ("Encurtamento", 5)],
    },
    {
        "name": "Nilton", "team": "SC Ferreira do Zêzere",
        "reports": [
            {"session_number": "", "opponent": "Famalicão", "date": "2026-03-21", "competition": "Liga Placard", "result": "",
             "off": {"passes_ok": 2, "passes_err": 3, "shots_ok": 1, "shots_err": 1, "repos_ok": 3, "repos_err": 0}},
            {"session_number": "", "opponent": "Torreense", "date": "2026-04-18", "competition": "Liga Placard", "result": "3-0",
             "off": {"passes_ok": 3, "passes_err": 6, "shots_ok": 1, "shots_err": 1, "repos_ok": 4, "repos_err": 2}},
            {"session_number": "", "opponent": "Braga", "date": "2026-05-02", "competition": "Liga Placard", "result": "",
             "off": {"passes_ok": 2, "passes_err": 3, "shots_ok": 1, "shots_err": 1, "repos_ok": 3, "repos_err": 2}},
        ],
        "sizes": [5, 11, 12], "n": 28,
        "evals": [("verde", 13), ("amarelo", 4), ("vermelho", 1), ("cinzenta", 10)],
        "sit": [("Remate", 18)], "zone": [("Corredor lateral esquerdo", 9)], "dist": [("7-10 m", 16)],
        "fin": [("Meia altura central", 12)],
        "tech": [("Barreirista", 6)],
        "fol": [("Equipa recuperou", 6)],
        "decs": [("Defesa de reação", 9), ("Técnica de recurso", 8), ("Ocupar espaço", 7), ("Encurtamento", 7), ("Atacar a bola", 6)],
    },
    {"name": "Rodrigo Prazeres", "team": "LPS", "reports": [], "n": 0},
    {"name": "Manuel Rodrigues", "team": "LPS sub17", "reports": [], "n": 0},
    {"name": "Tomás Guerra", "team": "LPS", "reports": [], "n": 0},
]


def run():
    created = 0
    for p in PLAYERS:
        if db.goalkeepers.find_one({"name": p["name"]}):
            print(f"skip (exists): {p['name']}")
            continue
        gk = db.goalkeepers.insert_one({
            "name": p["name"], "team": p["team"], "photo": "",
            "strong_points": [], "weak_points": [], "created_at": NOW,
        })
        gid = str(gk.inserted_id)
        created += 1
        if not p["reports"]:
            continue
        acts = build_actions(p["n"], p["evals"], p["sit"], p["zone"], p["dist"],
                             p["fin"], p["tech"], p["fol"], p["decs"])
        sizes = p.get("sizes", [p["n"]])
        parts = chunk(acts, sizes)
        for meta, part in zip(p["reports"], parts):
            db.reports.insert_one({
                "goalkeeper_id": gid, "goalkeeper_name": p["name"], "team": p["team"],
                "session_number": meta["session_number"], "opponent": meta["opponent"],
                "date": meta["date"], "competition": meta["competition"], "result": meta["result"],
                "coach_notes": "Dados recuperados da base antiga LPS.",
                "actions": part, "offensive": meta["off"], "created_at": NOW,
            })
        print(f"created: {p['name']} ({len(p['reports'])} rel., {p['n']} ações)")
    print(f"DONE. Novos guarda-redes: {created}")


if __name__ == "__main__":
    run()
