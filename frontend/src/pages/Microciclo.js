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
import { WEEK_DAYS, VIDEO_COMPONENTES } from "@/lib/constants";
import { CalendarDays, Plus, Pencil, Trash2, FileText, ArrowLeft, Save } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const emptyDays = () => Object.fromEntries(WEEK_DAYS.map((d) => [d, []]));

export default function Microciclo() {
  const [list, setList] = useState([]);
  const [videos, setVideos] = useState([]);
  const [current, setCurrent] = useState(null); // {id, name, days}
  const [dialog, setDialog] = useState(null); // {day, index, tr}

  const loadList = () => api.get("/microcycles").then((r) => setList(r.data)).catch(() => {});
  useEffect(() => { loadList(); api.get("/videos").then((r) => setVideos(r.data)).catch(() => {}); }, []);

  const openMc = async (id) => {
    const { data } = await api.get(`/microcycles/${id}`);
    setCurrent({ id: data.id, name: data.name || "", days: { ...emptyDays(), ...(data.days || {}) } });
  };
  const newMc = () => setCurrent({ id: null, name: "", days: emptyDays() });

  const save = async () => {
    if (!current.name.trim()) { toast.error("Dá um nome ao microciclo."); return null; }
    try {
      if (current.id) { await api.put(`/microcycles/${current.id}`, { name: current.name, days: current.days }); toast.success("Microciclo guardado."); loadList(); return current.id; }
      const { data } = await api.post("/microcycles", { name: current.name, days: current.days });
      setCurrent((c) => ({ ...c, id: data.id })); toast.success("Microciclo criado."); loadList(); return data.id;
    } catch (err) { toast.error(formatApiErrorDetail(err.response?.data?.detail)); return null; }
  };

  const removeMc = async (id) => { if (!window.confirm("Apagar este microciclo?")) return; await api.delete(`/microcycles/${id}`); loadList(); toast.success("Apagado."); };

  const genPdf = async () => { const id = await save(); if (id) window.open(`${API}/microcycles/${id}/pdf`, "_blank"); };

  // training dialog
  const openTr = (day) => setDialog({ day, index: -1, tr: { id: crypto.randomUUID(), number: "", duration: "", components: [], video_ids: [], notes: "" } });
  const editTr = (day, index, tr) => setDialog({ day, index, tr: { video_ids: [], components: [], ...tr } });
  const toggleComp = (c) => setDialog((d) => ({ ...d, tr: { ...d.tr, components: d.tr.components.includes(c) ? d.tr.components.filter((x) => x !== c) : [...d.tr.components, c] } }));
  const toggleVideo = (id) => setDialog((d) => ({ ...d, tr: { ...d.tr, video_ids: d.tr.video_ids.includes(id) ? d.tr.video_ids.filter((x) => x !== id) : [...d.tr.video_ids, id] } }));

  const saveTr = () => {
    const { day, index, tr } = dialog;
    const next = { ...current.days, [day]: [...(current.days[day] || [])] };
    if (index === -1) next[day].push(tr); else next[day][index] = tr;
    setCurrent((c) => ({ ...c, days: next }));
    setDialog(null);
  };
  const removeTr = (day, index) => setCurrent((c) => ({ ...c, days: { ...c.days, [day]: c.days[day].filter((_, i) => i !== index) } }));

  const matchVideos = dialog ? videos.filter((v) => dialog.tr.components.length === 0 || (v.components || []).some((c) => dialog.tr.components.includes(c))) : [];
  const videoTitle = (id) => videos.find((v) => v.id === id)?.title || "vídeo";

  if (!current) {
    return (
      <div className="space-y-4" data-testid="microciclo-list">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-2"><CalendarDays className="text-[#0C3B1E]" /><h1 className="font-cond text-3xl sm:text-4xl font-extrabold uppercase text-[#0C3B1E]">Microciclos</h1></div>
          <Button onClick={newMc} data-testid="new-microcycle-btn" className="bg-[#0C3B1E] hover:bg-[#0a3018] text-white"><Plus size={16} className="mr-2" /> Novo microciclo</Button>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {list.length === 0 && <div className="text-sm text-muted-foreground">Sem microciclos. Cria o primeiro.</div>}
          {list.map((m) => (
            <div key={m.id} data-testid={`mc-card-${m.id}`} className="rounded-2xl border-2 border-gray-200 p-4 bg-white flex items-center justify-between">
              <button onClick={() => openMc(m.id)} data-testid={`open-mc-${m.id}`} className="text-left font-cond text-xl font-extrabold uppercase text-[#0C3B1E]">{m.name}</button>
              <div className="flex gap-2">
                <button onClick={() => openMc(m.id)} className="text-[#0F3B43]"><Pencil size={16} /></button>
                <button onClick={() => removeMc(m.id)} data-testid={`del-mc-${m.id}`} className="text-red-500 hover:text-red-700"><Trash2 size={16} /></button>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4" data-testid="microciclo-editor">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <button onClick={() => setCurrent(null)} data-testid="mc-back" className="inline-flex items-center gap-1 text-[#0F3B43] font-semibold"><ArrowLeft size={16} /> Voltar</button>
        <div className="flex gap-2">
          <Button onClick={save} variant="outline" data-testid="mc-save-btn" className="border-[#0C3B1E] text-[#0C3B1E]"><Save size={16} className="mr-2" /> Guardar</Button>
          <Button onClick={genPdf} data-testid="mc-pdf-btn" className="bg-[#0C3B1E] hover:bg-[#0a3018] text-white"><FileText size={16} className="mr-2" /> Gerar PDF</Button>
        </div>
      </div>

      <div className="space-y-1 max-w-md">
        <Label>Nome do microciclo</Label>
        <Input value={current.name} data-testid="mc-name" onChange={(e) => setCurrent({ ...current, name: e.target.value })} placeholder="Ex.: Semana 12 · pré-jogo" />
      </div>

      <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-3">
        {WEEK_DAYS.map((day) => (
          <section key={day} data-testid={`mc-day-${day.toLowerCase()}`} className="rounded-2xl border-2 border-[#0F3B43]/25 p-3 bg-white space-y-2">
            <div className="flex items-center justify-between">
              <h2 className="font-cond text-lg font-extrabold uppercase text-[#0F3B43]">{day}</h2>
              <Button size="sm" variant="outline" onClick={() => openTr(day)} data-testid={`mc-add-${day.toLowerCase()}`} className="border-[#0C3B1E] text-[#0C3B1E] h-8"><Plus size={14} className="mr-1" /> Treino</Button>
            </div>
            {(current.days[day] || []).length === 0 ? (
              <div className="text-xs text-muted-foreground">Sem treinos.</div>
            ) : (current.days[day] || []).map((tr, i) => (
              <div key={tr.id || i} data-testid={`mc-tr-${tr.id}`} className="rounded-lg border border-gray-200 p-2.5 bg-gray-50 space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-sm flex-1">Treino Nº {tr.number || "—"} {tr.duration ? `· ${tr.duration}` : ""}</span>
                  <button onClick={() => editTr(day, i, tr)} data-testid={`mc-edit-tr-${tr.id}`} className="text-[#0F3B43]"><Pencil size={14} /></button>
                  <button onClick={() => removeTr(day, i)} data-testid={`mc-del-tr-${tr.id}`} className="text-red-500 hover:text-red-700"><Trash2 size={14} /></button>
                </div>
                {(tr.components || []).length > 0 && <div className="flex flex-wrap gap-1">{tr.components.map((c) => <span key={c} className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded-full bg-[#0C3B1E]/10 text-[#0C3B1E]">{c}</span>)}</div>}
                {(tr.video_ids || []).length > 0 && <div className="text-[11px] text-muted-foreground">{tr.video_ids.length} exercício(s): {tr.video_ids.map(videoTitle).join(", ")}</div>}
                {tr.notes && <div className="text-[11px] text-muted-foreground">Notas: {tr.notes}</div>}
              </div>
            ))}
          </section>
        ))}
      </div>

      <Dialog open={!!dialog} onOpenChange={(o) => !o && setDialog(null)}>
        <DialogContent data-testid="mc-tr-dialog">
          <DialogHeader>
            <DialogTitle>{dialog?.index === -1 ? "Novo treino específico" : "Editar treino"} · {dialog?.day}</DialogTitle>
            <DialogDescription>Define número, duração, componentes e escolhe os exercícios (vídeos) a treinar.</DialogDescription>
          </DialogHeader>
          {dialog && (
            <div className="space-y-3 max-h-[65vh] overflow-y-auto pr-1">
              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-1"><Label>Número</Label><Input value={dialog.tr.number} data-testid="mc-tr-number" onChange={(e) => setDialog({ ...dialog, tr: { ...dialog.tr, number: e.target.value } })} placeholder="Ex.: 1" /></div>
                <div className="space-y-1"><Label>Duração</Label><Input value={dialog.tr.duration} data-testid="mc-tr-duration" onChange={(e) => setDialog({ ...dialog, tr: { ...dialog.tr, duration: e.target.value } })} placeholder="Ex.: 20 min" /></div>
              </div>
              <div className="space-y-1">
                <Label>Componentes</Label>
                <div className="flex flex-wrap gap-1.5">
                  {VIDEO_COMPONENTES.map((c) => {
                    const on = dialog.tr.components.includes(c);
                    return <button type="button" key={c} data-testid={`mc-comp-${c.replace(/\s+/g, "-").toLowerCase()}`} onClick={() => toggleComp(c)} className={`px-2.5 py-1 rounded-full text-xs font-semibold border-2 ${on ? "bg-[#0C3B1E] text-white border-[#0C3B1E]" : "bg-white text-[#0C3B1E] border-gray-200"}`}>{c}</button>;
                  })}
                </div>
              </div>
              <div className="space-y-1">
                <Label>Exercícios (vídeos){dialog.tr.components.length ? " · filtrados pelas componentes" : ""}</Label>
                <div className="border border-gray-200 rounded-lg divide-y max-h-52 overflow-y-auto">
                  {matchVideos.length === 0 && <div className="p-2 text-xs text-muted-foreground">Sem vídeos para estas componentes. Adiciona vídeos no separador "Vídeos".</div>}
                  {matchVideos.map((v) => {
                    const on = dialog.tr.video_ids.includes(v.id);
                    return (
                      <button type="button" key={v.id} data-testid={`mc-video-${v.id}`} onClick={() => toggleVideo(v.id)} className={`w-full text-left px-2.5 py-2 text-sm flex items-center gap-2 ${on ? "bg-[#0C3B1E]/10" : ""}`}>
                        <span className={`w-4 h-4 rounded border ${on ? "bg-[#0C3B1E] border-[#0C3B1E]" : "border-gray-300"}`} />
                        <span className="flex-1">{v.title}</span>
                        <span className="text-[10px] text-muted-foreground">{(v.components || []).join(", ")}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
              <div className="space-y-1"><Label>Notas do treino</Label><Textarea rows={2} value={dialog.tr.notes} data-testid="mc-tr-notes" onChange={(e) => setDialog({ ...dialog, tr: { ...dialog.tr, notes: e.target.value } })} /></div>
            </div>
          )}
          <DialogFooter><Button onClick={saveTr} data-testid="mc-tr-save" className="bg-[#0C3B1E] hover:bg-[#0a3018] text-white">Guardar treino</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
