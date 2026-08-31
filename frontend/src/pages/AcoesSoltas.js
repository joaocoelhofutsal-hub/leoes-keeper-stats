import { useEffect, useState } from "react";
import api, { formatApiErrorDetail } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { PanelBlock, TileGrid, Tile, slug } from "@/components/Panels";
import { CourtZone, CourtDistance, GoalTarget } from "@/components/VisualPickers";
import {
  SITUACOES, TECNICAS, DECISOES, AVALIACOES, EMPTY_ACTION, SIT_SHORT, SEG_SHORT,
} from "@/lib/constants";
import { Plus, Trash2, Zap } from "lucide-react";

const AVAL_ORDER = ["cinzenta", "vermelho", "amarelo", "verde"];

export default function AcoesSoltas() {
  const [gks, setGks] = useState([]);
  const [gkId, setGkId] = useState("");
  const [action, setAction] = useState({ ...EMPTY_ACTION });
  const [list, setList] = useState([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => { api.get("/goalkeepers").then((r) => setGks(r.data)).catch(() => {}); }, []);

  const loadList = (id) => {
    if (!id) { setList([]); return; }
    api.get(`/goalkeepers/${id}/loose-actions`).then((r) => setList(r.data)).catch(() => {});
  };
  useEffect(() => { loadList(gkId); }, [gkId]);

  const setF = (k, v) => setAction((a) => ({ ...a, [k]: v }));
  const needFeedback = action.evaluation === "amarelo" || action.evaluation === "vermelho";
  const avalLabel = AVALIACOES.find((x) => x.key === action.evaluation)?.label;

  const seg = (opt) => (
    <Tile testid={`la-seg-${slug(opt)}`} active={action.followup === opt}
      onClick={() => setF("followup", action.followup === opt ? "" : opt)}>{SEG_SHORT[opt]}</Tile>
  );

  const add = async () => {
    if (!gkId) { toast.error("Seleciona o guarda-redes."); return; }
    if (!action.situation && !action.technique) { toast.error("Preenche pelo menos a Situação ou a Técnica."); return; }
    setSaving(true);
    try {
      await api.post(`/goalkeepers/${gkId}/loose-actions`, action);
      toast.success("Ação solta guardada.");
      setAction({ ...EMPTY_ACTION });
      loadList(gkId);
    } catch (err) { toast.error(formatApiErrorDetail(err.response?.data?.detail)); }
    finally { setSaving(false); }
  };

  const remove = async (aid) => {
    if (!window.confirm("Apagar esta ação?")) return;
    try { await api.delete(`/goalkeepers/${gkId}/loose-actions/${aid}`); loadList(gkId); toast.success("Ação apagada."); }
    catch (err) { toast.error(formatApiErrorDetail(err.response?.data?.detail)); }
  };

  return (
    <div className="space-y-3 max-w-5xl mx-auto pb-16" data-testid="acoes-soltas-page">
      <div className="flex items-center gap-2">
        <Zap className="text-[#0C3B1E]" />
        <h1 className="font-cond text-2xl sm:text-3xl font-extrabold uppercase text-[#0C3B1E]">Ações Soltas</h1>
      </div>
      <p className="text-sm text-muted-foreground">Regista ações individuais de um guarda-redes sem criar um relatório. Contam para o perfil e para as métricas dos sub-jogos, sem contar como jogo.</p>

      <section className="rounded-xl border border-gray-200 p-3 bg-white">
        <Label className="text-xs">Guarda-redes</Label>
        <select value={gkId} onChange={(e) => setGkId(e.target.value)} data-testid="la-gk-select"
          className="w-full h-10 rounded-lg border border-gray-300 px-2 bg-white text-sm mt-1">
          <option value="">— Selecionar —</option>
          {gks.map((g) => <option key={g.id} value={g.id}>{g.name} {g.team ? `(${g.team})` : ""}</option>)}
        </select>
      </section>

      <div className="rounded-xl border border-gray-200 p-3 bg-white space-y-3">
        <div className="flex items-center justify-between">
          <div className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Nova ação</div>
          <Button onClick={add} disabled={saving} data-testid="la-add-btn"
            className="h-10 px-4 bg-[#0F3B43] hover:bg-[#0b2d33] text-white font-bold uppercase tracking-wide">
            <Plus className="mr-1.5" size={16} /> Adicionar ação
          </Button>
        </div>

        <div className="space-y-1">
          <Label className="text-[11px] uppercase tracking-wide text-[#0F3B43] font-bold">Notas / observações</Label>
          <Textarea value={action.notes} rows={2} data-testid="la-notes" onChange={(e) => setF("notes", e.target.value)} placeholder="Texto livre sobre a ação" />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <PanelBlock title="Situação" selected={SIT_SHORT[action.situation] || action.situation}>
            <TileGrid options={SITUACOES} value={action.situation} onChange={(v) => setF("situation", v)} testid="la-situacao" cols="grid-cols-2" labelMap={SIT_SHORT} />
          </PanelBlock>
          <PanelBlock title="Tipo de finalização" selected={action.finish_type}>
            <GoalTarget value={action.finish_type} onChange={(v) => setF("finish_type", v)} />
          </PanelBlock>
          <PanelBlock title="Zona" selected={action.zone}>
            <CourtZone value={action.zone} onChange={(v) => setF("zone", v)} />
          </PanelBlock>
          <PanelBlock title="Distância bola-baliza" selected={action.distance}>
            <CourtDistance value={action.distance} onChange={(v) => setF("distance", v)} />
          </PanelBlock>
          <PanelBlock title="Seguimento" selected={SEG_SHORT[action.followup] || action.followup}>
            <div className="space-y-1.5">
              {seg("Bola saiu pela linha final")}
              <div className="grid grid-cols-3 gap-1.5">{seg("GR recuperou")}{seg("Equipa recuperou")}{seg("Sobrou no corredor central")}</div>
              <div className="grid grid-cols-2 gap-1.5">{seg("Bola no adversário")}{seg("Golo do adversário")}</div>
              {seg("Bola saiu pela lateral")}
            </div>
          </PanelBlock>
          <PanelBlock title="Técnica utilizada" selected={action.technique}>
            <TileGrid options={TECNICAS} value={action.technique} onChange={(v) => setF("technique", v)} testid="la-tecnica" cols="grid-cols-3" />
          </PanelBlock>
          <PanelBlock title="Tomada de decisão" selected={(action.decisions || []).join(", ")}>
            <TileGrid options={DECISOES} value={action.decisions} multi onChange={(v) => setF("decisions", v)} testid="la-decisao" cols="grid-cols-1" />
          </PanelBlock>
          <PanelBlock title="Avaliação do treinador" selected={avalLabel}>
            <div className="space-y-1.5">
              {AVAL_ORDER.map((key) => {
                const av = AVALIACOES.find((x) => x.key === key);
                const sel = action.evaluation === key;
                const dark = key === "amarelo" || key === "cinzenta";
                return (
                  <button type="button" key={key} data-testid={`la-avaliacao-${key}`} onClick={() => setF("evaluation", sel ? "" : key)}
                    className="w-full min-h-[34px] rounded-lg font-bold uppercase text-[12px] transition-all"
                    style={{ background: av.color, color: dark ? "#1f2937" : "#fff", outline: sel ? "3px solid #0C3B1E" : "none", outlineOffset: "1px", opacity: action.evaluation && !sel ? 0.55 : 1 }}>
                    {av.label}
                  </button>
                );
              })}
            </div>
          </PanelBlock>
        </div>

        {needFeedback && (
          <div className="space-y-1">
            <Label className="text-red-600 text-xs">Feedback breve (para {action.evaluation})</Label>
            <Input value={action.feedback} data-testid="la-feedback" onChange={(e) => setF("feedback", e.target.value)} placeholder="O que melhorar" />
          </div>
        )}
      </div>

      <section className="rounded-xl border border-gray-200 p-3 bg-white" data-testid="la-list">
        <h2 className="font-cond text-xl font-bold uppercase text-[#0F3B43] mb-2">Ações soltas guardadas ({list.length})</h2>
        {list.length === 0 ? (
          <div className="text-sm text-muted-foreground">Ainda sem ações soltas para este guarda-redes.</div>
        ) : (
          <div className="space-y-1.5">
            {list.map((a) => {
              const av = AVALIACOES.find((x) => x.key === a.evaluation);
              return (
                <div key={a.id} data-testid={`la-row-${a.id}`} className="flex items-center gap-2 p-2 rounded-lg bg-gray-50 border border-gray-200 text-[12px]">
                  <span className="inline-block w-4 h-4 rounded shrink-0" style={{ backgroundColor: av?.color || "#e5e7eb" }} />
                  <span className="whitespace-nowrap font-semibold">{a.situation || "—"}</span>
                  <span className="text-muted-foreground">· {a.technique || "—"} · {a.distance || "s/ dist."} · {(a.decisions || []).join(", ") || "s/ decisão"}</span>
                  <button onClick={() => remove(a.id)} data-testid={`la-del-${a.id}`} className="ml-auto text-red-500 hover:text-red-700"><Trash2 size={15} /></button>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
