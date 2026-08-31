import { useEffect, useState } from "react";
import api, { formatApiErrorDetail } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription,
} from "@/components/ui/dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  SITUACOES, TECNICAS, DECISOES, ZONAS, DISTANCIAS, SEGUIMENTOS, FINALIZACOES, AVALIACOES,
} from "@/lib/constants";
import { LayoutGrid, Plus, Pencil, Trash2, Save } from "lucide-react";

const SUBJOGOS = ["Defesa da baliza", "GR subido", "Transição defesa-ataque", "Transição ataque-defesa", "Bolas paradas"];

const METRIC_FIELDS = [
  { field: "", label: "Sem métrica (só avaliação)", options: [] },
  { field: "decisions", label: "Tomada de decisão", options: DECISOES },
  { field: "technique", label: "Técnica", options: TECNICAS },
  { field: "situation", label: "Situação", options: SITUACOES },
  { field: "zone", label: "Zona", options: ZONAS },
  { field: "distance", label: "Distância", options: DISTANCIAS },
  { field: "followup", label: "Seguimento", options: SEGUIMENTOS },
  { field: "finish_type", label: "Finalização", options: FINALIZACOES },
  { field: "offensive", label: "Ações ofensivas", options: [
    { value: "passes", label: "Passes" },
    { value: "shots", label: "Remates" },
    { value: "repos", label: "Reposições" },
  ] },
];

const EVAL_HEX = { verde: "#22C55E", amarelo: "#EAB308", vermelho: "#EF4444", cinzenta: "#9CA3AF" };
const EVAL_SCORE = { verde: 100, cinzenta: 70, amarelo: 40, vermelho: 10 };
const notaColor = (p) => (p >= 80 ? "#22C55E" : p >= 60 ? "#EAB308" : "#EF4444");
function subgameNota(topics) {
  const scores = [];
  (topics || []).forEach((t) => {
    if (t.metric_result && t.metric_result.count > 0) scores.push(t.metric_result.pct);
    else if (t.evaluation && EVAL_SCORE[t.evaluation] != null) scores.push(EVAL_SCORE[t.evaluation]);
  });
  if (!scores.length) return null;
  return Math.round(scores.reduce((a, b) => a + b, 0) / scores.length);
}
const NONE = "__none__";

