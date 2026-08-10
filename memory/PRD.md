# PRD — Leões de Porto Salvo · Análise de Guarda-Redes

## Problema original
App web para análise estatística de guarda-redes de futsal do clube Leões de Porto Salvo. Base de dados online centralizada, funciona por link em PC/iPad/tablet. Páginas: Registo (ações de jogo com botões de seleção visual), Base de Dados (CRUD + perfil automático + tendências), PDF do relatório. Login simples.

## Arquitetura
- Backend FastAPI + MongoDB (Motor async). Rotas com prefixo /api.
- Auth JWT via cookies httpOnly (access 12h + refresh 7d), bcrypt.
- PDF via reportlab (logo, tabelas, avaliação só cor, tendências, notas). Nome: `RI <nome> <sessão>.pdf`.
- Frontend React (CRA/craco) + Tailwind + shadcn/ui + sonner. Fontes: Barlow Condensed + Manrope.
- Logo do clube guardado em base64 na coleção `settings` (seed automático + upload).

## Personas
- Treinador de guarda-redes: regista ações durante treinos/jogos no tablet e analisa perfis.

## Requisitos core (estáticos)
- Registo de ações com: Situação, Zona, Distância, Finalização, Técnica, Tomada de decisão (multi), Seguimento, Avaliação (cinzenta/verde/amarelo/vermelho), feedback obrigatório em amarelo/vermelho, notas por ação. Form limpa após cada ação.
- Ações ofensivas: passe/remate/reposição certo-errado.
- Base de Dados: CRUD GR, relatórios por GR, apagar relatórios, pontos fortes/fracos + fonte.
- Perfil automático: total relatórios, média ações/jogo, média verdes/relatório, estilo, decisão/técnica/seguimento mais frequentes.
- Tendências apenas com >=3 ocorrências (técnica, decisão, seguimento, zona, distância; nunca Enquadramento como principal).
- PDF final e exportação de dados (JSON).

## Implementado (2026-06)
- ✅ Auth JWT + login PT, rota protegida, admin seed (joaocoelhofutsal@gmail.com).
- ✅ Página Registo completa com botões de seleção visual grandes (tablet-first).
- ✅ Página Base de Dados: cards, detalhe, perfil, tendências, CRUD, apagar relatórios.
- ✅ Perfil automático + tendências com regra >=3 (validado com exemplos do enunciado).
- ✅ PDF com logo, avaliação só cor, tabelas, nome correto — verificado visualmente.
- ✅ Exportar JSON, upload de logo.
- ✅ Testado: 100% backend e frontend (iteration_1).

## Implementado (2026-06 · iteração dados iniciais)
- ✅ Seed de 8 guarda-redes recuperados (Cintra, Osuji, Jaime, Pedro 2 rel., Nilton 3 rel., + Rodrigo/Manuel/Tomás sem relatórios). Script: /app/backend/seed_initial.py (idempotente).
- ✅ Ações reconstruídas a partir dos tops/totais; perfil/tendências gerados pelo motor (regra >=3, sem Enquadramento principal). Fracções ofensivas exatas.
- ✅ Fotografia por guarda-redes: POST /api/goalkeepers/{id}/photo; avatar nos cartões e no cabeçalho do perfil (botão câmara).
- ✅ Importação JSON (formato de export da própria app): POST /api/import; botão "Importar JSON" na Base de Dados.
- ✅ Tendência adicional zona→seguimento no motor de perfil.
- ✅ Removidas situações "1 contra 1" e "Remate após 1x1 na ala".

## Backlog / próximos (P1/P2)
- P2: validar ObjectId malformado (400) e 404 em update/delete inexistente.
- P2: migrar startup para lifespan handlers.
- P2: paginação em listagens grandes.
- P1: gráficos (recharts) de tendências no perfil.
- P1: dashboard geral do clube.
