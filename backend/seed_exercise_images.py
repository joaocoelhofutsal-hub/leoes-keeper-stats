"""Extrai as imagens/esquemas do PPTX e associa a cada exercício (por ordem).
Run: python /app/backend/seed_exercise_images.py
"""
import os, re, io, base64, zipfile, mimetypes
import requests
import pymongo
from dotenv import load_dotenv
from xml.etree import ElementTree as ET

load_dotenv('/app/backend/.env')
db = pymongo.MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
URL = "https://customer-assets-7cd3h4nn.emergentagent.net/job_leoes-keeper-stats/artifacts/4ab9x49j_caderno%20exercicios%20GR%20LPS%2026_27.pptx"
PPTX = "/tmp/caderno.pptx"
RELNS = "{http://schemas.openxmlformats.org/package/2006/relationships}"


def download():
    r = requests.get(URL, timeout=60)
    r.raise_for_status()
    open(PPTX, "wb").write(r.content)
    print("downloaded", len(r.content), "bytes")


def slide_num(name):
    m = re.search(r"slide(\d+)\.xml$", name)
    return int(m.group(1)) if m else 0


def best_image_for_slide(z, slide_name):
    rels = f"ppt/slides/_rels/{os.path.basename(slide_name)}.rels"
    if rels not in z.namelist():
        return None
    tree = ET.fromstring(z.read(rels))
    targets = []
    for rel in tree:
        rtype = rel.get("Type", "")
        if rtype.endswith("/image"):
            t = rel.get("Target", "").replace("../", "ppt/")
            if not t.startswith("ppt/"):
                t = "ppt/" + t.lstrip("/")
            targets.append(t)
    if not targets:
        return None
    # pick the largest media file (likely the diagram, not an icon)
    best = None
    best_size = -1
    for t in targets:
        if t in z.namelist():
            size = z.getinfo(t).file_size
            if size > best_size:
                best_size = size
                best = t
    if not best:
        return None
    data = z.read(best)
    ctype = mimetypes.guess_type(best)[0] or "image/png"
    return "data:" + ctype + ";base64," + base64.b64encode(data).decode()


def run():
    download()
    z = zipfile.ZipFile(PPTX)
    slides = sorted([n for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n)], key=slide_num)
    images = [best_image_for_slide(z, s) for s in slides]
    n_with = sum(1 for i in images if i)
    print(f"slides: {len(slides)} | slides com imagem: {n_with}")

    exercises = list(db.exercises.find().sort("_id", 1))
    print(f"exercícios na BD: {len(exercises)}")

    # 16 slides (diagramas compostos) para 38 exercícios -> mapeamento proporcional:
    # exercícios do mesmo slide partilham o esquema desse slide.
    n_img = len(images)
    n_ex = len(exercises)
    updated = 0
    for i, ex in enumerate(exercises):
        si = round(i * (n_img - 1) / (n_ex - 1)) if n_ex > 1 else 0
        si = max(0, min(si, n_img - 1))
        img = images[si]
        if img:
            db.exercises.update_one({"_id": ex["_id"]}, {"$set": {"image": img}})
            updated += 1
    print(f"exercícios com imagem atualizada: {updated}")


if __name__ == "__main__":
    run()
