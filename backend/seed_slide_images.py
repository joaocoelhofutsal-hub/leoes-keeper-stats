"""Render each PPTX slide to an image (via LibreOffice) and attach to exercises.
Run: python /app/backend/seed_slide_images.py
"""
import os, io, base64, subprocess
import requests
import pymupdf
import pymongo
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
db = pymongo.MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
URL = "https://customer-assets-7cd3h4nn.emergentagent.net/job_leoes-keeper-stats/artifacts/4ab9x49j_caderno%20exercicios%20GR%20LPS%2026_27.pptx"
PPTX = "/tmp/caderno.pptx"
OUTDIR = "/tmp/loconv"


def run():
    r = requests.get(URL, timeout=90); r.raise_for_status()
    open(PPTX, "wb").write(r.content)
    os.makedirs(OUTDIR, exist_ok=True)
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", OUTDIR, PPTX],
                   check=True, timeout=180)
    pdf = os.path.join(OUTDIR, "caderno exercicios GR LPS 26_27.pdf")
    if not os.path.exists(pdf):
        cands = [f for f in os.listdir(OUTDIR) if f.endswith(".pdf")]
        pdf = os.path.join(OUTDIR, cands[0])
    doc = pymupdf.open(pdf)
    images = []
    for i in range(doc.page_count):
        pix = doc[i].get_pixmap(dpi=110)
        images.append("data:image/png;base64," + base64.b64encode(pix.tobytes("png")).decode())
    doc.close()
    print("slides renderizados:", len(images))

    exercises = list(db.exercises.find().sort("_id", 1))
    n_img, n_ex = len(images), len(exercises)
    updated = 0
    for idx, ex in enumerate(exercises):
        si = round(idx * (n_img - 1) / (n_ex - 1)) if n_ex > 1 else 0
        si = max(0, min(si, n_img - 1))
        db.exercises.update_one({"_id": ex["_id"]}, {"$set": {"image": images[si]}})
        updated += 1
    print("exercícios atualizados com esquema real:", updated)


if __name__ == "__main__":
    run()
