import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { formatApiErrorDetail } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      await login(email, password);
      navigate("/registo");
    } catch (err) {
      setError(formatApiErrorDetail(err.response?.data?.detail) || err.message);
    } finally { setLoading(false); }
  };

  return (
    <div className="min-h-screen grid md:grid-cols-2">
      <div className="hidden md:block relative">
        <img src="https://customer-assets-7cd3h4nn.emergentagent.net/job_leoes-keeper-stats/artifacts/itnfxfa5_image.png"
          alt="Guarda-redes Leões de Porto Salvo" className="absolute inset-0 w-full h-full object-cover object-top" />
        <div className="absolute inset-0 bg-[#0C3B1E]/70" />
        <div className="absolute bottom-10 left-10 right-10 text-white">
          <div className="font-cond text-5xl font-extrabold uppercase leading-none">Leões de Porto Salvo</div>
          <p className="mt-3 text-white/80 max-w-md">Plataforma de análise estatística de guarda-redes de futsal.</p>
        </div>
      </div>
      <div className="flex items-center justify-center p-8 bg-white">
        <form onSubmit={submit} className="w-full max-w-sm space-y-5" data-testid="login-form">
          <div>
            <div className="font-cond text-4xl font-extrabold uppercase text-[#0C3B1E]">Entrar</div>
            <p className="text-sm text-muted-foreground mt-1">Acede à tua conta de treinador.</p>
          </div>
          <div className="space-y-2">
            <Label>Email</Label>
            <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
              data-testid="login-email" required placeholder="treinador@clube.pt" />
          </div>
          <div className="space-y-2">
            <Label>Palavra-passe</Label>
            <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
              data-testid="login-password" required placeholder="••••••••" />
          </div>
          {error && <div className="text-sm text-red-600" data-testid="login-error">{error}</div>}
          <Button type="submit" disabled={loading} data-testid="login-submit"
            className="w-full h-12 bg-[#0C3B1E] hover:bg-[#0a3018] text-white font-bold uppercase tracking-wide">
            {loading ? "A entrar..." : "Entrar"}
          </Button>
        </form>
      </div>
    </div>
  );
}
