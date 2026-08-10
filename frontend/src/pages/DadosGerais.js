import { useEffect, useState } from "react";
import api from "@/lib/api";

const EVAL = { verde: "#22C55E", amarelo: "#EAB308", vermelho: "#EF4444", cinzenta: "#9CA3AF" };
const EVAL_LABEL = { verde: "Verde", amarelo: "Amarelo", vermelho: "Vermelho", cinzenta: "Cinzenta" };

function StatCard({ label, value }) {
  return (
    <div className="rounded-xl border border-gray-200 p-4 bg-white">
      <div className="text-xs uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="font-cond text-3xl font-extrabold text-[#0C3B1E] mt-1">{value}</div>
    </div>
  );
}

export default function DadosGerais() {
  const [data, setData] = useState(null);

  useEffect(() => { api.get("/insights/general").then((r) => setData(r.data)).catch(() => {}); }, []);

  if (!data) return <div className="text-[#0C3B1E] font-cond text-2xl">A carregar...</div>;

  const totalEval = data.evaluation.reduce((s, e) => s + e.value, 0) || 1;
  const off = data.offensive_totals || {};
  const passT = (off.passes_ok || 0) + (off.passes_err || 0);
  const shotT = (off.shots_ok || 0) + (off.shots_err || 0);
  const repT = (off.repos_ok || 0) + (off.repos_err || 0);

  return (
    <div className="space-y-6" data-testid="dados-gerais-page">
      <h1 className="font-cond text-3xl sm:text-4xl font-extrabold uppercase text-[#0C3B1E]">Dados Gerais</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard label="Guarda-redes" value={data.goalkeepers} />
        <StatCard label="Relatórios" value={data.reports} />
        <StatCard label="Ações registadas" value={data.total_actions} />
        <StatCard label="Ações ofensivas" value={passT + shotT + repT} />
      </div>

      {/* Evaluation distribution */}
      <section className="rounded-2xl border border-gray-200 p-5 bg-gray-50 space-y-3">
        <h2 className="font-cond text-2xl font-bold uppercase text-[#0F3B43]">Distribuição de avaliações</h2>
        <div className="flex h-6 rounded-full overflow-hidden border border-gray-200" data-testid="eval-bar">
          {data.evaluation.map((e) => e.value > 0 && (
            <div key={e.name} style={{ width: `${(e.value / totalEval) * 100}%`, background: EVAL[e.name] }}
              title={`${EVAL_LABEL[e.name]}: ${e.value}`} />
          ))}
        </div>
        <div className="flex flex-wrap gap-4 text-sm">
          {data.evaluation.map((e) => (
            <span key={e.name} className="flex items-center gap-2">
              <span className="w-3 h-3 rounded" style={{ background: EVAL[e.name] }} />
              {EVAL_LABEL[e.name]}: <b>{e.value}</b> ({Math.round((e.value / totalEval) * 100)}%)
            </span>
          ))}
        </div>
      </section>

      {/* Decisions by situation */}
      <section className="space-y-3">
        <h2 className="font-cond text-2xl font-bold uppercase text-[#0F3B43]">O que os GR decidem consoante a situação</h2>
        <p className="text-sm text-muted-foreground">Tomada de decisão mais frequente por situação de jogo (dados acumulados de todos os guarda-redes).</p>
        {data.decisions_by_situation.length === 0 && (
          <div className="rounded-xl border border-dashed border-gray-300 p-8 text-center text-muted-foreground">Ainda não há dados suficientes.</div>
        )}
        <div className="grid md:grid-cols-2 gap-4">
          {data.decisions_by_situation.map((s) => (
            <div key={s.situation} className="rounded-2xl border border-gray-200 p-4 bg-white" data-testid={`situation-card-${s.situation.replace(/\s+/g, "-").toLowerCase()}`}>
              <div className="flex items-baseline justify-between mb-3">
                <span className="font-cond text-xl font-extrabold uppercase text-[#0C3B1E]">{s.situation}</span>
                <span className="text-xs text-muted-foreground">{s.total} ações</span>
              </div>
              {s.decisions.length === 0 && <div className="text-sm text-muted-foreground">Sem decisões registadas.</div>}
              <div className="space-y-2">
                {s.decisions.map((d) => (
                  <div key={d.name}>
                    <div className="flex justify-between text-sm mb-0.5">
                      <span>{d.name}</span>
                      <span className="font-semibold text-[#0F3B43]">{d.count} · {d.pct}%</span>
                    </div>
                    <div className="h-2 rounded-full bg-gray-100 overflow-hidden">
                      <div className="h-full bg-[#0C3B1E]" style={{ width: `${d.pct}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
