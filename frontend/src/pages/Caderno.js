import { useEffect, useState } from "react";
import api, { API, formatApiErrorDetail } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { COMPONENTES } from "@/lib/constants";
import { Plus, Pencil, Trash2, FileText, Dumbbell, Check } from "lucide-react";

export default function Caderno() {
  const [exercises, setExercises] = useState([]);
  const [components, setComponents] = useState([]);
  const [filter, setFilter] = useState("");
  const [selected, setSelected] = useState([]); // exercise ids for unit
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editId, setEditId] = useState(null);
  const [form, setForm] = useState({ title: "", description: "", components: [] });
  const [unit, setUnit] = useState({ title: "", date: new Date().toISOString().slice(0, 10), notes: "" });

  const loadComponents = () => api.get("/exercises/components").then((r) => setComponents(r.data)).catch(() => {});
  const load = (comp) => {
    const q = comp ? `?component=${encodeURIComponent(comp)}` : "";
    api.get(`/exercises${q}`).then((r) => setExercises(r.data)).catch(() => {});
  };
  useEffect(() => { load(""); loadComponents(); }, []);
  useEffect(() => { load(filter); }, [filter]);

  const openNew = () => { setEditId(null); setForm({ title: "", description: "", components: [] }); setDialogOpen(true); };
  const openEdit = (e) => { setEditId(e.id); setForm({ title: e.title, description: e.description || "", components: e.components || [] }); setDialogOpen(true); };

  const toggleComp = (c) => setForm((f) => ({ ...f, components: f.components.includes(c) ? f.components.filter((x) => x !== c) : [...f.components, c] }));

  const save = async () => {
    if (!form.title.trim()) { toast.error("Título obrigatório."); return; }
    try {
      if (editId) { await api.put(`/exercises/${editId}`, form); toast.success("Exercício atualizado."); }
      else { await api.post("/exercises", form); toast.success("Exercício criado."); }
      setDialogOpen(false); load(filter); loadComponents();
    } catch (err) { toast.error(formatApiErrorDetail(err.response?.data?.detail)); }
  };

  const remove = async (id) => {
    if (!window.confirm("Apagar este exercício?")) return;
    await api.delete(`/exercises/${id}`); setSelected((s) => s.filter((x) => x !== id)); load(filter); loadComponents();
    toast.success("Exercício apagado.");
  };

  const toggleSelect = (id) => setSelected((s) => s.includes(id) ? s.filter((x) => x !== id) : [...s, id]);

  const generateUnit = async () => {
    if (!unit.title.trim()) { toast.error("Dá um título à unidade de treino."); return; }
    if (selected.length === 0) { toast.error("Seleciona pelo menos um exercício."); return; }
    try {
      const { data } = await api.post("/training-units", { ...unit, exercise_ids: selected });
      toast.success("Unidade criada. A abrir PDF…");
      window.open(`${API}/training-units/${data.id}/pdf`, "_blank");
      setSelected([]);
    } catch (err) { toast.error(formatApiErrorDetail(err.response?.data?.detail)); }
  };

  return (
    <div className="space-y-5" data-testid="caderno-page">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <Dumbbell className="text-[#0C3B1E]" />
          <h1 className="font-cond text-3xl sm:text-4xl font-extrabold uppercase text-[#0C3B1E]">Caderno de Exercícios</h1>
        </div>
        <Button onClick={openNew} data-testid="new-exercise-btn" className="bg-[#0C3B1E] hover:bg-[#0a3018] text-white"><Plus size={16} className="mr-2" /> Novo exercício</Button>
      </div>

      {/* Filter chips */}
      <div className="flex flex-wrap gap-2" data-testid="filter-chips">
        <button onClick={() => setFilter("")} data-testid="filter-todas"
          className={`px-3 py-1.5 rounded-full text-sm font-semibold border-2 ${!filter ? "bg-[#0C3B1E] text-white border-[#0C3B1E]" : "bg-white text-[#0C3B1E] border-gray-200"}`}>
          Todas
        </button>
        {components.map((c) => (
          <button key={c} onClick={() => setFilter(c)} data-testid={`filter-${c.replace(/\s+/g, "-").toLowerCase()}`}
            className={`px-3 py-1.5 rounded-full text-sm font-semibold border-2 ${filter === c ? "bg-[#0F3B43] text-white border-[#0F3B43]" : "bg-white text-[#0F3B43] border-gray-200"}`}>
            {c}
          </button>
        ))}
      </div>

      {/* Exercise list */}
      <div className="grid md:grid-cols-2 gap-3">
        {exercises.length === 0 && <div className="text-sm text-muted-foreground">Sem exercícios para este filtro.</div>}
        {exercises.map((e) => {
          const sel = selected.includes(e.id);
          return (
            <div key={e.id} data-testid={`exercise-card-${e.id}`}
              className={`rounded-2xl border-2 p-4 bg-white transition-colors ${sel ? "border-[#0C3B1E]" : "border-gray-200"}`}>
              <div className="flex items-start justify-between gap-2">
                <button onClick={() => toggleSelect(e.id)} data-testid={`select-${e.id}`} className="flex items-start gap-2 text-left flex-1">
                  <span className={`mt-0.5 w-5 h-5 rounded-md border-2 flex items-center justify-center shrink-0 ${sel ? "bg-[#0C3B1E] border-[#0C3B1E] text-white" : "border-gray-300"}`}>{sel && <Check size={13} />}</span>
                  <span className="font-cond text-lg font-extrabold uppercase text-[#0C3B1E] leading-tight">{e.title}</span>
                </button>
                <div className="flex gap-1 shrink-0">
                  <button onClick={() => openEdit(e)} data-testid={`edit-exercise-${e.id}`} className="text-[#0F3B43] hover:opacity-70"><Pencil size={15} /></button>
                  <button onClick={() => remove(e.id)} data-testid={`del-exercise-${e.id}`} className="text-red-500 hover:text-red-700"><Trash2 size={15} /></button>
                </div>
              </div>
              <div className="flex flex-wrap gap-1 mt-2">
                {(e.components || []).map((c) => (
                  <span key={c} className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full bg-[#0C3B1E]/10 text-[#0C3B1E]">{c}</span>
                ))}
              </div>
              <p className="text-sm text-muted-foreground mt-2 leading-snug">{e.description}</p>
            </div>
          );
        })}
      </div>

      {/* Unit builder */}
      <section className="rounded-2xl border-2 border-[#0F3B43]/30 p-5 bg-gray-50 space-y-3" data-testid="unit-builder">
        <h2 className="font-cond text-2xl font-bold uppercase text-[#0F3B43]">Unidade de treino</h2>
        <p className="text-sm text-muted-foreground">Exercícios selecionados: <b className="text-[#0C3B1E]" data-testid="selected-count">{selected.length}</b></p>
        <div className="grid sm:grid-cols-2 gap-3">
          <div className="space-y-1"><Label className="text-xs">Título da unidade</Label>
            <Input value={unit.title} data-testid="unit-title" onChange={(e) => setUnit({ ...unit, title: e.target.value })} placeholder="Ex: UT2 Reação e potência" /></div>
          <div className="space-y-1"><Label className="text-xs">Data</Label>
            <Input type="date" value={unit.date} data-testid="unit-date" onChange={(e) => setUnit({ ...unit, date: e.target.value })} /></div>
        </div>
        <div className="space-y-1"><Label className="text-xs">Notas</Label>
          <Textarea value={unit.notes} rows={2} data-testid="unit-notes" onChange={(e) => setUnit({ ...unit, notes: e.target.value })} /></div>
        <Button onClick={generateUnit} data-testid="generate-unit-btn" className="w-full h-12 bg-[#0C3B1E] hover:bg-[#0a3018] text-white font-bold uppercase tracking-wide">
          <FileText className="mr-2" size={18} /> Gerar unidade + PDF
        </Button>
      </section>

      {/* Edit dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent data-testid="exercise-dialog">
          <DialogHeader><DialogTitle>{editId ? "Editar exercício" : "Novo exercício"}</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1"><Label>Título</Label><Input value={form.title} data-testid="ex-title" onChange={(e) => setForm({ ...form, title: e.target.value })} /></div>
            <div className="space-y-1"><Label>Descrição</Label><Textarea rows={3} value={form.description} data-testid="ex-description" onChange={(e) => setForm({ ...form, description: e.target.value })} /></div>
            <div className="space-y-1">
              <Label>Componentes</Label>
              <div className="flex flex-wrap gap-1.5">
                {COMPONENTES.map((c) => {
                  const on = form.components.includes(c);
                  return (
                    <button type="button" key={c} data-testid={`comp-${c.replace(/\s+/g, "-").toLowerCase()}`} onClick={() => toggleComp(c)}
                      className={`px-2.5 py-1 rounded-full text-xs font-semibold border-2 ${on ? "bg-[#0C3B1E] text-white border-[#0C3B1E]" : "bg-white text-[#0C3B1E] border-gray-200"}`}>{c}</button>
                  );
                })}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button onClick={save} data-testid="save-exercise-btn" className="bg-[#0C3B1E] hover:bg-[#0a3018] text-white">Guardar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
