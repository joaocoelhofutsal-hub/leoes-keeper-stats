# PRD — Leões de Porto Salvo · Análise de Guarda-Redes

## Problema original
App web para análise estatística de guarda-redes de futsal do clube Leões de Porto Salvo. Base de dados online centralizada, PC/iPad/tablet (otimizada para meio-ecrã). Idioma: Português (Portugal).

## Arquitetura
- Backend FastAPI + MongoDB (Motor async). Rotas com prefixo /api. Auth JWT em cookies httpOnly + bcrypt.
- PDF via reportlab. PyMuPDF para renderizar PDF em imagens (import de exercícios — módulo Caderno removido).
- Frontend React (CRA/craco) + Tailwind + shadcn/ui + sonner + recharts. Fontes: Barlow Condensed + Manrope.
- Logo em base64 na coleção `settings`. Imagens/vídeos: fotos base64; vídeos por link (embed).

## Módulos atuais (nav)
Registo · Ações (soltas) · Base de Dados · Comparar · Sub-jogos · Dados Gerais · Treino · Vídeos.
(Caderno de Exercícios foi REMOVIDO a pedido do utilizador.)

## Requisitos core
- Registo de ações (Situação, Zona, Distância, Finalização, Técnica, Decisão multi, Seguimento, Avaliação por cor, notas) + ações ofensivas. Guarda relatório + PDF.
- Base de Dados: CRUD GR, relatórios, pontos fortes/fracos + fonte, perfil automático, tendências (>=3), gráficos. Treino de reação mostra só Melhor + Médio.
- Comparar dois GR (stats + gráficos). Dados Gerais (insights do clube). Treino (3 modos reação + histórico). Vídeos (link + componentes + descrição).

## Implementado (2026-06)
- ✅ Auth, Registo, Base de Dados, perfil/tendências/gráficos, PDF, export/import JSON, 8 GR seed, fotos.
- ✅ Dados Gerais; Treino (Velocidade/Cores/Alvos Duplos) + histórico.
- ✅ Comparar GR; PWA instalável (manifest, ícones, apple meta, sw.js).
- ✅ Vídeos de Treino (/videos): link YouTube/Vimeo/.mp4 embebido, 12 componentes, descrição, filtros, CRUD. Título preenche automaticamente via oEmbed.
- ✅ Perfil: treino de reação mostra só Melhor resultado + Resultado médio.
- ✅ AÇÕES SOLTAS (/acoes): registar ação individual de um GR sem relatório. Guardadas num report interno com flag `loose:true`. Entram no perfil/trends/total de ações, mas NÃO contam como jogo (excluídas do report_count em list_goalkeepers, gk_reports, compute_profile e insights_general). Endpoints: GET/POST/DELETE /api/goalkeepers/{gid}/loose-actions[/{aid}].
- ✅ SUB-JOGOS (/sub-jogos): 5 sub-jogos (Defesa da baliza, GR subido, Transição defesa-ataque, Transição ataque-defesa, Bolas paradas). Tópicos com nome, avaliação (cor), nota e métrica opcional (fonte=campo da ação + valor) que calcula count + % sucesso (verde) das ações do GR. Endpoints: GET/PUT /api/goalkeepers/{gid}/subgames; coleção `subgame_evals`; helper `_metric`.
- ✅ Testado: iteration_4/5/6 (backend 100%, frontend 100%).

## Notas técnicas
- LibreOffice NÃO garantido no ambiente; import de exercícios era via PDF (PyMuPDF). Caderno removido.
- Loose actions: um documento report por GR com array `actions`; sem cap (pode crescer numa época — backlog).

## Backlog / próximos (P1/P2)
- P1: Filtro por época/datas/competição em relatórios, tendências, gráficos e sub-jogos.
- P1: Importação JSON legado (Edge) — falta exemplo do utilizador.
- P2: Vídeos por GR (associar ao perfil). Data do melhor tempo de reação no perfil.
- P2: Ranking de reação entre GR. Evolução dos tempos de reação (linha).
- P2: Dashboard inicial com KPIs do plantel.
- P2 (técnico): validar payload subgames com SubgameTopic; login brute-force lockout; dividir server.py em routers (>1200 linhas); paginação/cap nas loose actions; toasts a sobrepor a nav.
