# PRD — Leões de Porto Salvo · Análise de Guarda-Redes

## Problema original
App web para análise estatística de guarda-redes de futsal do clube Leões de Porto Salvo. Base de dados online centralizada, funciona por link em PC/iPad/tablet (otimizada para meio-ecrã). Páginas: Registo (ações de jogo com botões de seleção visual), Base de Dados (CRUD + perfil automático + tendências), Dados Gerais, Treino (jogos de reação), Caderno (exercícios), Comparar, PDF de relatório. Login simples. Idioma: Português (Portugal).

## Arquitetura
- Backend FastAPI + MongoDB (Motor async). Rotas com prefixo /api.
- Auth JWT via cookies httpOnly (access 12h + refresh 7d), bcrypt.
- PDF via reportlab. PyMuPDF para renderizar páginas de PDF em imagens (import de exercícios).
- Frontend React (CRA/craco) + Tailwind + shadcn/ui + sonner + recharts. Fontes: Barlow Condensed + Manrope.
- Logo do clube em base64 na coleção `settings`.

## Personas
- Treinador de guarda-redes: regista ações em treinos/jogos no tablet e analisa perfis.

## Requisitos core
- Registo de ações (Situação, Zona, Distância, Finalização, Técnica, Decisão multi, Seguimento, Avaliação por cor, notas). Ações ofensivas.
- Base de Dados: CRUD GR, relatórios, pontos fortes/fracos + fonte, perfil automático, tendências (>=3 ocorrências).
- Dados Gerais (insights do clube). Treino (3 modos de reação + histórico). Caderno (CRUD exercícios + Unidades de Treino + PDF).
- PDF final e exportação/importação JSON.

## Implementado (2026-06)
- ✅ Auth JWT + login PT, rotas protegidas, admin seed.
- ✅ Registo, Base de Dados, perfil + tendências, PDF, export/import JSON.
- ✅ Seed de 8 guarda-redes. Fotografia por GR.
- ✅ Dados Gerais. Treino (Velocidade, Cores, Alvos Duplos) + histórico no perfil.
- ✅ Caderno de exercícios (CRUD + imagem + componentes + Unidade de Treino + PDF).

## Implementado (2026-06 · iteração import + comparar + PWA)
- ✅ Caderno recomeçado do zero (0 exercícios). Componentes fixadas nas 7 pedidas: Potência, Agilidade, Força, Velocidade de reação, Mobilidade, Ativação, Coordenação (`constants.js`).
- ✅ Importar exercícios em lote (`Caderno.js` + backend):
  - POST /api/exercises/bulk — cria vários a partir de lista de texto ("Título | descrição | componentes"); adivinha componentes por palavras-chave (`guess_components`).
  - POST /api/exercises/import-doc — upload PDF (renderizado com PyMuPDF, 1 página = 1 exercício com imagem) ou .pptx (best-effort com LibreOffice; se ausente devolve erro 400 amigável em PT a pedir export para PDF).
- ✅ Página Comparar (`/comparar`, `Comparar.js`): dois GR lado a lado — stats + gráficos comparativos (Avaliações, Técnicas, Seguimento, Zona, Distância). Nav "Comparar" adicionada.
- ✅ PWA instalável (iPad): `manifest.json`, ícones (favicon/apple-touch/192/512), meta tags Apple + `sw.js` registado no `index.html`. theme_color #0C3B1E.
- ✅ Robustez: validação de ObjectId inválido (400) e 404 em update de exercício inexistente. DialogDescription (a11y).
- ✅ Testado: backend 10/10 novos testes + frontend 100% nas 3 funcionalidades (iteration_4).

## Notas de deployment
- LibreOffice NÃO está garantido no ambiente (nem em produção). O import por PDF (PyMuPDF) é o caminho robusto; PPTX é best-effort.
- Imagens de exercícios guardadas como data URL base64 no documento MongoDB — atenção ao tamanho para PDFs grandes.

## Backlog / próximos (P1/P2)
- P1: Filtro por época/datas/competição em relatórios, tendências e gráficos.
- P1: Ajustar importação JSON ao formato da app legada (Edge) — falta exemplo do utilizador.
- P2: Média de avaliação por situação nos "Dados Gerais".
- P2: Foto do GR no cabeçalho do PDF.
- P2: Gráfico de evolução dos tempos de reação por GR.
- P2: Duração/séries por exercício + tempo total na Unidade de Treino.
- P2: Ranking de treino (melhores tempos entre GR).
- P2: Import de exercícios — melhorar deteção de diacríticos no parseList (deixar backend adivinhar).