export default function SubJogos() {
  const [gks, setGks] = useState([]);
  const [gkId, setGkId] = useState("");
  const [subgames, setSubgames] = useState({});
  const [dialog, setDialog] = useState(null); // {sg, topic, index}

  useEffect(() => { api.get("/goalkeepers").then((r) => setGks(r.data)).catch(() => {}); }, []);

  const load = (id) => {
    if (!id) { setSubgames({}); return; }
    api.get(`/goalkeepers/${id}/subgames`).then((r) => {
      const sg = r.data.subgames || {};
      SUBJOGOS.forEach((k) => { if (!sg[k]) sg[k] = []; });
      setSubgames(sg);
    }).catch(() => {});
  };
  useEffect(() => { load(gkId); }, [gkId]);

  const persist = async (next) => {
    setSubgames(next);
    if (!gkId) return;
    try {
      await api.put(`/goalkeepers/${gkId}/subgames`, { subgames: next });
      load(gkId); // refresh metrics
    } catch (err) { toast.error(formatApiErrorDetail(err.response?.data?.detail)); }
  };

  const openNew = (sg) => setDialog({ sg, index: -1, topic: { id: crypto.randomUUID(), name: "", evaluation: "", field: "", value: "", field2: "", value2: "", benchmark_gk_id: "", note: "" } });
  const openEdit = (sg, index, topic) => setDialog({ sg, index, topic: { field2: "", value2: "", benchmark_gk_id: "", ...topic } });

  const saveTopic = async () => {
    const { sg, index, topic } = dialog;
    if (!topic.name.trim()) { toast.error("Dá um nome ao tópico."); return; }
    const next = { ...subgames, [sg]: [...(subgames[sg] || [])] };
    const clean = { id: topic.id, name: topic.name.trim(), evaluation: topic.evaluation || "", field: topic.field || "", value: topic.value || "", field2: topic.field2 || "", value2: topic.value2 || "", benchmark_gk_id: topic.benchmark_gk_id || "", note: topic.note || "" };
    if (index === -1) next[sg].push(clean); else next[sg][index] = clean;
    setDialog(null);
    await persist(next);
    toast.success("Tópico guardado.");
  };

  const removeTopic = async (sg, index) => {
    if (!window.confirm("Apagar este tópico?")) return;
    const next = { ...subgames, [sg]: (subgames[sg] || []).filter((_, i) => i !== index) };
    await persist(next);
    toast.success("Tópico removido.");
  };

  const fieldDef = dialog ? METRIC_FIELDS.find((f) => f.field === (dialog.topic.field || "")) : null;
  const valueOptions = (fieldDef?.options || []).map((o) => (typeof o === "string" ? { value: o, label: o } : o));
  const fieldDef2 = dialog ? METRIC_FIELDS.find((f) => f.field === (dialog.topic.field2 || "")) : null;
  const valueOptions2 = (fieldDef2?.options || []).filter(() => (dialog?.topic.field2 || "") !== "offensive").map((o) => (typeof o === "string" ? { value: o, label: o } : o));

  return (
    <div className="space-y-4" data-testid="sub-jogos-page">
      <div className="flex items-center gap-2">
        <LayoutGrid className="text-[#0C3B1E]" />
        <h1 className="font-cond text-2xl sm:text-3xl font-extrabold uppercase text-[#0C3B1E]">Avaliação por Sub-jogos</h1>
      </div>

      <section className="rounded-xl border border-gray-200 p-3 bg-white max-w-md">
        <Label className="text-xs">Guarda-redes</Label>
        <select value={gkId} onChange={(e) => setGkId(e.target.value)} data-testid="sj-gk-select"
          className="w-full h-10 rounded-lg border border-gray-300 px-2 bg-white text-sm mt-1">
          <option value="">— Selecionar —</option>
          {gks.map((g) => <option key={g.id} value={g.id}>{g.name} {g.team ? `(${g.team})` : ""}</option>)}
        </select>
      </section>

      {!gkId ? (
        <div className="rounded-2xl border border-dashed border-gray-300 p-12 text-center text-muted-foreground" data-testid="sj-empty">
          Seleciona um guarda-redes para avaliar os sub-jogos.
        </div>
      ) : (
        <div className="grid md:grid-cols-2 gap-4">
          {SUBJOGOS.map((sg) => (
            <section key={sg} data-testid={`sj-card-${sg.replace(/\s+/g, "-").toLowerCase()}`} className="rounded-2xl border-2 border-[#0F3B43]/25 p-4 bg-white space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <h2 className="font-cond text-xl font-extrabold uppercase text-[#0F3B43]">{sg}</h2>
                  {(() => { const nota = subgameNota(subgames[sg]); return nota != null ? (
                    <span data-testid={`sj-nota-${sg.replace(/\s+/g, "-").toLowerCase()}`} className="px-2 py-0.5 rounded-full text-white font-bold text-xs" style={{ background: notaColor(nota) }}>Nota {nota}%</span>
                  ) : null; })()}
                </div>
                <Button size="sm" variant="outline" onClick={() => openNew(sg)} data-testid={`sj-add-${sg.replace(/\s+/g, "-").toLowerCase()}`} className="border-[#0C3B1E] text-[#0C3B1E] h-8">
                  <Plus size={14} className="mr-1" /> Tópico
                </Button>
              </div>
              {(subgames[sg] || []).length === 0 ? (
                <div className="text-sm text-muted-foreground">Sem tópicos. Adiciona um com o botão "Tópico".</div>
              ) : (
                <div className="space-y-2">
                  {(subgames[sg] || []).map((t, i) => {
                    const m = t.metric_result;
                    return (
                      <div key={t.id || i} data-testid={`sj-topic-${t.id}`} className="rounded-lg border border-gray-200 p-2.5 bg-gray-50">
                        <div className="flex items-center gap-2">
                          {t.evaluation && <span className="inline-block w-3.5 h-3.5 rounded-full shrink-0" style={{ backgroundColor: EVAL_HEX[t.evaluation] }} />}
                          <span className="font-semibold text-sm flex-1">{t.name}</span>
                          <button onClick={() => openEdit(sg, i, t)} data-testid={`sj-edit-${t.id}`} className="text-[#0F3B43] hover:opacity-70"><Pencil size={14} /></button>
                          <button onClick={() => removeTopic(sg, i)} data-testid={`sj-del-${t.id}`} className="text-red-500 hover:text-red-700"><Trash2 size={14} /></button>
                        </div>
                        {m && (
                          <div className="mt-1.5 space-y-1 text-[12px]" data-testid={`sj-metric-${t.id}`}>
                            <div className="flex items-center gap-3">
                              <span className="px-2 py-0.5 rounded-full bg-[#0C3B1E]/10 text-[#0C3B1E] font-bold">{m.count} ações</span>
                              <span className="font-bold text-green-700">{m.pct}% sucesso</span>
                              <span className="text-muted-foreground">({m.success}/{m.count})</span>
                            </div>
                            {t.benchmark && (
                              <div className="flex items-center gap-2 flex-wrap">
                                {t.benchmark.is_best ? (
                                  <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-[#22C55E] text-white font-bold uppercase text-[10px]" data-testid={`sj-autoeval-${t.id}`}>Melhor da competição</span>
                                ) : (
                                  <>
                                    {t.auto_eval && (
                                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-white font-bold uppercase text-[10px]" style={{ background: EVAL_HEX[t.auto_eval] }} data-testid={`sj-autoeval-${t.id}`}>{(m.pct - t.benchmark.best_pct) >= 0 ? `+${m.pct - t.benchmark.best_pct}` : (m.pct - t.benchmark.best_pct)} p.p.</span>
                                    )}
                                    <span className="text-muted-foreground">Referência: <b className="text-[#0C3B1E]">{t.benchmark.best_pct}%</b>{t.benchmark.best_count ? ` (${t.benchmark.best_count})` : ""}{t.benchmark.best_gk ? ` · ${t.benchmark.best_gk}` : ""}</span>
                                  </>
                                )}
                              </div>
                            )}
                          </div>
                        )}
                        {t.note && <p className="text-xs text-muted-foreground mt-1">{t.note}</p>}
                      </div>
                    );
                  })}
                </div>
              )}
            </section>
          ))}
        </div>
      )}

      <Dialog open={!!dialog} onOpenChange={(o) => !o && setDialog(null)}>
        <DialogContent data-testid="sj-dialog">
          <DialogHeader>
            <DialogTitle>{dialog?.index === -1 ? "Novo tópico" : "Editar tópico"} · {dialog?.sg}</DialogTitle>
            <DialogDescription>Dá um nome ao tópico, uma avaliação, e liga a uma métrica da base de dados (opcional) para ver quantidade e % de sucesso.</DialogDescription>
          </DialogHeader>
          {dialog && (
            <div className="space-y-3">
              <div className="space-y-1"><Label>Nome do tópico</Label>
                <Input value={dialog.topic.name} data-testid="sj-topic-name" onChange={(e) => setDialog({ ...dialog, topic: { ...dialog.topic, name: e.target.value } })} placeholder="Ex: Ocupação de espaço" /></div>

              <div className="space-y-1">
                <Label>Avaliação</Label>
                <div className="flex gap-1.5">
                  {AVALIACOES.map((av) => {
                    const sel = dialog.topic.evaluation === av.key;
                    const dark = av.key === "amarelo" || av.key === "cinzenta";
                    return (
                      <button type="button" key={av.key} data-testid={`sj-eval-${av.key}`}
                        onClick={() => setDialog({ ...dialog, topic: { ...dialog.topic, evaluation: sel ? "" : av.key } })}
                        className="flex-1 h-9 rounded-lg font-bold uppercase text-[11px]"
                        style={{ background: av.color, color: dark ? "#1f2937" : "#fff", outline: sel ? "3px solid #0C3B1E" : "none" }}>{av.label}</button>
                    );
                  })}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-1">
                  <Label>Fonte de dados</Label>
                  <Select value={dialog.topic.field || NONE} onValueChange={(v) => setDialog({ ...dialog, topic: { ...dialog.topic, field: v === NONE ? "" : v, value: "" } })}>
                    <SelectTrigger data-testid="sj-field"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {METRIC_FIELDS.map((f) => <SelectItem key={f.field || NONE} value={f.field || NONE}>{f.label}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1">
                  <Label>Valor</Label>
                  <Select value={dialog.topic.value || NONE} disabled={!dialog.topic.field}
                    onValueChange={(v) => setDialog({ ...dialog, topic: { ...dialog.topic, value: v === NONE ? "" : v } })}>
                    <SelectTrigger data-testid="sj-value"><SelectValue placeholder="Escolher" /></SelectTrigger>
                    <SelectContent>
                      {valueOptions.map((o) => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-1">
                  <Label className="text-xs">Cruzar com (opcional)</Label>
                  <Select value={dialog.topic.field2 || NONE} onValueChange={(v) => setDialog({ ...dialog, topic: { ...dialog.topic, field2: v === NONE ? "" : v, value2: "" } })}>
                    <SelectTrigger data-testid="sj-field2"><SelectValue placeholder="Sem 2º filtro" /></SelectTrigger>
                    <SelectContent>
                      {METRIC_FIELDS.filter((f) => f.field !== "offensive").map((f) => <SelectItem key={f.field || NONE} value={f.field || NONE}>{f.field ? f.label : "Sem 2º filtro"}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">Valor</Label>
                  <Select value={dialog.topic.value2 || NONE} disabled={!dialog.topic.field2}
                    onValueChange={(v) => setDialog({ ...dialog, topic: { ...dialog.topic, value2: v === NONE ? "" : v } })}>
                    <SelectTrigger data-testid="sj-value2"><SelectValue placeholder="Escolher" /></SelectTrigger>
                    <SelectContent>
                      {valueOptions2.map((o) => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-1">
                <Label className="text-xs">GR de referência (melhor da competição, opcional)</Label>
                <Select value={dialog.topic.benchmark_gk_id || NONE} onValueChange={(v) => setDialog({ ...dialog, topic: { ...dialog.topic, benchmark_gk_id: v === NONE ? "" : v } })}>
                  <SelectTrigger data-testid="sj-benchmark"><SelectValue placeholder="Sem comparação" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value={NONE}>Sem comparação</SelectItem>
                    {gks.map((g) => <SelectItem key={g.id} value={g.id}>{g.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>

              <p className="text-xs text-muted-foreground">Podes cruzar dois filtros (ex.: Situação "Remate" + Decisão "Ocupar espaço"). Sucesso = ações verdes + cinzentas. Escolhe o GR de referência para a comparação "vs melhor" (usa os dados que tiveres desse GR).</p>

              <div className="space-y-1"><Label>Nota</Label>
                <Textarea rows={2} value={dialog.topic.note} data-testid="sj-note" onChange={(e) => setDialog({ ...dialog, topic: { ...dialog.topic, note: e.target.value } })} /></div>
            </div>
          )}
          <DialogFooter>
            <Button onClick={saveTopic} data-testid="sj-save-topic" className="bg-[#0C3B1E] hover:bg-[#0a3018] text-white"><Save size={15} className="mr-2" /> Guardar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
