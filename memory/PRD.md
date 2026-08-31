# PRD — Leões de Porto Salvo · Análise de Guarda-Redes

## Problema original
App web para análise estatística de guarda-redes de futsal do clube Leões de Porto Salvo. Base de dados online centralizada, PC/iPad/tablet (meio-ecrã). PT-PT. Ferramenta profissional (rendimento, consistência, evolução, comparação).

## Arquitetura
- Backend FastAPI + MongoDB (Motor). Rotas /api. Auth JWT em cookies httpOnly + bcrypt.
- Frontend React (CRA/craco) + Tailwind + shadcn/ui + sonner (toast bottom-right) + recharts. Fontes Barlow Condensed + Manrope. Logo base64 (settings). Vídeos por link.

## Módulos (nav): Dashboard · Registo · Ações (soltas) · Base de Dados · Comparar · Sub-jogos · Dados Gerais · Treino · Vídeos. (Caderno REMOVIDO.)

## Implementado (resumo)
- Auth; Registo (ações + ofensivas + PDF); Base de Dados (CRUD, perfil, tendências, gráficos, pontos fortes/fracos, secção "Ações soltas"); export/import JSON; Dados Gerais; Treino de reação (perfil mostra só Melhor+Médio); Comparar; PWA; Vídeos (link + componentes + descrição, título auto oEmbed).
- Ações Soltas (/acoes): ação individual sem relatório (report loose:true). Entra no perfil/trends/total ações, NÃO conta como jogo. Endpoints /api/goalkeepers/{gid}/loose-actions[/{aid}].
- Sub-jogos (/sub-jogos): 5 sub-jogos; tópicos com nome/avaliação/nota + métrica opcional. Fontes: campos da ação + "Ações ofensivas" (passes/remates/reposições). MÉTRICA CRUZADA (2 filtros em AND). Sucesso = verde + cinzenta. Benchmark = GR de REFERÊNCIA escolhido pelo utilizador (benchmark_gk_id) com os mesmos filtros; sem GR escolhido = sem comparação; se o próprio = "Melhor da competição"; selo mostra delta em p.p. (auto_eval verde/amarelo/vermelho por rácio 0.9/0.7). Coleção subgame_evals; helpers _metric_from/_squad_data/_match_action.
- Dashboard (/dashboard, página inicial): KPIs do plantel; destaques (Melhor % sucesso — exige ≥3 ações e mostra amostra; Melhor reação); ranking (GR sem ações no fim). Secção "Referências por sub-jogo": GR que o utilizador considera melhores por sub-jogo (podem não ser do plantel), com barra de % sucesso quando é GR do plantel. Endpoints GET /api/insights/squad; GET/POST/DELETE /api/references (coleção references).

## Testado: iteration_4..8 (backend 100%, frontend 100%).

## Backlog / próximos (P1/P2)
- P1: Filtro por época/datas/competição (dashboard, relatórios, tendências, gráficos, sub-jogos).
- P1: Importação JSON legado (Edge) — falta exemplo.
- P2: Vídeos por GR (perfil). Evolução dos tempos de reação (linha) + data do melhor tempo. Nota global automática por sub-jogo.
- P2 (técnico/UX conhecidos): GET /api/goalkeepers devolve fotos base64 (~1.3MB) — atrasa selects/dashboard; criar variante "light" e loading states. Persistir seleção de GR (/acoes e /sub-jogos) em URL/localStorage. Validar payload /subgames com SubgameTopic. Login brute-force lockout (via integration_expert). Dividir server.py em routers (>1300 linhas). Substituir window.confirm por AlertDialog. Header: reverificar clip a 1920px. addRef sem guarda de duplicados; persist() otimista sem rollback em erro.
