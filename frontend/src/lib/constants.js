export const SITUACOES = [
  "Balão", "Remate", "Remate após 1x1",
  "Passe ao 2º poste", "Cobertura",
];

export const ZONAS = [
  "Corredor lateral esquerdo", "Entre corredores esquerdo", "Corredor central",
  "Entre corredores direito", "Corredor lateral direito",
];

export const DISTANCIAS = ["0-2 m", "3-6 m", "7-10 m", "12 m+", "Meio-campo +"];

export const FINALIZACOES = [
  "Canto superior esquerdo", "Canto superior direito", "Canto inferior esquerdo",
  "Canto inferior direito", "Meia altura esquerda", "Meia altura central",
  "Meia altura direita", "Central alta", "Central rasteira", "Tornozelos do GR",
];

export const TECNICAS = [
  "Defesa com as pernas", "Defesa com os tornozelos", "Defesa com os braços",
  "Encaixe", "Parede", "Barreirista", "Aguardar em flexão", "Saída de joelhos",
  "Projeção no ar", "Queda lateral", "Limpar a bola", "Passe",
];

export const DECISOES = [
  "Enquadramento", "Encurtamento", "Ocupar espaço",
  "Técnica de recurso", "Defesa de reação", "Atacar a bola",
];

export const SEGUIMENTOS = [
  "Bola saiu pela lateral", "Bola saiu pela linha final", "GR recuperou",
  "Equipa recuperou", "Sobrou no corredor central", "Bola no adversário",
  "Golo do adversário",
];

export const AVALIACOES = [
  { key: "cinzenta", label: "Cinzenta", color: "#9CA3AF" },
  { key: "verde", label: "Verde", color: "#22C55E" },
  { key: "amarelo", label: "Amarelo", color: "#EAB308" },
  { key: "vermelho", label: "Vermelho", color: "#EF4444" },
];

export const EMPTY_ACTION = {
  situation: "", zone: "", distance: "", finish_type: "", technique: "",
  decisions: [], followup: "", evaluation: "", feedback: "", notes: "",
};

export const EMPTY_OFFENSIVE = {
  passes_ok: 0, passes_err: 0, shots_ok: 0, shots_err: 0, repos_ok: 0, repos_err: 0,
};

export const ZONA_SHORT = ["Lateral esq.", "Entre cor. esq.", "Corredor central", "Entre cor. dir.", "Lateral dir."];

export const GOAL_GRID = [
  ["Canto superior esquerdo", "Central alta", "Canto superior direito"],
  ["Meia altura esquerda", "Meia altura central", "Meia altura direita"],
  ["Canto inferior esquerdo", "Central rasteira", "Canto inferior direito"],
];

export const OFFENSIVE_BUTTONS = [
  { key: "passes_ok", label: "Passe certo", tone: "ok" },
  { key: "passes_err", label: "Passe errado", tone: "err" },
  { key: "shots_ok", label: "Remate certo", tone: "ok" },
  { key: "shots_err", label: "Remate errado", tone: "err" },
  { key: "repos_ok", label: "Reposição certa", tone: "ok" },
  { key: "repos_err", label: "Reposição errada", tone: "err" },
];

export const SIT_SHORT = {
  "Balão": "Balão", "Remate": "Remate", "Remate após 1x1": "Remate após 1x1",
  "Remate após 1x1 na ala": "1x1 na ala", "Passe ao 2º poste": "2º poste",
  "1 contra 1": "1 contra 1", "Cobertura": "Cobertura",
};

export const GOAL_SHORT = {
  "Canto superior esquerdo": "Canto sup. esq.", "Central alta": "Central alta",
  "Canto superior direito": "Canto sup. dir.", "Meia altura esquerda": "Meia esq.",
  "Meia altura central": "Central meia", "Meia altura direita": "Meia dir.",
  "Canto inferior esquerdo": "Canto inf. esq.", "Central rasteira": "Central rast.",
  "Canto inferior direito": "Canto inf. dir.",
};

export const SEG_SHORT = {
  "Bola saiu pela linha final": "Linha final", "GR recuperou": "GR recuperou",
  "Equipa recuperou": "Equipa recuperou", "Sobrou no corredor central": "Corredor central",
  "Bola no adversário": "Bola no adversário", "Golo do adversário": "Golo adversário",
  "Bola saiu pela lateral": "Lateral",
};

export const COMPONENTES = [
  "Potência", "Agilidade", "Força", "Velocidade de reação",
  "Mobilidade", "Ativação", "Coordenação",
];

export const VIDEO_COMPONENTES = [
  "Técnica", "Coordenação", "Agilidade", "Força",
  "Tático", "Velocidade de reação", "Potência", "Jogo de pés",
  "Domínio do espaço", "Velocidade", "Técnica de recurso", "Ativação/Aquecimento",
];
