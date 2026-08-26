import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Users } from "lucide-react";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend, Cell,
} from "recharts";

const A_COLOR = "#0C3B1E";
const B_COLOR = "#EAB308";
const EVAL_HEX = { verde: "#22C55E", amarelo: "#EAB308", vermelho: "#EF4444", cinzenta: "#9CA3AF" };

function mergeDist(a, b) {
  const names = [...new Set([...(a || []).map((x) => x.name), ...(b || []).map((x) => x.name)])];
  return names.map((n) => ({
    name: n,
    A: (a || []).find((x) => x.name === n)?.value || 0,
    B: (b || []).find((x) => x.name === n)?.value || 0,
  }));
}

function StatRow({ label, a, b }) {
  return (
    <div className="grid grid-cols-3 items-center py-2 border-b border-gray-100 text-sm" data-testid={`cmp-row-${label.replace(/\s+/g, "-").toLowerCase()}`}>
      <div className="font-cond text-xl font-extrabold text-[#0C3B1E] text-center">{a}</div>
      <div className="text-center text-xs uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="font-cond text-xl font-extrabold text-[#B8860B] text-center">{b}</div>
    </div>
  );
}

function CmpChart({ title, a, b, nameA, nameB, evalColors }) {
  const data = mergeDist(a, b);
  if (!data.length) return null;
  return (
    <div className="rounded-xl border border-gray-200 p-4 bg-white">
      <div className="font-cond font-bold uppercase text-[#0F3B43] mb-2">{title}</div>
      <ResponsiveContainer width="100%" height={Math.max(200, data.length * 46)}>
        <BarChart data={data} layout="vertical" margin={{ left: 10, right: 20 }} barGap={2}>
          <XAxis type="number" allowDecimals={false} hide />
          <YAxis type="category" dataKey="name" width={140} tick={{ fontSize: 11 }} />
          <Tooltip />
          <Legend />
          <Bar dataKey="A" name={nameA} fill={A_COLOR} radius={[0, 4, 4, 0]}>
            {evalColors && data.map((d) => <Cell key={`a-${d.name}`} fill={EVAL_HEX[d.name] || A_COLOR} />)}
          </Bar>
          <Bar dataKey="B" name={nameB} fill={B_COLOR} radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function GkPicker({ label, value, onChange, gks, exclude, testid }) {
  return (
    <div className="space-y-1">
      <div className="text-xs uppercase tracking-wide text-muted-foreground">{label}</div>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger data-testid={testid} className="h-12"><SelectValue placeholder="Escolher guarda-redes" /></SelectTrigger>
        <SelectContent>
          {gks.filter((g) => g.id !== exclude).map((g) => (
            <SelectItem key={g.id} value={g.id} data-testid={`${testid}-opt-${g.id}`}>{g.name}</SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

export default function Comparar() {
  const [gks, setGks] = useState([]);
  const [aId, setAId] = useState("");
  const [bId, setBId] = useState("");
  const [pA, setPA] = useState(null);
  const [pB, setPB] = useState(null);

  useEffect(() => { api.get("/goalkeepers").then((r) => setGks(r.data)).catch(() => {}); }, []);
  useEffect(() => { if (aId) api.get(`/goalkeepers/${aId}/profile`).then((r) => setPA(r.data)).catch(() => {}); else setPA(null); }, [aId]);
  useEffect(() => { if (bId) api.get(`/goalkeepers/${bId}/profile`).then((r) => setPB(r.data)).catch(() => {}); else setPB(null); }, [bId]);

  const nameA = gks.find((g) => g.id === aId)?.name || "GR A";
  const nameB = gks.find((g) => g.id === bId)?.name || "GR B";
  const ready = pA && pB;

  return (
    <div className="space-y-6" data-testid="comparar-page">
      <div className="flex items-center gap-2">
        <Users className="text-[#0C3B1E]" />
        <h1 className="font-cond text-3xl sm:text-4xl font-extrabold uppercase text-[#0C3B1E]">Comparar Guarda-Redes</h1>
      </div>

      <div className="grid sm:grid-cols-2 gap-4">
        <GkPicker label="Guarda-redes A" value={aId} onChange={setAId} gks={gks} exclude={bId} testid="cmp-select-a" />
        <GkPicker label="Guarda-redes B" value={bId} onChange={setBId} gks={gks} exclude={aId} testid="cmp-select-b" />
      </div>

      {!ready ? (
        <div className="rounded-2xl border border-dashed border-gray-300 p-12 text-center text-muted-foreground" data-testid="cmp-empty">
          Escolhe dois guarda-redes para comparar estatísticas e gráficos lado a lado.
        </div>
      ) : (
        <>
          <div className="rounded-2xl border border-gray-200 p-5 bg-white" data-testid="cmp-stats">
            <div className="grid grid-cols-3 pb-2 border-b-2 border-gray-200">
              <div className="font-cond text-2xl font-extrabold uppercase text-[#0C3B1E] text-center">{nameA}</div>
              <div />
              <div className="font-cond text-2xl font-extrabold uppercase text-[#B8860B] text-center">{nameB}</div>
            </div>
            <StatRow label="Relatórios" a={pA.total_reports} b={pB.total_reports} />
            <StatRow label="Total de ações" a={pA.total_actions} b={pB.total_actions} />
            <StatRow label="Ações/jogo" a={pA.avg_actions_per_game} b={pB.avg_actions_per_game} />
            <StatRow label="Verdes/relatório" a={pA.avg_green_per_report} b={pB.avg_green_per_report} />
            <div className="grid grid-cols-3 items-start py-3 text-sm">
              <div className="text-center text-[#0C3B1E]">{pA.style}</div>
              <div className="text-center text-xs uppercase tracking-wide text-muted-foreground">Estilo</div>
              <div className="text-center text-[#B8860B]">{pB.style}</div>
            </div>
          </div>

          <div className="grid md:grid-cols-2 gap-4">
            <CmpChart title="Avaliações" a={pA.distributions?.evaluation} b={pB.distributions?.evaluation} nameA={nameA} nameB={nameB} />
            <CmpChart title="Técnicas utilizadas" a={pA.distributions?.technique} b={pB.distributions?.technique} nameA={nameA} nameB={nameB} />
            <CmpChart title="Seguimento após defesa" a={pA.distributions?.followup} b={pB.distributions?.followup} nameA={nameA} nameB={nameB} />
            <CmpChart title="Zona do remate" a={pA.distributions?.zone} b={pB.distributions?.zone} nameA={nameA} nameB={nameB} />
            <CmpChart title="Distância bola-baliza" a={pA.distributions?.distance} b={pB.distributions?.distance} nameA={nameA} nameB={nameB} />
          </div>
        </>
      )}
    </div>
  );
}
