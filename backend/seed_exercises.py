"""Seed the 38 goalkeeper exercises from 'caderno exercicios GR LPS 26_27.pptx'.
Idempotent per title. Maps free-text components to a canonical set.
Run: python /app/backend/seed_exercises.py
"""
import os
from datetime import datetime, timezone
import pymongo
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
db = pymongo.MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
NOW = datetime.now(timezone.utc).isoformat()

CANON = [
    ("veloc", "Velocidade"), ("reaç", "Reação"), ("reac", "Reação"), ("reage", "Reação"),
    ("forç", "Força"), ("forc", "Força"),
    ("potên", "Potência"), ("poten", "Potência"), ("impuls", "Potência"), ("salto", "Potência"),
    ("agilidade", "Agilidade"),
    ("coorden", "Coordenação"),
    ("resist", "Resistência"),
    ("equil", "Equilíbrio"), ("verticalidade", "Equilíbrio"),
    ("decis", "Tomada de decisão"), ("1xgr", "Tomada de decisão"), ("2xgr", "Tomada de decisão"),
    ("situação de jogo", "Tomada de decisão"), ("pivot", "Tomada de decisão"),
    ("desloc", "Deslocamento"),
    ("aquecimento", "Aquecimento"),
    ("técnic", "Técnica"), ("tecnic", "Técnica"), ("encaixe", "Técnica"), ("barreirista", "Técnica"),
    ("parede", "Técnica"), ("punch", "Técnica"), ("poste", "Técnica"), ("queda", "Técnica"), ("volei", "Técnica"),
]


def canon(text):
    t = text.lower()
    s = set()
    for k, v in CANON:
        if k in t:
            s.add(v)
    if not s:
        s.add("Técnica")
    order = ["Velocidade", "Força", "Potência", "Agilidade", "Coordenação", "Reação",
             "Técnica", "Resistência", "Equilíbrio", "Tomada de decisão", "Deslocamento", "Aquecimento"]
    return [c for c in order if c in s]


