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
import { Plus, Pencil, Trash2, Video, ExternalLink } from "lucide-react";

function embedInfo(url) {
  if (!url) return { type: "none" };
  const yt = url.match(/(?:youtube\.com\/(?:watch\?v=|embed\/|shorts\/)|youtu\.be\/)([\w-]{11})/);
  if (yt) return { type: "iframe", src: `https://www.youtube.com/embed/${yt[1]}` };
  const vm = url.match(/vimeo\.com\/(?:video\/)?(\d+)/);
  if (vm) return { type: "iframe", src: `https://player.vimeo.com/video/${vm[1]}` };
  if (/\.(mp4|webm|ogg|mov)(\?.*)?$/i.test(url)) return { type: "video", src: url };
  return { type: "link", src: url };
}

function Player({ url }) {
  const info = embedInfo(url);
  if (info.type === "iframe")
    return (
      <div className="relative w-full rounded-lg overflow-hidden bg-black" style={{ paddingTop: "56.25%" }}>
        <iframe title="video" src={info.src} className="absolute inset-0 w-full h-full" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowFullScreen />
      </div>
    );
  if (info.type === "video")
    return <video src={info.src} controls className="w-full max-h-72 rounded-lg bg-black" />;
  if (info.type === "link")
    return (
      <a href={info.src} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-sm font-semibold text-[#0F3B43] hover:underline">
        <ExternalLink size={14} /> Abrir vídeo
      </a>
    );
  return null;
}

export default function Videos() {
  const [videos, setVideos] = useState([]);
  const [filter, setFilter] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editId, setEditId] = useState(null);
  const [form, setForm] = useState({ title: "", url: "", description: "", components: [] });

  const load = (comp) => {
    const q = comp ? `?component=${encodeURIComponent(comp)}` : "";
    api.get(`/videos${q}`).then((r) => setVideos(r.data)).catch(() => {});
  };
  useEffect(() => { load(filter); }, [filter]);

  const openNew = () => { setEditId(null); setForm({ title: "", url: "", description: "", components: [] }); setDialogOpen(true); };
  const openEdit = (v) => { setEditId(v.id); setForm({ title: v.title, url: v.url, description: v.description || "", components: v.components || [] }); setDialogOpen(true); };
  const toggleComp = (c) => setForm((f) => ({ ...f, components: f.components.includes(c) ? f.components.filter((x) => x !== c) : [...f.components, c] }));

  const fetchTitle = async (url) => {
    if (!url) return;
    let endpoint = null;
    if (/youtu\.?be/.test(url)) endpoint = `https://www.youtube.com/oembed?url=${encodeURIComponent(url)}&format=json`;
    else if (/vimeo\.com/.test(url)) endpoint = `https://vimeo.com/api/oembed.json?url=${encodeURIComponent(url)}`;
    if (!endpoint) return;
    try {
      const res = await fetch(endpoint);
      if (!res.ok) return;
      const data = await res.json();
      if (data.title) setForm((f) => (f.title.trim() ? f : { ...f, title: data.title }));
    } catch { /* ignore */ }
  };

  const save = async () => {
    if (!form.title.trim()) { toast.error("Título obrigatório."); return; }
    if (!form.url.trim()) { toast.error("Link do vídeo obrigatório."); return; }
    try {
      if (editId) { await api.put(`/videos/${editId}`, form); toast.success("Vídeo atualizado."); }
      else { await api.post("/videos", form); toast.success("Vídeo adicionado."); }
      setDialogOpen(false); load(filter);
    } catch (err) { toast.error(formatApiErrorDetail(err.response?.data?.detail)); }
  };

  const remove = async (id) => {
    if (!window.confirm("Apagar este vídeo?")) return;
    try {
      await api.delete(`/videos/${id}`); load(filter);
      toast.success("Vídeo apagado.");
    } catch (err) { toast.error(formatApiErrorDetail(err.response?.data?.detail)); }
  };

  return (
    <div className="space-y-5" data-testid="videos-page">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <Video className="text-[#0C3B1E]" />
          <h1 className="font-cond text-3xl sm:text-4xl font-extrabold uppercase text-[#0C3B1E]">Vídeos de Treino</h1>
        </div>
        <Button onClick={openNew} data-testid="new-video-btn" className="bg-[#0C3B1E] hover:bg-[#0a3018] text-white"><Plus size={16} className="mr-2" /> Novo vídeo</Button>
      </div>

      <div className="flex flex-wrap gap-2" data-testid="video-filter-chips">
        <button onClick={() => setFilter("")} data-testid="vfilter-todas"
          className={`px-3 py-1.5 rounded-full text-sm font-semibold border-2 ${!filter ? "bg-[#0C3B1E] text-white border-[#0C3B1E]" : "bg-white text-[#0C3B1E] border-gray-200"}`}>
          Todas
        </button>
        {VIDEO_COMPONENTES.map((c) => (
          <button key={c} onClick={() => setFilter(c)} data-testid={`vfilter-${c.replace(/\s+/g, "-").toLowerCase()}`}
            className={`px-3 py-1.5 rounded-full text-sm font-semibold border-2 ${filter === c ? "bg-[#0F3B43] text-white border-[#0F3B43]" : "bg-white text-[#0F3B43] border-gray-200"}`}>
            {c}
          </button>
        ))}
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        {videos.length === 0 && <div className="text-sm text-muted-foreground">Sem vídeos para este filtro. Adiciona o primeiro com o botão "Novo vídeo".</div>}
        {videos.map((v) => (
          <div key={v.id} data-testid={`video-card-${v.id}`} className="rounded-2xl border-2 border-gray-200 p-4 bg-white space-y-2">
            <div className="flex items-start justify-between gap-2">
              <h3 className="font-cond text-xl font-extrabold uppercase text-[#0C3B1E] leading-tight">{v.title}</h3>
              <div className="flex gap-1 shrink-0">
                <button onClick={() => openEdit(v)} data-testid={`edit-video-${v.id}`} className="text-[#0F3B43] hover:opacity-70"><Pencil size={15} /></button>
                <button onClick={() => remove(v.id)} data-testid={`del-video-${v.id}`} className="text-red-500 hover:text-red-700"><Trash2 size={15} /></button>
              </div>
            </div>
            <Player url={v.url} />
            <div className="flex flex-wrap gap-1">
              {(v.components || []).map((c) => (
                <span key={c} className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full bg-[#0C3B1E]/10 text-[#0C3B1E]">{c}</span>
              ))}
            </div>
            {v.description && <p className="text-sm text-muted-foreground leading-snug">{v.description}</p>}
          </div>
        ))}
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent data-testid="video-dialog">
          <DialogHeader>
            <DialogTitle>{editId ? "Editar vídeo" : "Novo vídeo"}</DialogTitle>
            <DialogDescription>Cola o link do vídeo (YouTube, Vimeo ou ficheiro .mp4), escolhe as componentes e escreve uma descrição.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1"><Label>Título <span className="text-muted-foreground font-normal">(preenche sozinho a partir do link)</span></Label><Input value={form.title} data-testid="video-title" placeholder="Preenchido automaticamente pelo vídeo" onChange={(e) => setForm({ ...form, title: e.target.value })} /></div>
            <div className="space-y-1"><Label>Link do vídeo</Label><Input value={form.url} data-testid="video-url" placeholder="https://youtube.com/... ou https://.../video.mp4" onChange={(e) => setForm({ ...form, url: e.target.value })} onBlur={(e) => fetchTitle(e.target.value)} /></div>
            <div className="space-y-1"><Label>Descrição</Label><Textarea rows={3} value={form.description} data-testid="video-description" onChange={(e) => setForm({ ...form, description: e.target.value })} /></div>
            <div className="space-y-1">
              <Label>Componentes</Label>
              <div className="flex flex-wrap gap-1.5">
                {VIDEO_COMPONENTES.map((c) => {
                  const on = form.components.includes(c);
                  return (
                    <button type="button" key={c} data-testid={`vcomp-${c.replace(/\s+/g, "-").toLowerCase()}`} onClick={() => toggleComp(c)}
                      className={`px-2.5 py-1 rounded-full text-xs font-semibold border-2 ${on ? "bg-[#0C3B1E] text-white border-[#0C3B1E]" : "bg-white text-[#0C3B1E] border-gray-200"}`}>{c}</button>
                  );
                })}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button onClick={save} data-testid="save-video-btn" className="bg-[#0C3B1E] hover:bg-[#0a3018] text-white">Guardar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
