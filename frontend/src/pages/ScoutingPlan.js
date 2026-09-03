import { useEffect, useState } from "react";
import { useParams, useLocation, useNavigate } from "react-router-dom";
import api, { formatApiErrorDetail } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { ArrowLeft, Save, FileText, Plus, Trash2, ClipboardList, ShieldCheck } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const DEFAULT_GKS = ["Guilherme Cintra", "Daniel Osuji", "Rodrigo Prazeres"];
const SET_PIECES = [
  { key: "penalti", label: "Penálti" },
  { key: "livre", label: "Livre" },
  { key: "livre10", label: "Livre de 10 metros" },
];

// resize + compress an image file to a base64 dataURL
function resizeImage(file, max = 520) {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const img = new Image();
      img.onload = () => {
        let { width, height } = img;
        if (width > height && width > max) { height = Math.round((height * max) / width); width = max; }
        else if (height > max) { width = Math.round((width * max) / height); height = max; }
        const canvas = document.createElement("canvas");
        canvas.width = width; canvas.height = height;
        canvas.getContext("2d").drawImage(img, 0, 0, width, height);
        resolve(canvas.toDataURL("image/jpeg", 0.85));
      };
      img.src = e.target.result;
    };
    reader.readAsDataURL(file);
  });
}

export default function ScoutingPlan() {
  const { gameId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const [gks, setGks] = useState([]);
  const [form, setForm] = useState(null);

  useEffect(() => {
    const game = location.state?.game || {};
    Promise.all([api.get("/goalkeepers"), api.get(`/scouting/${gameId}`)]).then(([g, s]) => {
      setGks(g.data || []);
      if (s.data?.exists) {
        setForm({
          opponent: s.data.opponent || "", competition: s.data.competition || "", round: s.data.round || "",
          date: s.data.date || "", time: s.data.time || "", venue: s.data.venue || "", home_away: s.data.home_away || "Casa",
          opponent_logo: s.data.opponent_logo || "", called_gks: s.data.called_gks || [],
          set_pieces: s.data.set_pieces || {}, opposition_players: s.data.opposition_players || [],
          match_notes: s.data.match_notes || "",
        });
      } else {
        const called = DEFAULT_GKS.map((name) => {
          const db = (g.data || []).find((x) => (x.name || "").toLowerCase().includes(name.toLowerCase().split(" ")[0]) && (x.name || "").toLowerCase().includes(name.toLowerCase().split(" ").slice(-1)[0]));
          return db ? { name: db.name, photo: db.photo || "", gk_id: db.id } : { name, photo: "" };
        });
        setForm({
          opponent: game.opponent || "", competition: game.competition || "", round: game.round || "",
          date: game.date || "", time: game.time || "", venue: game.venue || "", home_away: game.home_away || "Casa",
          opponent_logo: "", called_gks: called,
          set_pieces: { penalti: { mode: "campo", gk: "" }, livre: { mode: "campo", gk: "" }, livre10: { mode: "campo", gk: "" } },
          opposition_players: [], match_notes: "",
        });
      }
    }).catch((err) => toast.error(formatApiErrorDetail(err.response?.data?.detail)));
  }, [gameId, location.state]);

  const set = (patch) => setForm((f) => ({ ...f, ...patch }));

  const calledHas = (name) => (form?.called_gks || []).some((c) => c.name === name);
  const clearSpFor = (name, sp) => Object.fromEntries(Object.entries(sp || {}).map(([k, v]) => [k, v?.gk === name ? { ...v, gk: "" } : v]));
  const toggleGk = (gk) => {
    if (calledHas(gk.name)) set({ called_gks: form.called_gks.filter((c) => c.name !== gk.name), set_pieces: clearSpFor(gk.name, form.set_pieces) });
    else set({ called_gks: [...form.called_gks, { name: gk.name, photo: gk.photo || "", gk_id: gk.id }] });
  };
  const removeCalled = (name) => set({ called_gks: form.called_gks.filter((c) => c.name !== name), set_pieces: clearSpFor(name, form.set_pieces) });
  const [manual, setManual] = useState("");
  const addManual = () => { const n = manual.trim(); if (!n) return; if (calledHas(n)) { toast.error("Já convocado."); return; } set({ called_gks: [...form.called_gks, { name: n, photo: "" }] }); setManual(""); };

  const setSp = (key, patch) => set({ set_pieces: { ...form.set_pieces, [key]: { ...(form.set_pieces[key] || {}), ...patch } } });

  const addPlayer = () => set({ opposition_players: [...form.opposition_players, { id: crypto.randomUUID(), name: "", number: "", position: "", foot: "", notes: "", photo: "" }] });
  const setPlayer = (i, patch) => set({ opposition_players: form.opposition_players.map((p, idx) => idx === i ? { ...p, ...patch } : p) });
  const removePlayer = (i) => set({ opposition_players: form.opposition_players.filter((_, idx) => idx !== i) });

  const uploadLogo = async (file) => set({ opponent_logo: await resizeImage(file, 400) });
  const uploadPlayerPhoto = async (i, file) => setPlayer(i, { photo: await resizeImage(file, 420) });

  const save = async () => {
    try { await api.put(`/scouting/${gameId}`, form); toast.success("Scouting guardado."); return true; }
    catch (err) { toast.error(formatApiErrorDetail(err.response?.data?.detail)); return false; }
  };
  const genPdf = async () => { if (await save()) window.open(`${API}/scouting/${gameId}/pdf`, "_blank"); };

  if (!form) return <div className="text-[#0C3B1E] font-cond text-2xl">A carregar...</div>;

  const calledNames = (form.called_gks || []).map((c) => c.name);

  return (
    <div className="space-y-5" data-testid="scouting-page">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <button onClick={() => navigate("/microciclo")} data-testid="sp-back" className="inline-flex items-center gap-1 text-[#0F3B43] font-semibold"><ArrowLeft size={16} /> Voltar ao microciclo</button>
        <div className="flex gap-2">
          <Button onClick={save} variant="outline" data-testid="sp-save-btn" className="border-[#0C3B1E] text-[#0C3B1E]"><Save size={16} className="mr-2" /> Guardar</Button>
          <Button onClick={genPdf} data-testid="sp-pdf-btn" className="bg-[#0C3B1E] hover:bg-[#0a3018] text-white"><FileText size={16} className="mr-2" /> Gerar PDF</Button>
        </div>
      </div>

      <div className="rounded-2xl bg-[#0C3B1E] text-white p-5 border-b-4 border-[#C8A24B]">
        <div className="flex items-center gap-2 text-[#CFE3D6] text-xs uppercase tracking-[0.2em]"><ClipboardList size={14} /> Scouting &amp; Match Plan</div>
        <h1 className="font-cond text-3xl sm:text-4xl font-extrabold uppercase mt-1">vs {form.opponent || "adversário"}</h1>
      </div>

      {/* Info do jogo */}
      <Section title="Informação do jogo">
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
          <Field label="Adversário"><Input value={form.opponent} data-testid="sp-opponent" onChange={(e) => set({ opponent: e.target.value })} /></Field>
          <Field label="Competição"><Input value={form.competition} data-testid="sp-competition" onChange={(e) => set({ competition: e.target.value })} /></Field>
          <Field label="Jornada"><Input value={form.round} data-testid="sp-round" onChange={(e) => set({ round: e.target.value })} /></Field>
          <Field label="Data"><Input type="date" value={form.date} data-testid="sp-date" onChange={(e) => set({ date: e.target.value })} /></Field>
          <Field label="Hora"><Input type="time" value={form.time} data-testid="sp-time" onChange={(e) => set({ time: e.target.value })} /></Field>
          <Field label="Local"><Input value={form.venue} data-testid="sp-venue" onChange={(e) => set({ venue: e.target.value })} /></Field>
          <Field label="Casa / Fora">
            <div className="flex gap-2">
              {["Casa", "Fora"].map((v) => <button key={v} type="button" data-testid={`sp-ha-${v.toLowerCase()}`} onClick={() => set({ home_away: v })} className={`flex-1 px-3 py-2 rounded-lg text-sm font-semibold border-2 ${form.home_away === v ? "bg-[#0C3B1E] text-white border-[#0C3B1E]" : "bg-white text-[#0C3B1E] border-gray-200"}`}>{v}</button>)}
            </div>
          </Field>
          <Field label="Logótipo do adversário">
            <div className="flex items-center gap-3">
              {form.opponent_logo ? <img src={form.opponent_logo} alt="logo" className="w-14 h-14 object-contain rounded-lg border border-gray-200 bg-white" /> : <div className="w-14 h-14 rounded-lg bg-gray-100 border border-gray-200" />}
              <input type="file" accept="image/*" data-testid="sp-logo" onChange={(e) => e.target.files?.[0] && uploadLogo(e.target.files[0])} className="text-sm file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:bg-[#0C3B1E] file:text-white file:text-xs file:font-semibold file:cursor-pointer hover:file:bg-[#0a3018]" />
            </div>
          </Field>
        </div>
      </Section>

      {/* GRs convocados */}
      <Section title="Guarda-redes convocados">
        <div className="grid sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
          {gks.map((gk) => {
            const on = calledHas(gk.name);
            return (
              <button key={gk.id} type="button" data-testid={`sp-gk-${gk.id}`} onClick={() => toggleGk(gk)} className={`flex items-center gap-2 p-2.5 rounded-xl border-2 text-left transition-colors ${on ? "border-[#C8A24B] bg-[#fbf7ec]" : "border-gray-200 bg-white"}`}>
                {gk.photo ? <img src={gk.photo} alt="" className="w-11 h-11 rounded-full object-cover" /> : <div className="w-11 h-11 rounded-full bg-[#0F3B43] text-white flex items-center justify-center text-xs font-bold">GR</div>}
                <span className="flex-1 font-semibold text-sm text-[#0C3B1E] leading-tight">{gk.name}</span>
                <span className={`w-5 h-5 rounded-md border-2 flex items-center justify-center ${on ? "bg-[#0C3B1E] border-[#0C3B1E] text-white" : "border-gray-300"}`}>{on ? "✓" : ""}</span>
              </button>
            );
          })}
          {form.called_gks.filter((c) => !gks.some((g) => g.name === c.name)).map((c) => (
            <div key={c.name} data-testid={`sp-manual-${c.name}`} className="flex items-center gap-2 p-2.5 rounded-xl border-2 border-[#C8A24B] bg-[#fbf7ec]">
              <div className="w-11 h-11 rounded-full bg-[#0F3B43] text-white flex items-center justify-center text-xs font-bold">GR</div>
              <span className="flex-1 font-semibold text-sm text-[#0C3B1E]">{c.name}</span>
              <button onClick={() => removeCalled(c.name)} className="text-red-500"><Trash2 size={15} /></button>
            </div>
          ))}
        </div>
        <div className="flex gap-2 mt-3 max-w-sm">
          <Input value={manual} data-testid="sp-manual-input" placeholder="Adicionar GR manualmente" onChange={(e) => setManual(e.target.value)} onKeyDown={(e) => e.key === "Enter" && addManual()} />
          <Button onClick={addManual} data-testid="sp-manual-add" variant="outline" className="border-[#0C3B1E] text-[#0C3B1E]"><Plus size={16} /></Button>
        </div>
      </Section>

      {/* Set-piece plan */}
      <Section title="Goalkeeper Set-Piece Plan">
        <div className="space-y-3">
          {SET_PIECES.map(({ key, label }) => {
            const sp = form.set_pieces[key] || { mode: "campo", gk: "" };
            const campo = sp.mode === "campo";
            return (
              <div key={key} data-testid={`sp-setpiece-${key}`} className="flex flex-col sm:flex-row sm:items-center gap-3 p-3 rounded-xl border-2 border-gray-200 bg-white">
                <div className="flex items-center gap-2 sm:w-52 font-cond font-extrabold uppercase text-[#0C3B1E]"><ShieldCheck size={18} className="text-[#C8A24B]" /> {label}</div>
                <label className="flex items-center gap-2 text-sm font-semibold text-[#0F3B43]">
                  <input type="checkbox" data-testid={`sp-setpiece-campo-${key}`} checked={campo} onChange={(e) => setSp(key, { mode: e.target.checked ? "campo" : "gk" })} className="w-4 h-4 accent-[#0C3B1E]" />
                  GR que estiver em campo
                </label>
                {!campo && (
                  <select data-testid={`sp-setpiece-select-${key}`} value={sp.gk} onChange={(e) => setSp(key, { gk: e.target.value })} className="flex-1 px-3 py-2 rounded-lg border-2 border-gray-200 text-sm bg-white">
                    <option value="">— Escolher GR —</option>
                    {calledNames.map((n) => <option key={n} value={n}>{n}</option>)}
                  </select>
                )}
              </div>
            );
          })}
        </div>
      </Section>

      {/* Opposition players */}
      <Section title="Opposition Key Players" action={<Button onClick={addPlayer} data-testid="sp-add-player" size="sm" className="bg-[#0C3B1E] hover:bg-[#0a3018] text-white"><Plus size={14} className="mr-1" /> Adicionar jogador</Button>}>
        {form.opposition_players.length === 0 && <div className="text-sm text-muted-foreground">Sem jogadores. Adiciona os principais adversários.</div>}
        <div className="grid md:grid-cols-2 gap-3">
          {form.opposition_players.map((p, i) => (
            <div key={p.id || i} data-testid={`sp-player-${i}`} className="rounded-xl border-2 border-gray-200 bg-white p-3 flex gap-3">
              <div className="shrink-0 space-y-1">
                {p.photo ? <img src={p.photo} alt="" className="w-20 h-20 rounded-lg object-cover" /> : <div className="w-20 h-20 rounded-lg bg-gray-100 border border-gray-200 flex items-center justify-center text-[10px] text-gray-400 text-center">Sem foto</div>}
                <input type="file" accept="image/*" data-testid={`sp-player-photo-${i}`} onChange={(e) => e.target.files?.[0] && uploadPlayerPhoto(i, e.target.files[0])} className="text-[10px] w-20 file:mr-1 file:py-0.5 file:px-1.5 file:rounded file:border-0 file:bg-[#0C3B1E] file:text-white file:text-[9px] file:font-semibold file:cursor-pointer" />
              </div>
              <div className="flex-1 space-y-1.5">
                <div className="flex gap-1.5">
                  <Input value={p.number} data-testid={`sp-player-number-${i}`} onChange={(e) => setPlayer(i, { number: e.target.value })} placeholder="#" className="w-14" />
                  <Input value={p.name} data-testid={`sp-player-name-${i}`} onChange={(e) => setPlayer(i, { name: e.target.value })} placeholder="Nome" className="flex-1" />
                  <button onClick={() => removePlayer(i)} data-testid={`sp-player-del-${i}`} className="text-red-500 shrink-0 px-1"><Trash2 size={16} /></button>
                </div>
                <div className="flex gap-1.5">
                  <Input value={p.position} data-testid={`sp-player-position-${i}`} onChange={(e) => setPlayer(i, { position: e.target.value })} placeholder="Posição" className="flex-1" />
                  <select value={p.foot} data-testid={`sp-player-foot-${i}`} onChange={(e) => setPlayer(i, { foot: e.target.value })} className="w-28 px-2 rounded-md border-2 border-gray-200 text-sm bg-white">
                    <option value="">Pé forte</option>
                    <option value="Direito">Direito</option>
                    <option value="Esquerdo">Esquerdo</option>
                    <option value="Ambos">Ambos</option>
                  </select>
                </div>
                <Textarea rows={2} value={p.notes} data-testid={`sp-player-notes-${i}`} onChange={(e) => setPlayer(i, { notes: e.target.value })} placeholder="Observações/notas" />
              </div>
            </div>
          ))}
        </div>
      </Section>

      {/* Match notes */}
      <Section title="Match Notes">
        <Textarea rows={6} value={form.match_notes} data-testid="sp-match-notes" onChange={(e) => set({ match_notes: e.target.value })} placeholder="Estratégia, alertas, comportamentos do adversário, notas para os GR, situações especiais..." />
      </Section>
    </div>
  );
}

const Section = ({ title, action, children }) => (
  <section className="space-y-3">
    <div className="flex items-center justify-between gap-2 border-l-4 border-[#C8A24B] pl-3">
      <h2 className="font-cond text-xl sm:text-2xl font-extrabold uppercase text-[#0C3B1E]">{title}</h2>
      {action}
    </div>
    {children}
  </section>
);

const Field = ({ label, children }) => (
  <div className="space-y-1"><Label className="text-xs uppercase tracking-wide text-muted-foreground">{label}</Label>{children}</div>
);