# (título, descrição, [componentes originais do caderno])
EX = [
    ("Passe com a mão, com o pé e encaixe (Aquecimento)", "Passe com a mão, passe com o pé e encaixe. (Aquecimento)", ["Técnica"]),
    ("Poste, punch e barreirista", "Poste, punch e barreirista (execução técnica com braço a acompanhar o movimento). Técnica, velocidade e qualidade no deslocamento.", ["Técnica", "Velocidade", "Deslocamento"]),
    ("Remates altos alternados", "Remates altos alternados, 3/4 de cada lado. Defesa de bolas altas.", ["Força", "Potência", "Agilidade"]),
    ("Troca de passes + bolas picadas", "Troca de passes entre GR e TR GR. À voz sai para defender bolas picadas (3). Primeira bola previamente decidida. Velocidade de reação e defesa de recurso.", ["Coordenação", "Reação"]),
    ("Troca de passes + bolas rasteiras", "Troca de passes entre GR e TR GR (rasteiros). À voz sai para defender bolas rasteiras (3). Primeira bola previamente decidida. Velocidade de reação e defesa de recurso.", ["Coordenação", "Reação"]),
    ("Passe no tempo + bola alta", "Passe no tempo + bola alta (3x), terminando com barreirista na última sequência. Velocidade e qualidade no deslocamento, no passe e na execução técnica.", ["Força", "Agilidade", "Velocidade", "Deslocamento", "Técnica"]),
    ("Deslocamento para o cone e encaixe (Aquecimento)", "Deslocamento para o cone 1 e 2, regressa em diagonal e defende em encaixe. Repete para o lado contrário. 2 GR a trabalhar ao mesmo tempo. Primeiros deslocamentos e contacto com a bola. (Aquecimento)", ["Deslocamento", "Técnica"]),
    ("Salto na caixa e defesa rasteira", "Salto na caixa, volta ao chão e defende bola rasteira. Impulsão, flexão dos apoios, defesa com obstáculo à visão.", ["Força", "Potência", "Reação"]),
    ("GR em tração e decisão do portador", "GR em tração. Aproxima-se do portador da bola, que decide se remata ou lança a bola com a mão (por cima do GR) para que defenda em recurso. Equilíbrio, verticalidade e tomada de decisão.", ["Força", "Agilidade", "Equilíbrio", "Tomada de decisão"]),
    ("Coordenação: toca no colete e passe (Aquecimento)", "Coordenação. Toca no colete pedido e passe no tempo. Várias bolas. A cor do colete é dita sempre que o GR faz o passe. (Aquecimento)", ["Coordenação"]),
    ("Toca nos marcadores e defende bola alta/barreirista (Aquecimento)", "Toca nos marcadores com os pés e defende bola alta, e defende barreirista. (Aquecimento)", ["Agilidade", "Potência"]),
    ("Devolução de bola de ténis e defesa", "Devolve bola de ténis com uma mão – bola alta, barreirista e barreirista/queda.", ["Coordenação", "Agilidade"]),
    ("Deslocamento lateral e defesa poste/barreirista", "Deslocamento lateral ida e volta (2x) entre os cones. Defende bola alta ao primeiro poste e barreirista ao segundo. Velocidade e qualidade nos deslocamentos, explosão para defesa ao segundo poste.", ["Potência", "Força", "Agilidade", "Deslocamento"]),
    ("Aquecimento: deslocamento e defesa parede/bola alta", "Aquecimento com 2 GR a trabalhar. Deslocamento lateral ao centro e defesa em parede/bola alta. (Aquecimento)", ["Deslocamento", "Técnica"]),
    ("Reage, contorna obstáculo e defende", "Reage à indicação do TR GR e contorna o obstáculo para defender parede próxima + defesa em barreirista/queda após contornar obstáculo por trás no regresso.", ["Potência", "Força", "Agilidade", "Coordenação", "Reação"]),
    ("Bola no pivot e decisões", "Bola no pivot – roda ou bate, ou passa para o ala contrário – faz 2xGR.", ["Coordenação", "Tomada de decisão"]),
    ("Ténis picada e defesa baixa/meia-altura", "Devolve bola de ténis picada (3x) e defende bola baixa ou meia-altura. Na última defende ainda uma última ao segundo poste.", ["Agilidade", "Potência", "Coordenação"]),
    ("Colocação de cones e defesa de bolas", "GR coloca o cone do lado contrário e defende barreirista do lado contrário (3x). Depois de colocar todos nas laterais, volta a colocar no meio e defende uma bola alta por cada. Deslocamentos laterais, execução técnica de barreirista e ajuste dos membros superiores.", ["Força", "Potência", "Resistência", "Deslocamento", "Técnica"]),
    ("Queda lateral e controlo de bola (Aquecimento)", "Defende em queda lateral a bola que sai da zona do canto. Outra bola sai aérea para o GR controlar. Larga a bola no sítio e regressa à baliza para 2xGR (atacante decide a um toque). (Aquecimento)", ["Coordenação", "Tomada de decisão"]),
    ("Encaixe, devolução e defesa de bolas", "Encaixa e devolve nos marcadores, faz deslocamento posterior e defende bola ao primeiro poste + defesa de bola baixa ou meia-altura. Ocupação de espaço, velocidade no deslocamento e técnica básica.", ["Força", "Deslocamento", "Técnica"]),
    ("Defesa de remate exterior e desvio de ténis", "Defesa de remate exterior + desvio de bola de ténis. Velocidade de reação, ocupação de espaço, enquadramento na trajetória bola-baliza.", ["Reação", "Agilidade"]),
    ("Skipping lateral e defesa", "Skipping lateral e defesa em parede, retorno por detrás do cone e defesa em barreirista, toca na punch e defesa de bola alta.", ["Agilidade", "Potência", "Resistência", "Técnica"]),
    ("Toca na punch, parede e queda/barreirista", "Toca na punch, defende parede e queda/barreirista. Repete do outro lado (2x).", ["Agilidade", "Potência", "Técnica"]),
    ("Skipping, deslocamento e barreirista", "Skipping nos marcadores, deslocamento para o lado contrário e barreirista do outro. Punch + barreirista.", ["Agilidade", "Potência", "Deslocamento", "Técnica"]),
    ("Encurtamento, encaixe e bola nos tornozelos", "Encurtamento e encaixe, defesa de bola nos tornozelos.", ["Coordenação", "Agilidade", "Potência", "Técnica"]),
    ("Encurta para parede, bola pisada", "Encurta para parede, defende bola a ser pisada para remate interior para o lado contrário e barreirista.", ["Agilidade", "Força", "Técnica"]),
    ("Poste e barreirista, poste e defesa", "Poste e barreirista (2x), poste e defesa de bola para interior da área (2x).", ["Agilidade", "Reação", "Técnica"]),
    ("Deslocamento, passe no tempo e parede", "Deslocamento até ao marcador e faz passe no tempo, regressa e faz novo deslocamento até ao marcador para parede em zona 3. (3x)", ["Deslocamento", "Técnica"]),
    ("Duas bolas: devolução e remates", "Duas bolas para devolução com as mãos (ajuste frontal), remate para zona dos tornozelos e remate potente central (reação a recarga).", ["Reação", "Potência"]),
    ("Punch, remate diagonal e encurtamento", "Punch e defesa de bola em remate diagonal, encurtamento à frente do cone para defesa em parede. Recuo até aos marcadores e defesa de bola a meia-altura. Toca na punch e defende bola ao 2º poste.", ["Técnica", "Agilidade"]),
    ("Pisa o marcador e defende bola", "Pisa o marcador da cor indicada pelo treinador, defende bola próxima do lado contrário. Pisa novamente o mesmo marcador, ajusta ao meio e defende bola rasteira.", ["Tomada de decisão", "Reação"]),
    ("Volta ao cone, passe e defesa de remate", "Volta ao cone e passe, volta ao cone e defesa para remate na zona dos tornozelos. Toca na punch e defende bola alta, punch e defesa de bola diagonal (proteger o cone).", ["Deslocamento", "Técnica"]),
    ("Encaixe lateral, deslocamento e passe/bola alta", "Encaixe de bola lateral. Deslocamento à frente do pino + passe e bola alta, deslocamento à frente do pino, barreirista e queda.", ["Deslocamento", "Técnica"]),
    ("Passe, volei, encaixe e bola nos tornozelos", "Passe de um lado ao outro e defende volei rasteira. Encaixe e solta e defende volei meia altura. Encaixe, devolve e bola nos tornozelos + bola de volei aleatória (9m).", ["Técnica", "Reação"]),
    ("Rotação 180º, retorno e defesa aleatória", "Rotação lateral de 180º, retorno e defesa de bola aleatória. Mobilidade e velocidade dos membros inferiores, equilíbrio e salto.", ["Velocidade", "Equilíbrio", "Potência", "Reação"]),
    ("Encaixa, larga e repõe rápido", "Encaixa e deixa a bola no chão, defende barreirista e vai repor a bola rápido – 1xGR ou 2xGR (decisão do TR GR).", ["Técnica", "Tomada de decisão"]),
    ("Encaixe, devolução e passe para suporte", "Defesa em encaixe, devolve e recebe passe para colocar a dois tempos num dos GR em suporte (2x). Defende a terceira bola a finalizar para zona dos tornozelos, devolve e aproxima para tocar na bola e defender rasteira após deslocamento posterior. Defende última bola. Finalização cruzada pela ala.", ["Técnica", "Deslocamento"]),
    ("Circuito de GR subido", "Circuito de preparação para momento de GR subido. Controlo da bola e passes diversos – inversões, bolas rasteiras, tensas, no tempo. Desvio de obstáculos e tomada de decisão sobre comportamento adversário.", ["Tomada de decisão", "Técnica"]),
]


def run():
    created = 0
    for title, desc, comps in EX:
        if db.exercises.find_one({"title": title}):
            continue
        components = canon(title + " " + desc + " " + " ".join(comps))
        # merge any explicit canonical comps passed in
        for c in comps:
            if c in ["Velocidade", "Força", "Potência", "Agilidade", "Coordenação", "Reação",
                     "Técnica", "Resistência", "Equilíbrio", "Tomada de decisão", "Deslocamento", "Aquecimento"] and c not in components:
                components.append(c)
        db.exercises.insert_one({"title": title, "description": desc,
                                 "components": components, "created_at": NOW})
        created += 1
    print(f"DONE. Novos exercícios: {created}. Total: {db.exercises.count_documents({})}")


if __name__ == "__main__":
    run()
