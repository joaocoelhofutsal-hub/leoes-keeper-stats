# PRD — Leões de Porto Salvo · Análise de Guarda-Redes

## Problema original
App web para análise estatística de guarda-redes de futsal do clube Leões de Porto Salvo. Base de dados online centralizada, PC/iPad/tablet (otimizada para meio-ecrã). Idioma: Português (Portugal). Objetivo: ferramenta profissional (rendimento, consistência, evolução e comparação entre GR).

## Arquitetura
- Backend FastAPI + MongoDB (Motor async). Rotas /api. Auth JWT em cookies httpOnly + bcrypt.
- PDF via reportlab. PyMuPDF disponível. Frontend React (CRA/craco) + Tailwind + shadcn/ui + sonner + recharts.
- Fontes: Barlow Condensed + Manrope. Logo em base64 (settings). Vídeos por link (embed).

## Módulos (nav): Dashboard · Registo · Ações (soltas) · Base de Dados · Comparar · Sub-jogos · Dados Gerais · Treino · Vídeos.
(Caderno de Exercícios foi REMOVIDO a pedido do utilizador.)

## Implementado
- Auth, Registo (ações + ofensivas + PDF), Base de Dados (CRUD, perfil, tendências >=3, gráficos, pontos fortes/fracos), export/import JSON, 8+ GR seed, fotos.
- Dados Gerais (insights clube). Treino de reação (3 modos + histórico; perfil mostra só Melhor + Médio).
- Comparar dois GR. PWA instalável. Vídeos de Treino (link + 12 componentes + descrição + filtros; título auto via oEmbed).
- AÇÕES SOLTAS (/acoes): ação individual sem relatório (report interno loose:true). Entram no perfil/trends/total de ações mas NÃO contam como jogo (excluídas de report_count em list_goalkeepers, gk_reports, compute_profile e insights_general). Endpoints /api/goalkeepers/{gid}/loose-actions[/{aid}]. Mostradas no perfil (secção "Ações soltas", separadas dos jogos).
- SUB-JOGOS (/sub-jogos): 5 sub-jogos (Defesa da baliza, GR subido, Transição def-ataque, Transição ataque-def, Bolas paradas). Tópicos com nome/avaliação/nota + métrica opcional (fonte = campo da ação OU "Ações ofensivas" passes/remates/reposições). Métrica = count + % sucesso. SUCESSO = verde + cinzenta (cinzenta = normalidade). Avaliação comparativa "vs melhor" da competição (benchmark com amostra mínima 3, best_count, is_best="Melhor da competição"); auto_eval verde/amarelo/vermelho por rácio 0.9/0.7. Coleção subgame_evals; helper _metric_from/_squad_data.
- DASHBOARD (/dashboard): página inicial (login entra aqui). KPIs do plantel (GR, jogos, ações, % sucesso médio verdes+cinzentas), destaques (melhor % sucesso, melhor reação) e ranking (GR sem ações vão para o fim). Endpoint GET /api/insights/squad.
- Testado: iteration_4..7 (backend 100%, frontend 100%).

## Backlog / próximos (P1/P2)
- P1: Filtro por época/datas/competição (relatórios, tendências, gráficos, sub-jogos, dashboard).
- P1: Importação JSON legado (Edge) — falta exemplo do utilizador.
- P2: Vídeos por GR (associar ao perfil). Cruzar 2 filtros na métrica do sub-jogo (ex.: situação+decisão).
- P2: Evolução dos tempos de reação (linha) e data do melhor tempo no perfil.
- P2 (técnico): validar payload /subgames com SubgameTopic; login brute-force lockout (via integration_expert); dividir server.py em routers (>1300 linhas); pré-computar benchmark por (field,value); manter seleção de GR em /acoes; loading/erro no Dashboard; alinhar confirmações de delete (AlertDialog); afinar overflow da nav com 9 itens.
