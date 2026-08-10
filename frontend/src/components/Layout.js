import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { useEffect, useState } from "react";
import api from "@/lib/api";
import { ClipboardList, Database, LogOut, BarChart3 } from "lucide-react";
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
    { to: "/registo", label: "Registo", icon: ClipboardList },
    { to: "/base-dados", label: "Base de Dados", icon: Database },
    { to: "/dados-gerais", label: "Dados Gerais", icon: BarChart3 },
  ];

  const doLogout = async () => { await logout(); navigate("/login"); };

  return (
    <div className="min-h-screen bg-white">
      <header className="sticky top-0 z-50 bg-[#0C3B1E] text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            {logo && <img src={logo} alt="logo" className="h-10 w-10 rounded-md object-contain bg-white/10" />}
            <div className="leading-none">
              <div className="font-cond font-extrabold text-lg uppercase tracking-wide">Leões de Porto Salvo</div>
              <div className="text-[10px] uppercase tracking-[0.2em] text-white/60">Análise de Guarda-Redes</div>
            </div>
          </div>
          <nav className="flex items-center gap-1">
            {nav.map((n) => {
              const active = location.pathname === n.to;
              const Icon = n.icon;
              return (
                <Link key={n.to} to={n.to} data-testid={`nav-${n.label.replace(/\s+/g, "-").toLowerCase()}`}
                  className={cn("flex items-center gap-2 px-3 md:px-4 py-2 rounded-lg text-sm font-semibold transition-colors",
                    active ? "bg-white text-[#0C3B1E]" : "text-white/80 hover:bg-white/10")}>
                  <Icon size={18} /> <span className="hidden sm:inline">{n.label}</span>
                </Link>
              );
            })}
            <button onClick={doLogout} data-testid="logout-btn"
              className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-semibold text-white/80 hover:bg-white/10">
              <LogOut size={18} /> <span className="hidden sm:inline">Sair</span>
            </button>
          </nav>
        </div>
      </header>
      <main className="max-w-7xl mx-auto px-4 py-6">{children}</main>
    </div>
  );
}
