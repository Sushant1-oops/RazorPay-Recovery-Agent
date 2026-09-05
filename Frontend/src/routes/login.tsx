import { useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { ShieldCheck } from "lucide-react";
import { api, setToken, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export const Route = createFileRoute("/login")({
  head: () => ({
    meta: [
      { title: "Sign in — Recovery Agent Ops" },
      {
        name: "description",
        content:
          "Sign in to the payment failure recovery console to review failed payments and agent recovery attempts.",
      },
      { property: "og:title", content: "Sign in — Recovery Agent Ops" },
      {
        property: "og:description",
        content: "Access the AI payment failure recovery console.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: LoginPage,
});

function LoginPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res =
        mode === "login"
          ? await api.login(email, password)
          : await api.register(email, password);
      if (!res?.access_token) throw new ApiError(500, "No access token returned.");
      setToken(res.access_token);
      navigate({ to: "/" });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen">
      <div className="hidden flex-1 flex-col justify-between bg-sidebar p-10 lg:flex">
        <div className="flex items-center gap-2 text-sidebar-foreground">
          <ShieldCheck className="size-5 text-sidebar-primary" />
          <span className="font-display text-sm font-semibold">Recovery Agent</span>
        </div>
        <div className="max-w-md">
          <h2 className="font-display text-3xl leading-tight text-sidebar-foreground">
            Every failed payment gets a second chance.
          </h2>
          <p className="mt-3 text-sm text-sidebar-foreground/70">
            Root-cause analysis, recoverability scoring and a full evidence trail of every
            action the agent takes.
          </p>
        </div>
        <p className="text-xs text-sidebar-foreground/50">Internal recovery operations console</p>
      </div>

      <div className="flex flex-1 items-center justify-center bg-background px-6 py-12">
        <form onSubmit={submit} className="w-full max-w-sm space-y-5">
          <div>
            <h1 className="text-2xl font-semibold">
              {mode === "login" ? "Sign in" : "Create an account"}
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Use your recovery operations credentials.
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          {error ? (
            <p className="rounded-md border border-danger/30 bg-danger-soft px-3 py-2 text-sm text-danger">
              {error}
            </p>
          ) : null}

          <Button type="submit" className="w-full" disabled={busy}>
            {busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
          </Button>

          <button
            type="button"
            className="w-full text-sm text-muted-foreground underline-offset-4 hover:underline"
            onClick={() => {
              setMode(mode === "login" ? "register" : "login");
              setError(null);
            }}
          >
            {mode === "login"
              ? "No account yet? Register"
              : "Already registered? Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
