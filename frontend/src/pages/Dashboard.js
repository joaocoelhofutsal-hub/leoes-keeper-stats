import { useEffect, useState } from "react";
import api from "@/lib/api";
import { LayoutDashboard, Trophy, Timer, Activity, Users } from "lucide-react";

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

  useEffect(() => {
    api.get("/insights/squad").then((r) => { setSquad(r.data.goalkeepers || []); setTotals(r.data.totals || {}); }).catch(() => {});
  }, []);

  const withActions = squad.filter((g) => g.total_actions > 0);
  const bestSuccess = withActions.slice().sort((a, b) => b.success_pct - a.success_pct)[0];
  const withReaction = squad.filter((g) => g.best_reaction_ms);
  const bestReaction = withReaction.slice().sort((a, b) => a.best_reaction_ms - b.best_reaction_ms)[0];
  const ranked = squad.slice().sort((a, b) => (b.total_actions > 0) - (a.total_actions > 0) || b.success_pct - a.success_pct);

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
              <span className="ml-2 font-bold" style={{ color: pctColor(bestSuccess.success_pct) }}>{bestSuccess.success_pct}%</span></div>
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

      <section className="rounded-2xl border border-gray-200 bg-white overflow-hidden" data-testid="squad-table">
        <div className="px-4 py-3 border-b border-gray-200 font-cond text-xl font-bold uppercase text-[#0F3B43]">Ranking do plantel</div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-[11px] uppercase text-muted-foreground">
              <tr>
                <th className="text-left px-4 py-2">#</th>
                <th className="text-left px-4 py-2">Guarda-redes</th>
                <th className="text-right px-4 py-2">Jogos</th>
                <th className="text-right px-4 py-2">Ações</th>
                <th className="text-right px-4 py-2">% Sucesso</th>
                <th className="text-right px-4 py-2">Melhor reação</th>
              </tr>
            </thead>
            <tbody>
              {ranked.map((g, i) => (
                <tr key={g.id} data-testid={`squad-row-${g.id}`} className="border-t border-gray-100">
                  <td className="px-4 py-2 text-muted-foreground">{i + 1}</td>
                  <td className="px-4 py-2 font-semibold text-[#0C3B1E]">{g.name} {g.team ? <span className="text-xs text-muted-foreground font-normal">({g.team})</span> : null}</td>
                  <td className="px-4 py-2 text-right">{g.games}</td>
                  <td className="px-4 py-2 text-right">{g.total_actions}</td>
                  <td className="px-4 py-2 text-right font-bold" style={{ color: g.total_actions ? pctColor(g.success_pct) : "#9CA3AF" }}>{g.total_actions ? `${g.success_pct}%` : "—"}</td>
                  <td className="px-4 py-2 text-right">{g.best_reaction_ms ? `${g.best_reaction_ms} ms` : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
