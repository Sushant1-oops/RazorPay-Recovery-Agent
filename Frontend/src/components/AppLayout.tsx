import { useEffect, useState, type ReactNode } from "react";
import { Link, useNavigate, useRouterState } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { LayoutDashboard, CreditCard, LifeBuoy, LogOut, ShieldCheck } from "lucide-react";
import { api, clearToken, getToken } from "@/lib/api";
import { cn } from "@/lib/utils";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/payments", label: "Payments", icon: CreditCard },
  { to: "/recoveries", label: "Recoveries", icon: LifeBuoy },
] as const;

function HealthDot() {
  const { data, isError, isLoading } = useQuery({
    queryKey: ["health"],
    queryFn: () => api.health(),
    refetchInterval: 30_000,
    retry: false,
  });
  const ok = !isError && data !== undefined;
  return (
    <span className="flex items-center gap-2 text-xs text-sidebar-foreground/70">
      <span
        className={cn(
          "size-2 rounded-full",
          isLoading ? "bg-sidebar-foreground/40" : ok ? "bg-success" : "bg-danger",
        )}
      />
      {isLoading ? "Checking" : ok ? "Service online" : "Service unreachable"}
    </span>
  );
}

export function AppLayout({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string | undefined;
  children: ReactNode;
}) {
  const navigate = useNavigate();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!getToken()) {
      navigate({ to: "/login" });
      return;
    }
    setReady(true);
  }, [navigate]);

  if (!ready) {
    return <div className="min-h-screen bg-background" />;
  }

  return (
    <div className="flex min-h-screen bg-background">
      <aside className="hidden w-60 shrink-0 flex-col justify-between bg-sidebar p-5 md:flex">
        <div>
          <div className="flex items-center gap-2 text-sidebar-foreground">
            <ShieldCheck className="size-5 text-sidebar-primary" />
            <span className="font-display text-sm font-semibold tracking-tight">
              Recovery Agent
            </span>
          </div>
          <nav className="mt-8 space-y-1">
            {NAV.map((item) => {
              const active =
                item.to === "/" ? pathname === "/" : pathname.startsWith(item.to);
              return (
                <Link
                  key={item.to}
                  to={item.to}
                  className={cn(
                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                    active
                      ? "bg-sidebar-accent text-sidebar-accent-foreground"
                      : "text-sidebar-foreground/70 hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground",
                  )}
                >
                  <item.icon className="size-4" />
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>
        <div className="space-y-3 border-t border-sidebar-border pt-4">
          <HealthDot />
          <button
            onClick={() => {
              clearToken();
              navigate({ to: "/login" });
            }}
            className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-sidebar-foreground/70 transition-colors hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground"
          >
            <LogOut className="size-4" />
            Sign out
          </button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-border bg-card px-6 py-4">
          <div>
            <h1 className="text-lg font-semibold">{title}</h1>
            {subtitle ? (
              <p className="text-sm text-muted-foreground">{subtitle}</p>
            ) : null}
          </div>
          <div className="flex items-center gap-4 md:hidden">
            <nav className="flex gap-3 text-sm">
              {NAV.map((item) => (
                <Link key={item.to} to={item.to} className="text-muted-foreground">
                  {item.label}
                </Link>
              ))}
            </nav>
          </div>
        </header>
        <main className="flex-1 px-6 py-6">{children}</main>
      </div>
    </div>
  );
}

export function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="rounded-lg border border-dashed border-border bg-card px-6 py-16 text-center">
      <p className="font-display text-base font-medium">{title}</p>
      <p className="mx-auto mt-1 max-w-md text-sm text-muted-foreground">{description}</p>
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-danger/30 bg-danger-soft px-6 py-8 text-center text-sm text-danger">
      {message}
    </div>
  );
}
