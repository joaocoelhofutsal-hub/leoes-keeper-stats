import { useEffect, useRef, useState } from "react";
import api from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Zap, Trophy, Eye, RotateCcw, Play, Target } from "lucide-react";

const PALETTE = [
  { key: "verde", hex: "#22C55E", name: "Verde" },
  { key: "gold", hex: "#F4C430", name: "Amarelo" },
  { key: "vermelho", hex: "#EF4444", name: "Vermelho" },
  { key: "petrol", hex: "#0F3B43", name: "Azul petróleo" },
  { key: "branco", hex: "#E5E7EB", name: "Branco" },
];
const GRID = 9;
const MAX_ROUNDS = 10;
const rand = (a, b) => Math.floor(Math.random() * (b - a)) + a;
const MODE_LABEL = { reacao: "Reação", cores: "Cores", duplos: "Alvos duplos" };

export default function Treino() {
  const [gks, setGks] = useState([]);
  const [gkId, setGkId] = useState("");
  const [mode, setMode] = useState("reacao");
  const [phase, setPhase] = useState("idle");
  const [round, setRound] = useState(0);
  const [active, setActive] = useState(null);
  const [decoy, setDecoy] = useState(null);
  const [pads, setPads] = useState(Array(GRID).fill(null));
  const [prompt, setPrompt] = useState(null);
  const [times, setTimes] = useState([]);
  const [tooSoon, setTooSoon] = useState(0);
  const [msg, setMsg] = useState("Escolhe um modo e toca em Começar.");
  const [savedId, setSavedId] = useState(null);

  const startRef = useRef(0);
  const toRef = useRef(null);
  const phaseRef = useRef("idle");
  const roundRef = useRef(0);
  const modeRef = useRef("reacao");
  const timesRef = useRef([]);
  const tooSoonRef = useRef(0);

  useEffect(() => { api.get("/goalkeepers").then((r) => setGks(r.data)).catch(() => {}); }, []);

  const setPh = (p) => { phaseRef.current = p; setPhase(p); };
  const clearTimer = () => { if (toRef.current) { clearTimeout(toRef.current); toRef.current = null; } };
  useEffect(() => () => clearTimer(), []);

  const start = () => {
    clearTimer(); modeRef.current = mode; setSavedId(null);
    setTimes([]); timesRef.current = []; setTooSoon(0); tooSoonRef.current = 0;
    setActive(null); setDecoy(null); setPads(Array(GRID).fill(null)); setPrompt(null);
    roundRef.current = 0; setRound(0);
    scheduleNext(0);
  };

  const scheduleNext = (r) => {
    roundRef.current = r; setRound(r);
    if (r >= MAX_ROUNDS) { finish(); return; }
    setActive(null); setDecoy(null); setPads(Array(GRID).fill(null)); setPrompt(null);
    setPh("wait"); setMsg("Espera pelo sinal…");
    const delay = rand(700, 2100);
    toRef.current = setTimeout(() => {
      startRef.current = performance.now();
      const m = modeRef.current;
      if (m === "reacao") {
        setActive(rand(0, GRID)); setMsg("TOCA!");
      } else if (m === "duplos") {
        const a = rand(0, GRID); let d = rand(0, GRID); while (d === a) d = rand(0, GRID);
        setActive(a); setDecoy(d); setMsg("Toca no DOURADO (evita o vermelho)");
      } else {
        const p = PALETTE[rand(0, PALETTE.length)];
        const arr = Array.from({ length: GRID }, () => PALETTE[rand(0, PALETTE.length)].hex);
        arr[rand(0, GRID)] = p.hex;
        setPads(arr); setPrompt(p); setMsg(`Toca em: ${p.name}`);
      }
      setPh("live");
    }, delay);
  };

  const record = () => {
    const t = Math.round(performance.now() - startRef.current);
    timesRef.current = [...timesRef.current, t]; setTimes(timesRef.current);
    setActive(null); setDecoy(null); setPads(Array(GRID).fill(null)); setPrompt(null);
    setPh("pause"); setMsg(`⚡ ${t} ms`);
    toRef.current = setTimeout(() => scheduleNext(roundRef.current + 1), 450);
  };

  const finish = async () => {
    clearTimer(); setPh("done");
    setActive(null); setDecoy(null); setPads(Array(GRID).fill(null)); setPrompt(null);
    setMsg("Sessão concluída!");
    const ts = timesRef.current;
    if (gkId && ts.length) {
      const avg = Math.round(ts.reduce((a, b) => a + b, 0) / ts.length);
      const best = Math.min(...ts);
      const gk = gks.find((g) => g.id === gkId);
      try {
        const { data } = await api.post("/training", {
          goalkeeper_id: gkId, goalkeeper_name: gk?.name || "",
          mode: modeRef.current, rounds: ts.length, avg_ms: avg, best_ms: best, too_soon: tooSoonRef.current,
        });
        setSavedId(data.id); toast.success("Resultado guardado no perfil do guarda-redes.");
      } catch { toast.error("Não foi possível guardar o resultado."); }
    }
  };

  const onPad = (i) => {
    const ph = phaseRef.current;
    if (ph === "wait") { clearTimer(); tooSoonRef.current += 1; setTooSoon(tooSoonRef.current); setMsg("Cedo demais! Espera pelo sinal."); scheduleNext(roundRef.current); return; }
    if (ph !== "live") return;
    const m = modeRef.current;
    if (m === "reacao") { if (i === active) record(); else setMsg("Falhaste o alvo!"); }
    else if (m === "duplos") { if (i === active) record(); else if (i === decoy) setMsg("Alvo falso! (vermelho)"); }
    else { if (prompt && pads[i] === prompt.hex) record(); else setMsg("Cor errada!"); }
  };

  const running = phase !== "idle" && phase !== "done";
  const best = times.length ? Math.min(...times) : 0;
  const avg = times.length ? Math.round(times.reduce((a, b) => a + b, 0) / times.length) : 0;

  const padStyle = (i) => {
    const m = modeRef.current;
    if (phase === "live") {
      if ((m === "reacao" || m === "duplos") && i === active) return { background: "#F4C430", boxShadow: "0 0 24px rgba(244,196,48,0.7)" };
      if (m === "duplos" && i === decoy) return { background: "#EF4444", boxShadow: "0 0 20px rgba(239,68,68,0.6)" };
      if (m === "cores" && pads[i]) return { background: pads[i], boxShadow: `0 0 16px ${pads[i]}66` };
    }
    return { background: "rgba(255,255,255,0.06)", boxShadow: "inset 0 0 0 1px rgba(255,255,255,0.12)" };
  };

  const modes = [
    { key: "reacao", icon: Zap, label: "Reação", desc: "Toca no alvo dourado ao acender." },
    { key: "cores", icon: Eye, label: "Cores", desc: "Toca só na cor pedida." },
    { key: "duplos", icon: Target, label: "Alvos duplos", desc: "Toca no dourado, evita o vermelho." },
  ];

  return (
    <div className="space-y-5 max-w-3xl mx-auto" data-testid="treino-page">
      <div className="flex items-center gap-2">
        <Zap className="text-[#F4C430]" />
        <h1 className="font-cond text-3xl sm:text-4xl font-extrabold uppercase text-[#0C3B1E]">Treino de Reação</h1>
      </div>
      <p className="text-sm text-muted-foreground -mt-2">Treino visual, ocular e de velocidade de reação. 10 sinais por sessão.</p>

      <div className="grid sm:grid-cols-2 gap-2 items-end">
        <div className="space-y-1">
          <label className="text-xs font-bold uppercase text-[#0F3B43]">Guarda-redes (para guardar no perfil)</label>
          <select value={gkId} onChange={(e) => setGkId(e.target.value)} data-testid="treino-gk-select" disabled={running}
            className="w-full h-10 rounded-lg border border-gray-300 px-2 bg-white text-sm">
            <option value="">— Sem guardar (treino livre) —</option>
            {gks.map((g) => <option key={g.id} value={g.id}>{g.name} {g.team ? `(${g.team})` : ""}</option>)}
          </select>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2">
        {modes.map((mo) => {
          const Icon = mo.icon; const on = mode === mo.key;
          return (
            <button key={mo.key} data-testid={`mode-${mo.key}`} disabled={running} onClick={() => setMode(mo.key)}
              className={`rounded-xl border-2 p-2.5 text-left transition-colors ${on ? "border-[#0C3B1E] bg-[#0C3B1E] text-white" : "border-gray-200 bg-white text-[#0C3B1E]"} ${running ? "opacity-60" : ""}`}>
              <div className="flex items-center gap-1.5 font-bold uppercase text-xs"><Icon size={15} /> {mo.label}</div>
              <div className={`text-[11px] mt-1 leading-tight ${on ? "text-white/80" : "text-muted-foreground"}`}>{mo.desc}</div>
            </button>
          );
        })}
      </div>

      <div className="grid grid-cols-4 gap-2">
        {[["Sinal", `${Math.min(round + (phase === "pause" ? 1 : 0), MAX_ROUNDS)}/${MAX_ROUNDS}`],
          ["Último", times.length ? `${times[times.length - 1]}ms` : "—"],
          ["Média", avg ? `${avg}ms` : "—"], ["Melhor", best ? `${best}ms` : "—"]].map(([l, v], idx) => (
          <div key={l} className="rounded-lg border border-gray-200 p-2 text-center bg-white" data-testid={`stat-${idx}`}>
            <div className="text-[10px] uppercase text-muted-foreground">{l}</div>
            <div className="font-cond text-xl font-extrabold text-[#0C3B1E]">{v}</div>
          </div>
        ))}
      </div>

      <div className={`rounded-xl px-4 py-3 text-center font-bold text-lg transition-colors ${
        phase === "live" ? "bg-[#F4C430] text-[#0C3B1E]" : phase === "wait" ? "bg-[#0F3B43] text-white" : "bg-gray-100 text-[#0C3B1E]"
      }`} data-testid="game-message">{msg}</div>

      <div className="rounded-2xl p-3" style={{ background: "linear-gradient(160deg,#0C3B1E,#0F3B43)" }}>
        <div className="grid grid-cols-3 gap-2.5">
          {Array.from({ length: GRID }).map((_, i) => (
            <button key={i} type="button" data-testid={`pad-${i}`} onClick={() => onPad(i)}
              className="aspect-square rounded-xl transition-all active:scale-95" style={padStyle(i)} />
          ))}
        </div>
      </div>

      <div className="flex gap-2">
        {!running ? (
          <Button onClick={start} data-testid="start-btn" className="flex-1 h-12 bg-[#0C3B1E] hover:bg-[#0a3018] text-white font-bold uppercase tracking-wide">
            <Play className="mr-2" size={18} /> {phase === "done" ? "Jogar outra vez" : "Começar"}
          </Button>
        ) : (
          <Button onClick={() => { clearTimer(); setPh("idle"); setMsg("Sessão parada."); }} data-testid="stop-btn" variant="outline" className="flex-1 h-12 font-bold uppercase">
            <RotateCcw className="mr-2" size={18} /> Parar
          </Button>
        )}
      </div>

      {phase === "done" && times.length > 0 && (
        <div className="rounded-2xl border-2 border-[#F4C430] p-5 bg-white space-y-2" data-testid="finish-summary">
          <div className="flex items-center gap-2 font-cond text-2xl font-extrabold uppercase text-[#0C3B1E]"><Trophy className="text-[#F4C430]" /> Resultado · {MODE_LABEL[modeRef.current]}</div>
          <div className="grid grid-cols-3 gap-3 text-center">
            <div><div className="text-xs uppercase text-muted-foreground">Média</div><div className="font-cond text-3xl font-extrabold text-[#0C3B1E]">{avg}<span className="text-base">ms</span></div></div>
            <div><div className="text-xs uppercase text-muted-foreground">Melhor</div><div className="font-cond text-3xl font-extrabold text-green-600">{best}<span className="text-base">ms</span></div></div>
            <div><div className="text-xs uppercase text-muted-foreground">Cedo demais</div><div className="font-cond text-3xl font-extrabold text-red-500">{tooSoon}</div></div>
          </div>
          {savedId && <div className="text-sm text-center text-green-700">✓ Guardado no perfil do guarda-redes.</div>}
        </div>
      )}
    </div>
  );
}
