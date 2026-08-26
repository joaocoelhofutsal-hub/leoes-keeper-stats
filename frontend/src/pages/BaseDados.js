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
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Plus, Pencil, Trash2, FileText, ChevronLeft, Download, Upload, Camera } from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, PieChart, Pie, Legend,
} from "recharts";

function StatCard({ label, value }) {
  return (
    <div className="rounded-xl border border-gray-200 p-4 bg-white hover:-translate-y-1 transition-transform">
      <div className="text-xs uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="font-cond text-3xl font-extrabold text-[#0C3B1E] mt-1">{value}</div>
    </div>
  );
}

const EVAL_HEX = { verde: "#22C55E", amarelo: "#EAB308", vermelho: "#EF4444", cinzenta: "#9CA3AF" };
const EVAL_LABEL = { verde: "Verde", amarelo: "Amarelo", vermelho: "Vermelho", cinzenta: "Cinzenta" };

function ChartCard({ title, children }) {
  return (
    <div className="rounded-xl border border-gray-200 p-4 bg-white">
      <div className="font-cond font-bold uppercase text-[#0F3B43] mb-2">{title}</div>
      {children}
    </div>
  );
}

function ProfileCharts({ d }) {
  if (!d) return null;
  const hasAny = (arr) => arr && arr.some((x) => x.value > 0);
  const evalData = (d.evaluation || []).filter((x) => x.value > 0)
    .map((x) => ({ ...x, label: EVAL_LABEL[x.name] || x.name }));
  const barGroups = [
    { key: "technique", title: "Técnicas utilizadas" },
    { key: "followup", title: "Seguimento após defesa" },
    { key: "zone", title: "Zona do remate" },
    { key: "distance", title: "Distância bola-baliza" },
  ];
  return (
    <section className="space-y-4" data-testid="profile-charts">
      <h2 className="font-cond text-2xl font-bold uppercase text-[#0F3B43]">Gráficos</h2>
      <div className="grid md:grid-cols-2 gap-4">
        {hasAny(evalData) && (
          <ChartCard title="Avaliações">
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={evalData} dataKey="value" nameKey="label" cx="50%" cy="50%" outerRadius={80} label>
                  {evalData.map((e) => <Cell key={e.name} fill={EVAL_HEX[e.name] || "#0C3B1E"} />)}
                </Pie>
                <Legend /><Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </ChartCard>
        )}
        {barGroups.map((g) => hasAny(d[g.key]) && (
          <ChartCard key={g.key} title={g.title}>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={d[g.key]} layout="vertical" margin={{ left: 10, right: 20 }}>
                <XAxis type="number" allowDecimals={false} hide />
                <YAxis type="category" dataKey="name" width={140} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="value" fill="#0C3B1E" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
        ))}
      </div>
    </section>
  );
}

export default function BaseDados() {
  const [gks, setGks] = useState([]);
  const [selected, setSelected] = useState(null);
  const [profile, setProfile] = useState(null);
  const [reports, setReports] = useState([]);
  const [editOpen, setEditOpen] = useState(false);
  const [form, setForm] = useState({ name: "", team: "", strengths: "", weaknesses: "", source: "" });
  const [editId, setEditId] = useState(null);
  const [confirmDel, setConfirmDel] = useState(null); // {type,id}
  const [spText, setSpText] = useState(""); const [spSrc, setSpSrc] = useState("");
  const [wpText, setWpText] = useState(""); const [wpSrc, setWpSrc] = useState("");
  const [training, setTraining] = useState([]);

  const load = () => api.get("/goalkeepers").then((r) => setGks(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const openGk = async (g) => {
    setSelected(g);
    const [p, r, t] = await Promise.all([
      api.get(`/goalkeepers/${g.id}/profile`),
      api.get(`/goalkeepers/${g.id}/reports`),
      api.get(`/goalkeepers/${g.id}/training`),
    ]);
    setProfile(p.data); setReports(r.data); setTraining(t.data);
  };

  const openNew = () => { setEditId(null); setForm({ name: "", team: "" }); setEditOpen(true); };
  const openEdit = (g) => { setEditId(g.id); setForm({ name: g.name, team: g.team || "" }); setEditOpen(true); };

  const savePoints = async (sp, wp) => {
    await api.put(`/goalkeepers/${selected.id}`, { name: selected.name, team: selected.team, strong_points: sp, weak_points: wp });
    setSelected({ ...selected, strong_points: sp, weak_points: wp });
    await load();
  };
  const addPoint = async (kind) => {
    const text = kind === "strong" ? spText : wpText;
    const source = kind === "strong" ? spSrc : wpSrc;
    if (!text.trim()) { toast.error("Escreve o ponto primeiro."); return; }
    const sp = [...(selected.strong_points || [])];
    const wp = [...(selected.weak_points || [])];
    const item = { text: text.trim(), source: source.trim() };
    if (kind === "strong") sp.push(item); else wp.push(item);
    await savePoints(sp, wp);
    if (kind === "strong") { setSpText(""); setSpSrc(""); } else { setWpText(""); setWpSrc(""); }
    toast.success("Adicionado.");
  };
  const removePoint = async (kind, idx) => {
    const sp = [...(selected.strong_points || [])];
    const wp = [...(selected.weak_points || [])];
    if (kind === "strong") sp.splice(idx, 1); else wp.splice(idx, 1);
    await savePoints(sp, wp);
  };

  const saveGk = async () => {
    if (!form.name.trim()) { toast.error("Nome obrigatório."); return; }
    try {
      if (editId) { await api.put(`/goalkeepers/${editId}`, form); toast.success("Guarda-redes atualizado."); }
      else { await api.post("/goalkeepers", form); toast.success("Guarda-redes criado."); }
      setEditOpen(false); await load();
      if (selected && editId === selected.id) openGk({ ...selected, ...form });
    } catch (err) { toast.error(formatApiErrorDetail(err.response?.data?.detail)); }
  };

  const doDelete = async () => {
    const { type, id } = confirmDel;
    try {
      if (type === "gk") { await api.delete(`/goalkeepers/${id}`); setSelected(null); await load(); toast.success("Guarda-redes apagado."); }
      else { await api.delete(`/reports/${id}`); await openGk(selected); toast.success("Relatório apagado."); }
    } catch (err) { toast.error(formatApiErrorDetail(err.response?.data?.detail)); }
    setConfirmDel(null);
  };

  const exportData = async () => {
    const { data } = await api.get("/export");
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = "leoes-export.json"; a.click();
    URL.revokeObjectURL(url);
  };

  const uploadLogo = async (e) => {
    const file = e.target.files?.[0]; if (!file) return;
    const fd = new FormData(); fd.append("file", file);
    try { await api.post("/settings/logo", fd, { headers: { "Content-Type": "multipart/form-data" } }); toast.success("Logo atualizado. Recarrega para ver no topo."); }
    catch { toast.error("Falha ao enviar logo."); }
  };

  const uploadGkPhoto = async (gid, file) => {
    if (!file) return;
    const fd = new FormData(); fd.append("file", file);
    try {
      const { data } = await api.post(`/goalkeepers/${gid}/photo`, fd, { headers: { "Content-Type": "multipart/form-data" } });
      setSelected((s) => (s && s.id === gid ? { ...s, photo: data.photo } : s));
      await load();
      toast.success("Fotografia atualizada.");
    } catch { toast.error("Falha ao enviar foto."); }
  };

  const importData = async (e) => {
    const file = e.target.files?.[0]; if (!file) return;
    let json;
    try { json = JSON.parse(await file.text()); } catch { toast.error("Ficheiro JSON inválido."); return; }
    const payload = { goalkeepers: json.goalkeepers || [], reports: json.reports || [] };
    if (!payload.goalkeepers.length && !payload.reports.length) { toast.error("JSON sem 'goalkeepers'/'reports'."); return; }
    try {
      const { data } = await api.post("/import", payload);
      toast.success(`Importado: ${data.goalkeepers} GR, ${data.reports} relatórios.`);
      await load();
    } catch (err) { toast.error(formatApiErrorDetail(err.response?.data?.detail)); }
  };

  // ---- Detail view ----
  if (selected) {
    return (
      <div className="space-y-6" data-testid="gk-detail">
        <button onClick={() => { setSelected(null); setProfile(null); }} data-testid="back-btn"
          className="flex items-center gap-1 text-sm font-semibold text-[#0F3B43]"><ChevronLeft size={18} /> Voltar à lista</button>
        <div className="flex items-start justify-between flex-wrap gap-3">
          <div className="flex items-center gap-4">
            <div className="relative">
              {selected.photo
                ? <img src={selected.photo} alt={selected.name} className="w-20 h-20 rounded-2xl object-cover border border-gray-200" />
                : <div className="w-20 h-20 rounded-2xl bg-[#0C3B1E]/10 flex items-center justify-center font-cond text-3xl font-extrabold text-[#0C3B1E]">{(selected.name || "?")[0]}</div>}
              <label data-testid="gk-photo-label" className="absolute -bottom-2 -right-2 w-8 h-8 rounded-full bg-[#0F3B43] text-white flex items-center justify-center cursor-pointer shadow hover:bg-[#0b2d33]">
                <Camera size={15} />
                <input type="file" accept="image/*" className="hidden" data-testid="gk-photo-input"
                  onChange={(e) => uploadGkPhoto(selected.id, e.target.files?.[0])} />
              </label>
            </div>
            <div>
              <h1 className="font-cond text-4xl font-extrabold uppercase text-[#0C3B1E]">{selected.name}</h1>
              <div className="text-muted-foreground">{selected.team || "Sem escalão"}</div>
            </div>
          </div>
          <Button onClick={() => openEdit(selected)} variant="outline" data-testid="edit-gk-btn"><Pencil size={16} className="mr-2" /> Editar</Button>
        </div>

        {profile && (
          <>
            <h2 className="font-cond text-2xl sm:text-3xl font-extrabold uppercase text-[#0F3B43] border-b-2 border-[#0F3B43]/20 pb-1">Perfil do Guarda-Redes</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <StatCard label="Nº de relatórios" value={profile.total_reports} />
              <StatCard label="Média ações/jogo" value={profile.avg_actions_per_game} />
              <StatCard label="Média verdes/relatório" value={profile.avg_green_per_report} />
              <StatCard label="Total de ações" value={profile.total_actions} />
            </div>

            <section className="rounded-2xl border border-gray-200 p-5 bg-gray-50 space-y-3">
              <h2 className="font-cond text-2xl font-bold uppercase text-[#0F3B43]">Perfil automático</h2>
              <div className="grid md:grid-cols-3 gap-3 text-sm">
                <div><span className="font-bold">Estilo:</span> {profile.style}</div>
                <div><span className="font-bold">Técnica mais usada:</span> {profile.top_technique || "—"}</div>
                <div><span className="font-bold">Decisão mais frequente:</span> {profile.top_decision || "—"}</div>
                <div><span className="font-bold">Seguimento mais frequente:</span> {profile.top_followup || "—"}</div>
              </div>
              <div>
                <div className="font-bold text-sm mb-1">Tendências (mín. 3 ocorrências):</div>
                {profile.trends?.length ? (
                  <ul className="list-disc pl-5 space-y-1 text-sm" data-testid="trends-list">
                    {profile.trends.map((t, i) => <li key={i}>{t}</li>)}
                  </ul>
                ) : <div className="text-sm text-muted-foreground">Sem base estatística suficiente para tendências.</div>}
              </div>
            </section>

            <ProfileCharts d={profile.distributions} />

            <section className="rounded-2xl border border-gray-200 p-5 bg-white" data-testid="training-history">
              <h2 className="font-cond text-2xl font-bold uppercase text-[#0F3B43] mb-3">Treino de reação</h2>
              {training.length === 0 ? (
                <div className="text-sm text-muted-foreground">Sem sessões de treino. Vai ao separador "Treino", seleciona este guarda-redes e realiza um teste.</div>
              ) : (
                <div className="grid grid-cols-2 gap-3 max-w-md" data-testid="reaction-summary">
                  <StatCard label="Melhor resultado" value={(() => { const a = training.map((t) => t.best_ms).filter(Boolean); return a.length ? `${Math.min(...a)} ms` : "—"; })()} />
                  <StatCard label="Resultado médio" value={`${Math.round(training.reduce((s, t) => s + (t.avg_ms || 0), 0) / training.length)} ms`} />
                </div>
              )}
            </section>

            <section className="rounded-2xl border border-gray-200 p-5 bg-white space-y-4">
              <h2 className="font-cond text-2xl font-bold uppercase text-[#0F3B43]">Análise do treinador</h2>
              <div className="grid md:grid-cols-2 gap-6">
                {/* Pontos fortes */}
                <div className="space-y-3">
                  <div className="font-bold text-green-700 uppercase text-sm">Pontos fortes</div>
                  <div className="space-y-2">
                    {(selected.strong_points || []).length === 0 && <div className="text-sm text-muted-foreground">Sem pontos fortes.</div>}
                    {(selected.strong_points || []).map((p, i) => (
                      <div key={i} className="flex items-start gap-2 p-2 rounded-lg bg-green-50 border border-green-200" data-testid={`strong-item-${i}`}>
                        <div className="flex-1 text-sm"><div>{p.text}</div>{p.source && <div className="text-xs text-muted-foreground">Fonte: {p.source}</div>}</div>
                        <button onClick={() => removePoint("strong", i)} data-testid={`del-strong-${i}`} className="text-red-500 hover:text-red-700"><Trash2 size={16} /></button>
                      </div>
                    ))}
                  </div>
                  <div className="space-y-2">
                    <Input placeholder="Novo ponto forte" value={spText} data-testid="strong-text" onChange={(e) => setSpText(e.target.value)} />
                    <div className="flex gap-2">
                      <Input placeholder="Fonte (ex: jogo vs Sporting)" value={spSrc} data-testid="strong-source" onChange={(e) => setSpSrc(e.target.value)} />
                      <Button onClick={() => addPoint("strong")} data-testid="add-strong-btn" className="bg-green-700 hover:bg-green-800 text-white shrink-0"><Plus size={16} /></Button>
                    </div>
                  </div>
                </div>
                {/* Pontos fracos */}
                <div className="space-y-3">
                  <div className="font-bold text-red-600 uppercase text-sm">Pontos fracos</div>
                  <div className="space-y-2">
                    {(selected.weak_points || []).length === 0 && <div className="text-sm text-muted-foreground">Sem pontos fracos.</div>}
                    {(selected.weak_points || []).map((p, i) => (
                      <div key={i} className="flex items-start gap-2 p-2 rounded-lg bg-red-50 border border-red-200" data-testid={`weak-item-${i}`}>
                        <div className="flex-1 text-sm"><div>{p.text}</div>{p.source && <div className="text-xs text-muted-foreground">Fonte: {p.source}</div>}</div>
                        <button onClick={() => removePoint("weak", i)} data-testid={`del-weak-${i}`} className="text-red-500 hover:text-red-700"><Trash2 size={16} /></button>
                      </div>
                    ))}
                  </div>
                  <div className="space-y-2">
                    <Input placeholder="Novo ponto fraco" value={wpText} data-testid="weak-text" onChange={(e) => setWpText(e.target.value)} />
                    <div className="flex gap-2">
                      <Input placeholder="Fonte (ex: treino UT2)" value={wpSrc} data-testid="weak-source" onChange={(e) => setWpSrc(e.target.value)} />
                      <Button onClick={() => addPoint("weak")} data-testid="add-weak-btn" className="bg-red-600 hover:bg-red-700 text-white shrink-0"><Plus size={16} /></Button>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            <section className="rounded-2xl border border-gray-200 p-5 bg-white">
              <h2 className="font-cond text-2xl font-bold uppercase text-[#0F3B43] mb-3">Relatórios guardados ({reports.length})</h2>
              <div className="space-y-2">
                {reports.length === 0 && <div className="text-sm text-muted-foreground">Sem relatórios ainda.</div>}
                {reports.map((r) => (
                  <div key={r.id} className="flex items-center gap-3 p-3 rounded-lg bg-gray-50 border border-gray-200" data-testid={`report-row-${r.id}`}>
                    <div className="flex-1 text-sm">
                      <span className="font-semibold">{r.session_number || "—"}</span>
                      <span className="text-muted-foreground"> · {r.opponent || "s/ adversário"} · {r.date} · {r.actions?.length || 0} ações</span>
                    </div>
                    <button onClick={() => window.open(`${API}/reports/${r.id}/pdf`, "_blank")} data-testid={`pdf-${r.id}`}
                      className="text-[#0C3B1E] hover:opacity-70"><FileText size={18} /></button>
                    <button onClick={() => setConfirmDel({ type: "report", id: r.id })} data-testid={`del-report-${r.id}`}
                      className="text-red-500 hover:text-red-700"><Trash2 size={18} /></button>
                  </div>
                ))}
              </div>
            </section>

            <Button onClick={() => setConfirmDel({ type: "gk", id: selected.id })} variant="destructive" data-testid="delete-gk-btn">
              <Trash2 size={16} className="mr-2" /> Apagar guarda-redes
            </Button>
          </>
        )}
        {renderEditDialog()}
        {renderConfirm()}
      </div>
    );
  }

  // ---- List view ----
  function renderEditDialog() {
    return (
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent data-testid="gk-dialog">
          <DialogHeader><DialogTitle>{editId ? "Editar guarda-redes" : "Novo guarda-redes"}</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1"><Label>Nome</Label><Input value={form.name} data-testid="form-name" onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
            <div className="space-y-1"><Label>Escalão / Equipa</Label><Input value={form.team} data-testid="form-team" onChange={(e) => setForm({ ...form, team: e.target.value })} /></div>
            <p className="text-xs text-muted-foreground">Os pontos fortes e fracos são geridos no perfil do guarda-redes.</p>
          </div>
          <DialogFooter>
            <Button onClick={saveGk} data-testid="save-gk-btn" className="bg-[#0C3B1E] hover:bg-[#0a3018] text-white">Guardar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    );
  }

  function renderConfirm() {
    return (
      <AlertDialog open={!!confirmDel} onOpenChange={(o) => !o && setConfirmDel(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Confirmar eliminação</AlertDialogTitle>
            <AlertDialogDescription>Esta ação é permanente e não pode ser desfeita.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={doDelete} data-testid="confirm-delete-btn" className="bg-red-600 hover:bg-red-700">Apagar</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    );
  }

  return (
    <div className="space-y-6" data-testid="base-dados-page">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="font-cond text-4xl font-extrabold uppercase text-[#0C3B1E]">Base de Dados</h1>
        <div className="flex gap-2 flex-wrap">
          <Button variant="outline" onClick={exportData} data-testid="export-btn"><Download size={16} className="mr-2" /> Exportar</Button>
          <label className="inline-flex items-center gap-2 px-4 h-10 rounded-md border border-gray-300 text-sm font-medium cursor-pointer hover:bg-gray-50" data-testid="import-label">
            <Upload size={16} /> Importar JSON
            <input type="file" accept="application/json,.json" className="hidden" onChange={importData} data-testid="import-input" />
          </label>
          <label className="inline-flex items-center gap-2 px-4 h-10 rounded-md border border-gray-300 text-sm font-medium cursor-pointer hover:bg-gray-50" data-testid="upload-logo-label">
            <Upload size={16} /> Logo
            <input type="file" accept="image/*" className="hidden" onChange={uploadLogo} data-testid="upload-logo-input" />
          </label>
          <Button onClick={openNew} data-testid="new-gk-btn" className="bg-[#0C3B1E] hover:bg-[#0a3018] text-white"><Plus size={16} className="mr-2" /> Novo GR</Button>
        </div>
      </div>

      {gks.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-gray-300 p-12 text-center text-muted-foreground" data-testid="empty-state">
          Ainda não há guarda-redes. Cria o primeiro ou regista uma sessão na página Registo.
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {gks.map((g) => (
            <div key={g.id} onClick={() => openGk(g)} data-testid={`gk-card-${g.id}`}
              className="cursor-pointer rounded-2xl border border-gray-200 p-5 bg-white hover:-translate-y-1 hover:shadow-md transition-all">
              <div className="flex items-start justify-between">
                <div>
                  <div className="font-cond text-2xl font-extrabold uppercase text-[#0C3B1E]">{g.name}</div>
                  <div className="text-sm text-muted-foreground">{g.team || "Sem escalão"}</div>
                </div>
                <button onClick={(e) => { e.stopPropagation(); openEdit(g); }} data-testid={`edit-card-${g.id}`} className="text-[#0F3B43] hover:opacity-70"><Pencil size={16} /></button>
              </div>
              <div className="mt-4 text-sm"><span className="font-bold text-[#0C3B1E]">{g.report_count}</span> relatório(s)</div>
            </div>
          ))}
        </div>
      )}
      {renderEditDialog()}
      {renderConfirm()}
    </div>
  );
}
