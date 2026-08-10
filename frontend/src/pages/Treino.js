import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Zap, Trophy, Eye, RotateCcw, Play } from "lucide-react";

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

export default function Treino() {
  const [mode, setMode] = useState("reacao"); // reacao | cores
  const [phase, setPhase] = useState("idle"); // idle | wait | live | pause | done
  const [round, setRound] = useState(0);
  const [active, setActive] = useState(null);
  const [pads, setPads] = useState(Array(GRID).fill(null));
  const [prompt, setPrompt] = useState(null);
  const [times, setTimes] = useState([]);
  const [tooSoon, setTooSoon] = useState(0);
  const [msg, setMsg] = useState("Escolhe um modo e toca em Começar.");

  const startRef = useRef(0);
  const toRef = useRef(null);
  const phaseRef = useRef("idle");
  const roundRef = useRef(0);
  const modeRef = useRef("reacao");

  const setPh = (p) => { phaseRef.current = p; setPhase(p); };
  const clearTimer = () => { if (toRef.current) { clearTimeout(toRef.current); toRef.current = null; } };
  useEffect(() => () => clearTimer(), []);

  const start = () => {
    clearTimer();
    modeRef.current = mode;
    setTimes([]); setTooSoon(0); setActive(null); setPads(Array(GRID).fill(null)); setPrompt(null);
    roundRef.current = 0; setRound(0);
    scheduleNext(0);
  };

  const scheduleNext = (r) => {
    roundRef.current = r; setRound(r);
    if (r >= MAX_ROUNDS) { finish(); return; }
    setActive(null); setPads(Array(GRID).fill(null)); setPrompt(null);
    setPh("wait"); setMsg("Espera pelo sinal…");
    const delay = rand(700, 2100);
    toRef.current = setTimeout(() => {
      startRef.current = performance.now();
      if (modeRef.current === "reacao") {
        setActive(rand(0, GRID)); setMsg("TOCA!");
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
    setTimes((x) => [...x, t]);
    setActive(null); setPads(Array(GRID).fill(null)); setPrompt(null);
    setPh("pause"); setMsg(`⚡ ${t} ms`);
    toRef.current = setTimeout(() => scheduleNext(roundRef.current + 1), 450);
  };

  const finish = () => { clearTimer(); setPh("done"); setActive(null); setPads(Array(GRID).fill(null)); setPrompt(null); setMsg("Sessão concluída!"); };

  const onPad = (i) => {
    const ph = phaseRef.current;
    if (ph === "wait") {
      clearTimer(); setTooSoon((t) => t + 1); setMsg("Cedo demais! Espera pelo sinal.");
      scheduleNext(roundRef.current);
      return;
    }
    if (ph !== "live") return;
    if (modeRef.current === "reacao") {
      if (i === active) record(); else setMsg("Falhaste o alvo!");
    } else {
      if (prompt && pads[i] === prompt.hex) record(); else setMsg("Cor errada!");
    }
  };

  const running = phase !== "idle" && phase !== "done";
  const best = times.length ? Math.min(...times) : 0;
  const avg = times.length ? Math.round(times.reduce((a, b) => a + b, 0) / times.length) : 0;

  const padStyle = (i) => {
    if (mode === "reacao" || modeRef.current === "reacao") {
      if (phase === "live" && i === active) return { background: "#F4C430", boxShadow: "0 0 24px rgba(244,196,48,0.7)" };
      return { background: "rgba(255,255,255,0.06)", boxShadow: "inset 0 0 0 1px rgba(255,255,255,0.12)" };
    }
    const c = pads[i];
    if (phase === "live" && c) return { background: c, boxShadow: `0 0 16px ${c}66` };
    return { background: "rgba(255,255,255,0.06)", boxShadow: "inset 0 0 0 1px rgba(255,255,255,0.12)" };
  };

  return (
    <div className="space-y-5 max-w-3xl mx-auto" data-testid="treino-page">
      <div className="flex items-center gap-2">
        <Zap className="text-[#F4C430]" />
        <h1 className="font-cond text-3xl sm:text-4xl font-extrabold uppercase text-[#0C3B1E]">Treino de Reação</h1>
      </div>
      <p className="text-sm text-muted-foreground -mt-2">Treino visual, ocular e de velocidade de reação. 10 sinais por sessão.</p>

      {/* Mode selector */}
      <div className="grid grid-cols-2 gap-2">
        <button data-testid="mode-reacao" disabled={running}
          onClick={() => setMode("reacao")}
          className={`rounded-xl border-2 p-3 text-left transition-colors ${mode === "reacao" ? "border-[#0C3B1E] bg-[#0C3B1E] text-white" : "border-gray-200 bg-white text-[#0C3B1E]"} ${running ? "opacity-60" : ""}`}>
          <div className="flex items-center gap-2 font-bold uppercase text-sm"><Zap size={16} /> Reação</div>
          <div className={`text-xs mt-1 ${mode === "reacao" ? "text-white/80" : "text-muted-foreground"}`}>Toca no alvo dourado assim que acender.</div>
        </button>
        <button data-testid="mode-cores" disabled={running}
          onClick={() => setMode("cores")}
          className={`rounded-xl border-2 p-3 text-left transition-colors ${mode === "cores" ? "border-[#0C3B1E] bg-[#0C3B1E] text-white" : "border-gray-200 bg-white text-[#0C3B1E]"} ${running ? "opacity-60" : ""}`}>
          <div className="flex items-center gap-2 font-bold uppercase text-sm"><Eye size={16} /> Cores</div>
          <div className={`text-xs mt-1 ${mode === "cores" ? "text-white/80" : "text-muted-foreground"}`}>Toca só na cor pedida (discriminação visual).</div>
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-2">
        {[["Sinal", `${Math.min(round + (phase === "pause" ? 1 : 0), MAX_ROUNDS)}/${MAX_ROUNDS}`],
          ["Último", times.length ? `${times[times.length - 1]}ms` : "—"],
          ["Média", avg ? `${avg}ms` : "—"],
          ["Melhor", best ? `${best}ms` : "—"]].map(([l, v], idx) => (
          <div key={l} className="rounded-lg border border-gray-200 p-2 text-center bg-white" data-testid={`stat-${idx}`}>
            <div className="text-[10px] uppercase text-muted-foreground">{l}</div>
            <div className="font-cond text-xl font-extrabold text-[#0C3B1E]">{v}</div>
          </div>
        ))}
      </div>

      {/* Message banner */}
      <div className={`rounded-xl px-4 py-3 text-center font-bold text-lg transition-colors ${
        phase === "live" ? "bg-[#F4C430] text-[#0C3B1E]" : phase === "wait" ? "bg-[#0F3B43] text-white" : "bg-gray-100 text-[#0C3B1E]"
      }`} data-testid="game-message">
        {msg}
      </div>

      {/* Play grid */}
      <div className="rounded-2xl p-3" style={{ background: "linear-gradient(160deg,#0C3B1E,#0F3B43)" }}>
        <div className="grid grid-cols-3 gap-2.5">
          {Array.from({ length: GRID }).map((_, i) => (
            <button key={i} type="button" data-testid={`pad-${i}`} onClick={() => onPad(i)}
              className="aspect-square rounded-xl transition-all active:scale-95" style={padStyle(i)} />
          ))}
        </div>
      </div>

      {/* Controls */}
      <div className="flex gap-2">
        {!running ? (
          <Button onClick={start} data-testid="start-btn" className="flex-1 h-12 bg-[#0C3B1E] hover:bg-[#0a3018] text-white font-bold uppercase tracking-wide">
            <Play className="mr-2" size={18} /> {phase === "done" ? "Jogar outra vez" : "Começar"}
          </Button>
        ) : (
          <Button onClick={() => { clearTimer(); setPh("idle"); setMsg("Sessão parada."); }} data-testid="stop-btn"
            variant="outline" className="flex-1 h-12 font-bold uppercase">
            <RotateCcw className="mr-2" size={18} /> Parar
          </Button>
        )}
      </div>

      {/* Finish summary */}
      {phase === "done" && times.length > 0 && (
        <div className="rounded-2xl border-2 border-[#F4C430] p-5 bg-white space-y-2" data-testid="finish-summary">
          <div className="flex items-center gap-2 font-cond text-2xl font-extrabold uppercase text-[#0C3B1E]"><Trophy className="text-[#F4C430]" /> Resultado</div>
          <div className="grid grid-cols-3 gap-3 text-center">
            <div><div className="text-xs uppercase text-muted-foreground">Média</div><div className="font-cond text-3xl font-extrabold text-[#0C3B1E]">{avg}<span className="text-base">ms</span></div></div>
            <div><div className="text-xs uppercase text-muted-foreground">Melhor</div><div className="font-cond text-3xl font-extrabold text-green-600">{best}<span className="text-base">ms</span></div></div>
            <div><div className="text-xs uppercase text-muted-foreground">Cedo demais</div><div className="font-cond text-3xl font-extrabold text-red-500">{tooSoon}</div></div>
          </div>
        </div>
      )}
    </div>
  );
}
