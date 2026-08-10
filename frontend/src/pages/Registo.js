import { useEffect, useState } from "react";
import api, { API, formatApiErrorDetail } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { SelectGrid } from "@/components/SelectGrid";
import {
  SITUACOES, ZONAS, DISTANCIAS, FINALIZACOES, TECNICAS, DECISOES,
  SEGUIMENTOS, AVALIACOES, EMPTY_ACTION, EMPTY_OFFENSIVE,
} from "@/lib/constants";
import { Plus, Trash2, Save, Minus } from "lucide-react";

function Counter({ label, okKey, errKey, off, setOff, color }) {
  const set = (k, delta) => setOff({ ...off, [k]: Math.max(0, off[k] + delta) });
  const Cell = ({ k, tone }) => (
    <div className="flex items-center gap-2">
      <button type="button" onClick={() => set(k, -1)} data-testid={`off-${k}-minus`}
        className="w-9 h-9 rounded-lg border-2 border-gray-200 flex items-center justify-center hover:border-[#0C3B1E]"><Minus size={16} /></button>
      <span className={`w-8 text-center font-bold text-lg ${tone}`} data-testid={`off-${k}-value`}>{off[k]}</span>
      <button type="button" onClick={() => set(k, 1)} data-testid={`off-${k}-plus`}
        className="w-9 h-9 rounded-lg border-2 border-gray-200 flex items-center justify-center hover:border-[#0C3B1E]"><Plus size={16} /></button>
    </div>
  );
  return (
    <div className="rounded-xl border border-gray-200 p-4 bg-white">
      <div className="font-cond font-bold uppercase text-lg mb-3" style={{ color }}>{label}</div>
      <div className="flex items-center justify-between">
        <div><div className="text-xs uppercase text-green-700 font-bold mb-1">Certo</div><Cell k={okKey} tone="text-green-700" /></div>
        <div><div className="text-xs uppercase text-red-600 font-bold mb-1">Errado</div><Cell k={errKey} tone="text-red-600" /></div>
      </div>
    </div>
  );
}

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
    window.scrollTo({ top: document.getElementById("action-block").offsetTop - 80, behavior: "smooth" });
  };

  const removeAction = (i) => setActions((a) => a.filter((_, idx) => idx !== i));

  const needFeedback = action.evaluation === "amarelo" || action.evaluation === "vermelho";

  const saveReport = async () => {
    let goalkeeper_id = gkId;
    if (!general.goalkeeper_name.trim()) { toast.error("Indica o nome do guarda-redes."); return; }
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
      // reset
      setActions([]); setOffensive({ ...EMPTY_OFFENSIVE }); setAction({ ...EMPTY_ACTION });
      // offer PDF
      downloadPdf(data.id);
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail));
    } finally { setSaving(false); }
  };

  const downloadPdf = (rid) => {
    window.open(`${API}/reports/${rid}/pdf`, "_blank");
  };

  return (
    <div className="space-y-6" data-testid="registo-page">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="font-cond text-4xl font-extrabold uppercase text-[#0C3B1E]">Registo</h1>
        <div className="text-sm text-muted-foreground">Ações registadas: <span className="font-bold text-[#0C3B1E]">{actions.length}</span></div>
      </div>

      {/* General */}
      <section className="rounded-2xl border border-gray-200 p-5 bg-gray-50 space-y-4">
        <h2 className="font-cond text-2xl font-bold uppercase text-[#0F3B43]">Relatório</h2>
        <div className="grid md:grid-cols-3 gap-4">
          <div className="space-y-2">
            <Label>Guarda-redes</Label>
            <select value={gkId} onChange={(e) => onSelectGk(e.target.value)} data-testid="gk-select"
              className="w-full h-11 rounded-lg border border-gray-300 px-3 bg-white text-sm">
              <option value="">— Selecionar —</option>
              {gks.map((g) => <option key={g.id} value={g.id}>{g.name} {g.team ? `(${g.team})` : ""}</option>)}
              <option value="__new__">➕ Criar novo guarda-redes</option>
            </select>
          </div>
          <div className="space-y-2">
            <Label>Nome do guarda-redes</Label>
            <Input value={general.goalkeeper_name} data-testid="gk-name"
              onChange={(e) => setGeneral({ ...general, goalkeeper_name: e.target.value })} placeholder="Nome" />
          </div>
          <div className="space-y-2">
            <Label>Escalão / Equipa</Label>
            <Input value={general.team} data-testid="gk-team"
              onChange={(e) => setGeneral({ ...general, team: e.target.value })} placeholder="Ex: Sub-15" />
          </div>
          <div className="space-y-2">
            <Label>Nº treino/jogo</Label>
            <Input value={general.session_number} data-testid="gen-session"
              onChange={(e) => setGeneral({ ...general, session_number: e.target.value })} placeholder="Ex: UT2 ou J4" />
          </div>
          <div className="space-y-2">
            <Label>Adversário</Label>
            <Input value={general.opponent} data-testid="gen-opponent"
              onChange={(e) => setGeneral({ ...general, opponent: e.target.value })} />
          </div>
          <div className="space-y-2">
            <Label>Data</Label>
            <Input type="date" value={general.date} data-testid="gen-date"
              onChange={(e) => setGeneral({ ...general, date: e.target.value })} />
          </div>
          <div className="space-y-2">
            <Label>Competição</Label>
            <Input value={general.competition} data-testid="gen-competition"
              onChange={(e) => setGeneral({ ...general, competition: e.target.value })} />
          </div>
          <div className="space-y-2">
            <Label>Resultado</Label>
            <Input value={general.result} data-testid="gen-result"
              onChange={(e) => setGeneral({ ...general, result: e.target.value })} placeholder="Ex: 3-2" />
          </div>
        </div>
        <div className="space-y-2">
          <Label>Notas gerais do treinador</Label>
          <Textarea value={general.coach_notes} data-testid="gen-notes"
            onChange={(e) => setGeneral({ ...general, coach_notes: e.target.value })} rows={2} />
        </div>
      </section>

      {/* Action block */}
      <section id="action-block" className="rounded-2xl border-2 border-[#0C3B1E]/20 p-5 bg-white space-y-6">
        <h2 className="font-cond text-2xl font-bold uppercase text-[#0C3B1E]">Nova ação de jogo</h2>
        <SelectGrid label="Situação" options={SITUACOES} value={action.situation} testid="sel-situacao"
          onChange={(v) => setAction({ ...action, situation: v })} cols="grid-cols-2 md:grid-cols-4" />
        <SelectGrid label="Zona" options={ZONAS} value={action.zone} testid="sel-zona"
          onChange={(v) => setAction({ ...action, zone: v })} cols="grid-cols-2 md:grid-cols-5" />
        <SelectGrid label="Distância bola-baliza" options={DISTANCIAS} value={action.distance} testid="sel-distancia"
          onChange={(v) => setAction({ ...action, distance: v })} cols="grid-cols-2 md:grid-cols-5" />
        <SelectGrid label="Tipo de finalização" options={FINALIZACOES} value={action.finish_type} testid="sel-finalizacao"
          onChange={(v) => setAction({ ...action, finish_type: v })} cols="grid-cols-2 md:grid-cols-5" />
        <SelectGrid label="Técnica utilizada" options={TECNICAS} value={action.technique} testid="sel-tecnica"
          onChange={(v) => setAction({ ...action, technique: v })} cols="grid-cols-2 md:grid-cols-4" />
        <SelectGrid label="Tomada de decisão (várias)" options={DECISOES} value={action.decisions} multi testid="sel-decisao"
          onChange={(v) => setAction({ ...action, decisions: v })} cols="grid-cols-2 md:grid-cols-3" />
        <SelectGrid label="Seguimento" options={SEGUIMENTOS} value={action.followup} testid="sel-seguimento"
          onChange={(v) => setAction({ ...action, followup: v })} cols="grid-cols-2 md:grid-cols-4" />

        {/* Evaluation */}
        <div className="space-y-2">
          <div className="text-xs font-bold uppercase tracking-[0.15em] text-[#0F3B43]">Avaliação do treinador</div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {AVALIACOES.map((av) => (
              <button type="button" key={av.key} data-testid={`sel-avaliacao-${av.key}`}
                onClick={() => setAction({ ...action, evaluation: action.evaluation === av.key ? "" : av.key })}
                className="select-tile min-h-[56px] rounded-xl border-2 font-bold uppercase text-sm flex items-center justify-center"
                style={{
                  backgroundColor: action.evaluation === av.key ? av.color : "#fff",
                  borderColor: av.color,
                  color: action.evaluation === av.key ? "#fff" : av.color,
                }}>
                {av.label}
              </button>
            ))}
          </div>
        </div>

        {needFeedback && (
          <div className="space-y-2">
            <Label className="text-red-600">Feedback breve (obrigatório para {action.evaluation})</Label>
            <Input value={action.feedback} data-testid="action-feedback"
              onChange={(e) => setAction({ ...action, feedback: e.target.value })} placeholder="O que correu mal / a melhorar" />
          </div>
        )}

        <div className="space-y-2">
          <Label>Notas / observações da ação</Label>
          <Textarea value={action.notes} rows={2} data-testid="action-notes"
            onChange={(e) => setAction({ ...action, notes: e.target.value })} />
        </div>

        <Button onClick={addAction} data-testid="add-action-btn"
          className="w-full h-14 bg-[#0F3B43] hover:bg-[#0b2d33] text-white font-bold uppercase tracking-wide text-base">
          <Plus className="mr-2" /> Adicionar ação
        </Button>
      </section>

      {/* Actions list */}
      {actions.length > 0 && (
        <section className="rounded-2xl border border-gray-200 p-5 bg-white">
          <h2 className="font-cond text-2xl font-bold uppercase text-[#0F3B43] mb-3">Ações desta sessão ({actions.length})</h2>
          <div className="space-y-2">
            {actions.map((a, i) => {
              const av = AVALIACOES.find((x) => x.key === a.evaluation);
              return (
                <div key={i} className="flex items-center gap-3 p-3 rounded-lg bg-gray-50 border border-gray-200" data-testid={`action-row-${i}`}>
                  <span className="w-6 h-6 rounded-full flex-shrink-0" style={{ backgroundColor: av?.color || "#e5e7eb" }} />
                  <div className="flex-1 text-sm">
                    <span className="font-semibold">{a.situation || "—"}</span>
                    <span className="text-muted-foreground"> · {a.zone || "—"} · {a.distance || "—"} · {a.technique || "—"}</span>
                  </div>
                  <button onClick={() => removeAction(i)} data-testid={`remove-action-${i}`} className="text-red-500 hover:text-red-700"><Trash2 size={18} /></button>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Offensive */}
      <section className="rounded-2xl border border-gray-200 p-5 bg-gray-50 space-y-4">
        <h2 className="font-cond text-2xl font-bold uppercase text-[#0F3B43]">Ações ofensivas</h2>
        <div className="grid md:grid-cols-3 gap-4">
          <Counter label="Passe" okKey="passes_ok" errKey="passes_err" off={offensive} setOff={setOffensive} color="#0C3B1E" />
          <Counter label="Remate" okKey="shots_ok" errKey="shots_err" off={offensive} setOff={setOffensive} color="#0C3B1E" />
          <Counter label="Reposição" okKey="repos_ok" errKey="repos_err" off={offensive} setOff={setOffensive} color="#0C3B1E" />
        </div>
      </section>

      <div className="sticky bottom-0 bg-white/95 backdrop-blur py-4 border-t border-gray-200">
        <Button onClick={saveReport} disabled={saving} data-testid="save-report-btn"
          className="w-full h-14 bg-[#0C3B1E] hover:bg-[#0a3018] text-white font-bold uppercase tracking-wide text-base">
          <Save className="mr-2" /> {saving ? "A guardar..." : "Guardar relatório + PDF"}
        </Button>
      </div>
    </div>
  );
}
