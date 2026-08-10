import { useEffect, useState } from "react";
import api, { API, formatApiErrorDetail } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { SelectGrid } from "@/components/SelectGrid";
import { CourtZone, CourtDistance, GoalTarget } from "@/components/VisualPickers";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import {
  SITUACOES, ZONAS, DISTANCIAS, TECNICAS, DECISOES, SEGUIMENTOS,
  AVALIACOES, OFFENSIVE_BUTTONS, EMPTY_ACTION, EMPTY_OFFENSIVE,
} from "@/lib/constants";
import { Plus, Trash2, Save, Minus } from "lucide-react";

const Section = ({ title, children }) => (
  <section className="rounded-xl border border-gray-200 p-2.5 sm:p-3 bg-white space-y-2.5">
    {title && <h2 className="font-cond text-lg font-bold uppercase text-[#0C3B1E]">{title}</h2>}
    {children}
  </section>
);

export default function Registo() {
  const [gks, setGks] = useState([]);
  const [gkId, setGkId] = useState("");
  const [newGk, setNewGk] = useState(false);
  const [general, setGeneral] = useState({
    goalkeeper_name: "", team: "", session_number: "", opponent: "",
    date: new Date().toISOString().slice(0, 10), competition: "", result: "", coach_notes: "",
  });
  const [action, setAction] = useState({ ...EMPTY_ACTION });
  const [actions, setActions] = useState([]);
  const [offensive, setOffensive] = useState({ ...EMPTY_OFFENSIVE });
  const [saving, setSaving] = useState(false);

  const loadGks = () => api.get("/goalkeepers").then((r) => setGks(r.data)).catch(() => {});
  useEffect(() => { loadGks(); }, []);

  const onSelectGk = (id) => {
    setGkId(id); setNewGk(id === "__new__");
    if (id && id !== "__new__") {
      const g = gks.find((x) => x.id === id);
      if (g) setGeneral((p) => ({ ...p, goalkeeper_name: g.name, team: g.team || "" }));
    } else if (id === "__new__") {
      setGeneral((p) => ({ ...p, goalkeeper_name: "", team: "" }));
    }
  };

  const addAction = () => {
    if (!action.situation && !action.technique) {
      toast.error("Preenche pelo menos a Situação ou a Técnica da ação.");
      return;
    }
    setActions((a) => [...a, action]);
    setAction({ ...EMPTY_ACTION });
    toast.success("Ação adicionada. Formulário limpo.");
    const el = document.getElementById("action-block");
    if (el) window.scrollTo({ top: el.offsetTop - 70, behavior: "smooth" });
  };

  const removeAction = (i) => setActions((a) => a.filter((_, idx) => idx !== i));
  const bumpOff = (k, d) => setOffensive((o) => ({ ...o, [k]: Math.max(0, o[k] + d) }));

  const needFeedback = action.evaluation === "amarelo" || action.evaluation === "vermelho";

  const saveReport = async () => {
    let goalkeeper_id = gkId;
    if (!general.goalkeeper_name.trim()) { toast.error("Indica o nome do guarda-redes."); return; }
    if (actions.length === 0) { toast.error("Adiciona pelo menos uma ação."); return; }
    setSaving(true);
    try {
      if (newGk || !goalkeeper_id || goalkeeper_id === "__new__") {
        const { data } = await api.post("/goalkeepers", { name: general.goalkeeper_name.trim(), team: general.team });
        goalkeeper_id = data.id;
        await loadGks();
      }
      const payload = { ...general, goalkeeper_id, goalkeeper_name: general.goalkeeper_name.trim(), actions, offensive };
      const { data } = await api.post("/reports", payload);
      toast.success("Relatório guardado na base de dados.");
      setActions([]); setOffensive({ ...EMPTY_OFFENSIVE }); setAction({ ...EMPTY_ACTION });
      window.open(`${API}/reports/${data.id}/pdf`, "_blank");
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail));
    } finally { setSaving(false); }
  };

  return (
    <div className="space-y-3 max-w-5xl mx-auto pb-28" data-testid="registo-page">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h1 className="font-cond text-2xl sm:text-3xl font-extrabold uppercase text-[#0C3B1E]">Registo</h1>
        <div className="text-sm text-muted-foreground">Ações: <span className="font-bold text-[#0C3B1E]">{actions.length}</span></div>
      </div>

      {/* General */}
      <Section title="Relatório">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
          <div className="space-y-1">
            <Label className="text-xs">Guarda-redes</Label>
            <select value={gkId} onChange={(e) => onSelectGk(e.target.value)} data-testid="gk-select"
              className="w-full h-10 rounded-lg border border-gray-300 px-2 bg-white text-sm">
              <option value="">— Selecionar —</option>
              {gks.map((g) => <option key={g.id} value={g.id}>{g.name} {g.team ? `(${g.team})` : ""}</option>)}
              <option value="__new__">+ Criar novo guarda-redes</option>
            </select>
          </div>
          <div className="space-y-1"><Label className="text-xs">Nome</Label>
            <Input value={general.goalkeeper_name} data-testid="gk-name" onChange={(e) => setGeneral({ ...general, goalkeeper_name: e.target.value })} placeholder="Nome" /></div>
          <div className="space-y-1"><Label className="text-xs">Escalão / Equipa</Label>
            <Input value={general.team} data-testid="gk-team" onChange={(e) => setGeneral({ ...general, team: e.target.value })} placeholder="Ex: Sub-15" /></div>
          <div className="space-y-1"><Label className="text-xs">Nº treino/jogo</Label>
            <Input value={general.session_number} data-testid="gen-session" onChange={(e) => setGeneral({ ...general, session_number: e.target.value })} placeholder="Ex: UT2 ou J4" /></div>
          <div className="space-y-1"><Label className="text-xs">Adversário</Label>
            <Input value={general.opponent} data-testid="gen-opponent" onChange={(e) => setGeneral({ ...general, opponent: e.target.value })} /></div>
          <div className="space-y-1"><Label className="text-xs">Data</Label>
            <Input type="date" value={general.date} data-testid="gen-date" onChange={(e) => setGeneral({ ...general, date: e.target.value })} /></div>
          <div className="space-y-1"><Label className="text-xs">Competição</Label>
            <Input value={general.competition} data-testid="gen-competition" onChange={(e) => setGeneral({ ...general, competition: e.target.value })} /></div>
          <div className="space-y-1"><Label className="text-xs">Resultado</Label>
            <Input value={general.result} data-testid="gen-result" onChange={(e) => setGeneral({ ...general, result: e.target.value })} placeholder="Ex: 3-2" /></div>
        </div>
        <div className="space-y-1"><Label className="text-xs">Notas gerais do treinador</Label>
          <Textarea value={general.coach_notes} data-testid="gen-notes" onChange={(e) => setGeneral({ ...general, coach_notes: e.target.value })} rows={2} /></div>
      </Section>

      {/* Action block */}
      <div id="action-block" className="rounded-xl border-2 border-[#0C3B1E]/25 p-2.5 sm:p-3 bg-white space-y-3">
        <h2 className="font-cond text-lg font-bold uppercase text-[#0C3B1E]">Nova ação de jogo</h2>

        <SelectGrid label="Situação" options={SITUACOES} value={action.situation} testid="sel-situacao"
          onChange={(v) => setAction({ ...action, situation: v })} cols="grid-cols-2 sm:grid-cols-3 lg:grid-cols-4" />

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="space-y-2">
            <CourtZone value={action.zone} onChange={(v) => setAction({ ...action, zone: v })} />
            <SelectGrid label="Zona (rápido)" options={ZONAS} value={action.zone} testid="sel-zona"
              onChange={(v) => setAction({ ...action, zone: v })} cols="grid-cols-2 sm:grid-cols-3" />
          </div>
          <div className="space-y-2">
            <CourtDistance value={action.distance} onChange={(v) => setAction({ ...action, distance: v })} />
            <SelectGrid label="Distância (rápido)" options={DISTANCIAS} value={action.distance} testid="sel-distancia"
              onChange={(v) => setAction({ ...action, distance: v })} cols="grid-cols-2 sm:grid-cols-3" />
          </div>
        </div>

        <GoalTarget value={action.finish_type} onChange={(v) => setAction({ ...action, finish_type: v })} />

        <SelectGrid label="Técnica utilizada" options={TECNICAS} value={action.technique} testid="sel-tecnica"
          onChange={(v) => setAction({ ...action, technique: v })} cols="grid-cols-2 sm:grid-cols-3 lg:grid-cols-4" />
        <SelectGrid label="Tomada de decisão (várias)" options={DECISOES} value={action.decisions} multi testid="sel-decisao"
          onChange={(v) => setAction({ ...action, decisions: v })} cols="grid-cols-2 sm:grid-cols-3" />
        <SelectGrid label="Seguimento" options={SEGUIMENTOS} value={action.followup} testid="sel-seguimento"
          onChange={(v) => setAction({ ...action, followup: v })} cols="grid-cols-2 sm:grid-cols-3 lg:grid-cols-4" />

        {/* Evaluation */}
        <div className="space-y-1.5">
          <div className="text-[11px] font-bold uppercase tracking-[0.12em] text-[#0F3B43]">Avaliação do treinador</div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5">
            {AVALIACOES.map((av) => (
              <button type="button" key={av.key} data-testid={`sel-avaliacao-${av.key}`}
                onClick={() => setAction({ ...action, evaluation: action.evaluation === av.key ? "" : av.key })}
                className="select-tile min-h-[34px] rounded-md border-2 font-bold uppercase text-[11px] sm:text-xs flex items-center justify-center"
                style={{
                  backgroundColor: action.evaluation === av.key ? av.color : "#fff",
                  borderColor: av.color, color: action.evaluation === av.key ? "#fff" : av.color,
                }}>
                {av.label}
              </button>
            ))}
          </div>
        </div>

        {needFeedback && (
          <div className="space-y-1">
            <Label className="text-red-600 text-xs">Feedback breve (para {action.evaluation})</Label>
            <Input value={action.feedback} data-testid="action-feedback"
              onChange={(e) => setAction({ ...action, feedback: e.target.value })} placeholder="O que melhorar" />
          </div>
        )}

        <div className="space-y-1">
          <Label className="text-xs">Notas / observações da ação</Label>
          <Textarea value={action.notes} rows={2} data-testid="action-notes"
            onChange={(e) => setAction({ ...action, notes: e.target.value })} />
        </div>

        <Button onClick={addAction} data-testid="add-action-btn"
          className="w-full h-11 bg-[#0F3B43] hover:bg-[#0b2d33] text-white font-bold uppercase tracking-wide">
          <Plus className="mr-2" size={18} /> Adicionar ação
        </Button>
      </div>

      {/* Actions TABLE */}
      {actions.length > 0 && (
        <Section title={`Tabela de ações (${actions.length})`}>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  {["#", "Situação", "Zona", "Distância", "Finalização", "Técnica", "Decisão", "Seguimento", "Aval.", "Notas/Feedback", ""].map((h) => (
                    <TableHead key={h} className="text-[11px] whitespace-nowrap">{h}</TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {actions.map((a, i) => {
                  const av = AVALIACOES.find((x) => x.key === a.evaluation);
                  return (
                    <TableRow key={i} data-testid={`action-row-${i}`} className="text-[11px]">
                      <TableCell>{i + 1}</TableCell>
                      <TableCell className="whitespace-nowrap">{a.situation || "—"}</TableCell>
                      <TableCell className="whitespace-nowrap">{a.zone || "—"}</TableCell>
                      <TableCell className="whitespace-nowrap">{a.distance || "—"}</TableCell>
                      <TableCell className="whitespace-nowrap">{a.finish_type || "—"}</TableCell>
                      <TableCell className="whitespace-nowrap">{a.technique || "—"}</TableCell>
                      <TableCell className="whitespace-nowrap">{(a.decisions || []).join(", ") || "—"}</TableCell>
                      <TableCell className="whitespace-nowrap">{a.followup || "—"}</TableCell>
                      <TableCell><span className="inline-block w-5 h-5 rounded" style={{ backgroundColor: av?.color || "#e5e7eb" }} /></TableCell>
                      <TableCell className="max-w-[160px]">{[a.feedback, a.notes].filter(Boolean).join(" · ") || "—"}</TableCell>
                      <TableCell><button onClick={() => removeAction(i)} data-testid={`remove-action-${i}`} className="text-red-500 hover:text-red-700"><Trash2 size={16} /></button></TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        </Section>
      )}

      {/* Offensive */}
      <Section title="Ações ofensivas (toca para adicionar)">
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5">
          {OFFENSIVE_BUTTONS.map((b) => {
            const ok = b.tone === "ok";
            return (
              <div key={b.key} className={`rounded-lg border p-1.5 flex flex-col items-center ${ok ? "border-green-300" : "border-red-300"}`}>
                <button type="button" onClick={() => bumpOff(b.key, 1)} data-testid={`off-add-${b.key}`}
                  className={`w-full min-h-[32px] rounded-md text-[11px] font-bold text-white ${ok ? "bg-green-600 hover:bg-green-700" : "bg-red-500 hover:bg-red-600"}`}>
                  {b.label}
                </button>
                <div className="flex items-center gap-2 mt-1">
                  <button type="button" onClick={() => bumpOff(b.key, -1)} data-testid={`off-minus-${b.key}`}
                    className="w-6 h-6 rounded-md border flex items-center justify-center text-gray-500"><Minus size={13} /></button>
                  <span data-testid={`off-count-${b.key}`} className="font-bold text-base w-6 text-center">{offensive[b.key]}</span>
                </div>
              </div>
            );
          })}
        </div>
      </Section>

      {actions.length > 0 && (
        <div className="sticky bottom-0 bg-white/95 backdrop-blur py-3 border-t border-gray-200">
          <Button onClick={saveReport} disabled={saving} data-testid="save-report-btn"
            className="w-full h-12 bg-[#0C3B1E] hover:bg-[#0a3018] text-white font-bold uppercase tracking-wide">
            <Save className="mr-2" size={18} /> {saving ? "A guardar..." : "Guardar relatório + PDF"}
          </Button>
        </div>
      )}
    </div>
  );
}
