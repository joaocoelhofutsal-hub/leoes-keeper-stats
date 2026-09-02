import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { Layout } from "@/components/Layout";
import { Toaster } from "@/components/ui/sonner";
import Login from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";
import Registo from "@/pages/Registo";
import BaseDados from "@/pages/BaseDados";
import DadosGerais from "@/pages/DadosGerais";
import Treino from "@/pages/Treino";
import Comparar from "@/pages/Comparar";
import Videos from "@/pages/Videos";
import AcoesSoltas from "@/pages/AcoesSoltas";
import SubJogos from "@/pages/SubJogos";
import Microciclo from "@/pages/Microciclo";

function Protected({ children }) {
  const { user, ready } = useAuth();
  if (!ready) return <div className="min-h-screen flex items-center justify-center text-[#0C3B1E] font-cond text-2xl">A carregar...</div>;
  if (!user) return <Navigate to="/login" replace />;
  return <Layout>{children}</Layout>;
}

function PublicOnly({ children }) {
  const { user, ready } = useAuth();
  if (!ready) return <div className="min-h-screen" />;
  if (user) return <Navigate to="/dashboard" replace />;
  return children;
}

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<PublicOnly><Login /></PublicOnly>} />
            <Route path="/dashboard" element={<Protected><Dashboard /></Protected>} />
            <Route path="/registo" element={<Protected><Registo /></Protected>} />
            <Route path="/base-dados" element={<Protected><BaseDados /></Protected>} />
            <Route path="/dados-gerais" element={<Protected><DadosGerais /></Protected>} />
            <Route path="/treino" element={<Protected><Treino /></Protected>} />
            <Route path="/comparar" element={<Protected><Comparar /></Protected>} />
            <Route path="/videos" element={<Protected><Videos /></Protected>} />
            <Route path="/acoes" element={<Protected><AcoesSoltas /></Protected>} />
            <Route path="/sub-jogos" element={<Protected><SubJogos /></Protected>} />
            <Route path="/microciclo" element={<Protected><Microciclo /></Protected>} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
          <Toaster position="bottom-right" richColors />
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;
