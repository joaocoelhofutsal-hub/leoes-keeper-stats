import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { useEffect, useState } from "react";
import api from "@/lib/api";
import { ClipboardList, Database, LogOut, BarChart3, Zap, Users, Video, ListPlus, LayoutGrid, LayoutDashboard, CalendarDays } from "lucide-react";
import { cn } from "@/lib/utils";

export function Layout({ children }) {
  const { logout, user } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [logo, setLogo] = useState(null);

  useEffect(() => {
    api.get("/settings/logo").then((r) => setLogo(r.data.logo)).catch(() => {});
  }, []);

  const nav = [
    { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
    { to: "/registo", label: "Registo", icon: ClipboardList },
    { to: "/acoes", label: "Ações", icon: ListPlus },
    { to: "/base-dados", label: "Base de Dados", icon: Database },
    { to: "/comparar", label: "Comparar", icon: Users },
    { to: "/sub-jogos", label: "Sub-jogos", icon: LayoutGrid },
    { to: "/dados-gerais", label: "Dados Gerais", icon: BarChart3 },
    { to: "/treino", label: "Treino", icon: Zap },
    { to: "/videos", label: "Vídeos", icon: Video },
    { to: "/microciclo", label: "Microciclo", icon: CalendarDays },
  ];

  const doLogout = async () => { await logout(); navigate("/login"); };

  return (
    <div className="min-h-screen bg-white">
      <header className="sticky top-0 z-50 bg-[#0C3B1E] text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3 shrink-0">
            {logo && <img src={logo} alt="logo" className="h-10 w-10 rounded-md object-contain bg-white/10" />}
            <div className="leading-none">
              <div className="font-cond font-extrabold text-base lg:text-lg uppercase tracking-wide whitespace-nowrap">Leões de Porto Salvo</div>
              <div className="text-[10px] uppercase tracking-[0.2em] text-white/60 whitespace-nowrap">Análise de Guarda-Redes</div>
            </div>
          </div>
          <nav className="flex items-center gap-0.5 min-w-0 overflow-x-auto">
            {nav.map((n) => {
              const active = location.pathname === n.to;
              const Icon = n.icon;
              return (
                <Link key={n.to} to={n.to} data-testid={`nav-${n.label.replace(/\s+/g, "-").toLowerCase()}`} title={n.label}
                  className={cn("flex items-center gap-1.5 px-2 lg:px-2.5 py-2 rounded-lg text-sm font-semibold transition-colors whitespace-nowrap",
                    active ? "bg-white text-[#0C3B1E]" : "text-white/80 hover:bg-white/10")}>
                  <Icon size={18} /> <span className={active ? "inline" : "hidden"}>{n.label}</span>
                </Link>
              );
            })}
            <button onClick={doLogout} data-testid="logout-btn" title="Sair"
              className="flex items-center gap-1.5 px-2 py-2 rounded-lg text-sm font-semibold text-white/80 hover:bg-white/10 whitespace-nowrap">
              <LogOut size={18} />
            </button>
          </nav>
        </div>
      </header>
      <main className="max-w-7xl mx-auto px-4 py-6">{children}</main>
    </div>
  );
}
