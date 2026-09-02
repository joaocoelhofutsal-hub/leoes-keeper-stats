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
import { VIDEO_COMPONENTES } from "@/lib/constants";
import { LifeBuoy, Plus, Pencil, Trash2, ExternalLink } from "lucide-react";

export default function Recurso() {
  const [items, setItems] = useState([]);
  const [filter, setFilter] = useState("");
  const [open, setOpen] = useState(false);
  const [editId, setEditId] = useState(null);
  const [form, setForm] = useState({ title: "", url: "", description: "", components: [] });

  const load = (comp) => {
    const q = comp ? `?component=${encodeURIComponent(comp)}` : "";
    api.get(`/recurso-exercises${q}`).then((r) => setItems(r.data)).catch(() => {});
  };
  useEffect(() => { load(filter); }, [filter]);

  const openNew = () => { setEditId(null); setForm({ title: "", url: "", description: "", components: [] }); setOpen(true); };
  const openEdit = (x) => { setEditId(x.id); setForm({ title: x.title, url: x.url || "", description: x.description || "", components: x.components || [] }); setOpen(true); };
  const toggle = (c) => setForm((f) => ({ ...f, components: f.components.includes(c) ? f.components.filter((y) => y !== c) : [...f.components, c] }));

  const save = async () => {
    if (!form.title.trim()) { toast.error("Título obrigatório."); return; }
    try {
      if (editId) await api.put(`/recurso-exercises/${editId}`, form);
      else await api.post("/recurso-exercises", form);
      toast.success("Guardado."); setOpen(false); load(filter);
    } catch (err) { toast.error(formatApiErrorDetail(err.response?.data?.detail)); }
  };
  const remove = async (id) => {
    if (!window.confirm("Apagar este exercício de recurso?")) return;
    try { await api.delete(`/recurso-exercises/${id}`); load(filter); toast.success("Apagado."); }
    catch (err) { toast.error(formatApiErrorDetail(err.response?.data?.detail)); }
  };

  return (
    <div className="space-y-4" data-testid="recurso-page">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <LifeBuoy className="text-[#0C3B1E]" />
          <h1 className="font-cond text-3xl sm:text-4xl font-extrabold uppercase text-[#0C3B1E]">Exercícios de Recurso</h1>
        </div>
        <Button onClick={openNew} data-testid="new-recurso-btn" className="bg-[#0C3B1E] hover:bg-[#0a3018] text-white"><Plus size={16} className="mr-2" /> Novo exercício</Button>
      </div>

      <div className="flex flex-wrap gap-2">
        <button onClick={() => setFilter("")} data-testid="rfilter-todas" className={`px-3 py-1.5 rounded-full text-sm font-semibold border-2 ${!filter ? "bg-[#0C3B1E] text-white border-[#0C3B1E]" : "bg-white text-[#0C3B1E] border-gray-200"}`}>Todas</button>
        {VIDEO_COMPONENTES.map((c) => (
          <button key={c} onClick={() => setFilter(c)} className={`px-3 py-1.5 rounded-full text-sm font-semibold border-2 ${filter === c ? "bg-[#0F3B43] text-white border-[#0F3B43]" : "bg-white text-[#0F3B43] border-gray-200"}`}>{c}</button>
        ))}
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        {items.length === 0 && <div className="text-sm text-muted-foreground">Sem exercícios de recurso. Adiciona o primeiro.</div>}
        {items.map((x) => (
          <div key={x.id} data-testid={`recurso-card-${x.id}`} className="rounded-2xl border-2 border-gray-200 p-4 bg-white space-y-2">
            <div className="flex items-start justify-between gap-2">
              <h3 className="font-cond text-xl font-extrabold uppercase text-[#0C3B1E] leading-tight">{x.title}</h3>
              <div className="flex gap-1 shrink-0">
                <button onClick={() => openEdit(x)} data-testid={`edit-recurso-${x.id}`} className="text-[#0F3B43] hover:opacity-70"><Pencil size={15} /></button>
                <button onClick={() => remove(x.id)} data-testid={`del-recurso-${x.id}`} className="text-red-500 hover:text-red-700"><Trash2 size={15} /></button>
              </div>
            </div>
            <div className="flex flex-wrap gap-1">
              {(x.components || []).map((c) => <span key={c} className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full bg-[#0C3B1E]/10 text-[#0C3B1E]">{c}</span>)}
            </div>
            {x.description && <p className="text-sm text-muted-foreground leading-snug">{x.description}</p>}
            {x.url && <a href={x.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-sm font-semibold text-[#0F3B43] hover:underline"><ExternalLink size={14} /> Abrir vídeo/recurso</a>}
          </div>
        ))}
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent data-testid="recurso-dialog">
          <DialogHeader>
            <DialogTitle>{editId ? "Editar exercício" : "Novo exercício de recurso"}</DialogTitle>
            <DialogDescription>Exercícios alternativos/de recurso. Link opcional, descrição e componentes.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1"><Label>Título</Label><Input value={form.title} data-testid="recurso-title" onChange={(e) => setForm({ ...form, title: e.target.value })} /></div>
            <div className="space-y-1"><Label>Link (opcional)</Label><Input value={form.url} data-testid="recurso-url" onChange={(e) => setForm({ ...form, url: e.target.value })} placeholder="https://..." /></div>
            <div className="space-y-1"><Label>Descrição</Label><Textarea rows={3} value={form.description} data-testid="recurso-description" onChange={(e) => setForm({ ...form, description: e.target.value })} /></div>
            <div className="space-y-1">
              <Label>Componentes</Label>
              <div className="flex flex-wrap gap-1.5">
                {VIDEO_COMPONENTES.map((c) => {
                  const on = form.components.includes(c);
                  return <button type="button" key={c} onClick={() => toggle(c)} className={`px-2.5 py-1 rounded-full text-xs font-semibold border-2 ${on ? "bg-[#0C3B1E] text-white border-[#0C3B1E]" : "bg-white text-[#0C3B1E] border-gray-200"}`}>{c}</button>;
                })}
              </div>
            </div>
          </div>
          <DialogFooter><Button onClick={save} data-testid="save-recurso-btn" className="bg-[#0C3B1E] hover:bg-[#0a3018] text-white">Guardar</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
