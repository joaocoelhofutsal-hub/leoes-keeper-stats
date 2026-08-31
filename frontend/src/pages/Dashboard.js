import { useEffect, useState } from "react";
import api from "@/lib/api";
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
import { SUBJOGOS } from "@/lib/constants";
import { LayoutDashboard, Trophy, Timer, Activity, Users, Plus, Trash2 } from "lucide-react";

const NONE = "__none__";

function Kpi({ icon: Icon, label, value, sub }) {
  return (
    <div className="rounded-2xl border border-gray-200 p-4 bg-white" data-testid={`kpi-${label.replace(/\s+/g, "-").toLowerCase()}`}>
      <div className="flex items-center gap-2 text-muted-foreground"><Icon size={16} /><span className="text-xs uppercase tracking-wide">{label}</span></div>
      <div className="font-cond text-4xl font-extrabold text-[#0C3B1E] mt-1">{value}</div>
      {sub && <div className="text-xs text-muted-foreground mt-0.5">{sub}</div>}
    </div>
  );
}

const pctColor = (p) => (p >= 80 ? "#22C55E" : p >= 60 ? "#EAB308" : "#EF4444");

export default function Dashboard() {
  const [squad, setSquad] = useState([]);
  const [totals, setTotals] = useState({ goalkeepers: 0, games: 0, total_actions: 0, success_pct: 0 });
  const [refs, setRefs] = useState([]);
  const [refOpen, setRefOpen] = useState(false);
  const [refForm, setRefForm] = useState({ subgame: SUBJOGOS[0], gk_id: "", name: "", note: "" });

  const loadRefs = () => api.get("/references").then((r) => setRefs(r.data)).catch(() => {});
  useEffect(() => {
    api.get("/insights/squad").then((r) => { setSquad(r.data.goalkeepers || []); setTotals(r.data.totals || {}); }).catch(() => {});
    loadRefs();
  }, []);

  const addRef = async () => {
    const name = (refForm.name || "").trim() || (squad.find((g) => g.id === refForm.gk_id)?.name || "");
    if (!name) { toast.error("Escolhe um guarda-redes ou escreve um nome."); return; }
    try {
      await api.post("/references", { ...refForm, name });
      setRefOpen(false); setRefForm({ subgame: SUBJOGOS[0], gk_id: "", name: "", note: "" }); loadRefs();
      toast.success("Referência adicionada.");
    } catch { toast.error("Falha ao adicionar."); }
  };
  const removeRef = async (id) => {
    if (!window.confirm("Apagar esta referência?")) return;
    try { await api.delete(`/references/${id}`); loadRefs(); } catch { toast.error("Falha ao apagar."); }
  };
  const gkById = Object.fromEntries(squad.map((g) => [g.id, g]));

  const eligible = squad.filter((g) => g.total_actions >= 3);
  const bestSuccess = (eligible.length ? eligible : squad.filter((g) => g.total_actions > 0)).slice().sort((a, b) => b.success_pct - a.success_pct)[0];
  const withReaction = squad.filter((g) => g.best_reaction_ms);
  const bestReaction = withReaction.slice().sort((a, b) => a.best_reaction_ms - b.best_reaction_ms)[0];

  return (
    <div className="space-y-5" data-testid="dashboard-page">
      <div className="flex items-center gap-2">
        <LayoutDashboard className="text-[#0C3B1E]" />
        <h1 className="font-cond text-3xl sm:text-4xl font-extrabold uppercase text-[#0C3B1E]">Dashboard do Plantel</h1>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Kpi icon={Users} label="Guarda-redes" value={totals.goalkeepers ?? 0} />
        <Kpi icon={Activity} label="Jogos" value={totals.games ?? 0} />
        <Kpi icon={Activity} label="Total de ações" value={totals.total_actions ?? 0} />
        <Kpi icon={Trophy} label="Sucesso médio" value={`${totals.success_pct ?? 0}%`} sub="verdes + cinzentas" />
      </div>

      <div className="grid sm:grid-cols-2 gap-3">
        <div className="rounded-2xl border-2 border-[#0C3B1E]/20 p-4 bg-[#0C3B1E]/5" data-testid="best-success">
          <div className="flex items-center gap-2 text-[#0C3B1E]"><Trophy size={16} /><span className="text-xs uppercase tracking-wide font-bold">Melhor % de sucesso</span></div>
          {bestSuccess ? (
            <div className="mt-1"><span className="font-cond text-3xl font-extrabold text-[#0C3B1E]">{bestSuccess.name}</span>
              <span className="ml-2 font-bold" style={{ color: pctColor(bestSuccess.success_pct) }}>{bestSuccess.success_pct}%</span>
              <span className="ml-2 text-xs text-muted-foreground">({bestSuccess.total_actions} ações)</span></div>
          ) : <div className="text-sm text-muted-foreground mt-1">Sem dados.</div>}
        </div>
        <div className="rounded-2xl border-2 border-[#0F3B43]/20 p-4 bg-[#0F3B43]/5" data-testid="best-reaction">
          <div className="flex items-center gap-2 text-[#0F3B43]"><Timer size={16} /><span className="text-xs uppercase tracking-wide font-bold">Melhor tempo de reação</span></div>
          {bestReaction ? (
            <div className="mt-1"><span className="font-cond text-3xl font-extrabold text-[#0F3B43]">{bestReaction.name}</span>
              <span className="ml-2 font-bold text-green-600">{bestReaction.best_reaction_ms} ms</span></div>
          ) : <div className="text-sm text-muted-foreground mt-1">Sem sessões de treino.</div>}
        </div>
      </div>

      <section className="rounded-2xl border border-gray-200 bg-white p-4" data-testid="references-board">
        <div className="flex items-center justify-between mb-1">
          <div className="font-cond text-xl font-bold uppercase text-[#0F3B43]">Referências por sub-jogo</div>
          <Button size="sm" onClick={() => setRefOpen(true)} data-testid="add-reference-btn" className="bg-[#0C3B1E] hover:bg-[#0a3018] text-white h-8"><Plus size={14} className="mr-1" /> Adicionar</Button>
        </div>
        <p className="text-xs text-muted-foreground mb-3">Os guarda-redes que consideras melhores em cada sub-jogo (podem não ser do teu plantel).</p>
        <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-3">
          {SUBJOGOS.map((sg) => {
            const items = refs.filter((r) => r.subgame === sg);
            return (
              <div key={sg} data-testid={`ref-col-${sg.replace(/\s+/g, "-").toLowerCase()}`} className="rounded-xl border border-gray-200 p-3">
                <div className="font-cond font-bold uppercase text-[#0C3B1E] text-sm mb-2">{sg}</div>
                {items.length === 0 ? <div className="text-xs text-muted-foreground">—</div> : (
                  <div className="space-y-2.5">
                    {items.map((r) => {
                      const g = gkById[r.gk_id];
                      const pct = g?.success_pct;
                      const hasBar = typeof pct === "number" && g?.total_actions > 0;
                      return (
                        <div key={r.id} data-testid={`ref-item-${r.id}`} className="text-sm">
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-[#0F3B43]">{r.name}</span>
                            {g && <span className="text-[11px] text-muted-foreground">{g.total_actions} ações</span>}
                            <button onClick={() => removeRef(r.id)} data-testid={`ref-del-${r.id}`} className="ml-auto text-red-500 hover:text-red-700"><Trash2 size={13} /></button>
                          </div>
                          {hasBar && (
                            <>
                              <div className="mt-1 h-2 rounded-full bg-gray-100 overflow-hidden">
                                <div className="h-full rounded-full" style={{ width: `${pct}%`, background: pctColor(pct) }} />
                              </div>
                              <div className="text-[11px] text-muted-foreground mt-0.5">{pct}% sucesso · {g.best_reaction_ms ? `${g.best_reaction_ms} ms reação` : "sem reação"}</div>
                            </>
                          )}
                          {r.note && <div className="text-xs text-muted-foreground mt-0.5">{r.note}</div>}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </section>

      <Dialog open={refOpen} onOpenChange={setRefOpen}>
        <DialogContent data-testid="reference-dialog">
          <DialogHeader>
            <DialogTitle>Adicionar referência</DialogTitle>
            <DialogDescription>Escolhe o sub-jogo e o guarda-redes que consideras melhor. Se for do teu plantel, mostramos a % de sucesso.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1"><Label>Sub-jogo</Label>
              <Select value={refForm.subgame} onValueChange={(v) => setRefForm({ ...refForm, subgame: v })}>
                <SelectTrigger data-testid="ref-subgame"><SelectValue /></SelectTrigger>
                <SelectContent>{SUBJOGOS.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="space-y-1"><Label>Guarda-redes do plantel (opcional)</Label>
              <Select value={refForm.gk_id || NONE} onValueChange={(v) => setRefForm({ ...refForm, gk_id: v === NONE ? "" : v })}>
                <SelectTrigger data-testid="ref-gk"><SelectValue placeholder="Nenhum" /></SelectTrigger>
                <SelectContent><SelectItem value={NONE}>Nenhum (escrever nome)</SelectItem>{squad.map((g) => <SelectItem key={g.id} value={g.id}>{g.name}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="space-y-1"><Label>Nome (se não for do plantel)</Label>
              <Input value={refForm.name} data-testid="ref-name" onChange={(e) => setRefForm({ ...refForm, name: e.target.value })} placeholder="Ex.: João Silva (Sporting)" /></div>
            <div className="space-y-1"><Label>Nota</Label>
              <Textarea rows={2} value={refForm.note} data-testid="ref-note" onChange={(e) => setRefForm({ ...refForm, note: e.target.value })} /></div>
          </div>
          <DialogFooter>
            <Button onClick={addRef} data-testid="ref-save-btn" className="bg-[#0C3B1E] hover:bg-[#0a3018] text-white">Guardar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
