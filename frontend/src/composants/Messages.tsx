import { LoaderCircle, ServerOff, TriangleAlert } from "lucide-react";
import type { ReactNode } from "react";

export function Chargement({ texte = "Analyse en cours…" }: { texte?: string }) {
  return (
    <div role="status" className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
      <LoaderCircle className="animate-spin text-bouclier-500" aria-hidden="true" />
      <span>{texte}</span>
    </div>
  );
}

export function Squelette({ lignes = 3 }: { lignes?: number }) {
  return (
    <div aria-hidden="true" className="space-y-3 rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
      {Array.from({ length: lignes }, (_, i) => (
        <div key={i} className="h-4 animate-pulse rounded bg-slate-200 dark:bg-slate-800" style={{ width: `${90 - i * 15}%` }} />
      ))}
    </div>
  );
}

export function MessageErreur({ titre = "Une erreur est survenue", children, serveur = false }: { titre?: string; children: ReactNode; serveur?: boolean }) {
  const Icone = serveur ? ServerOff : TriangleAlert;
  return (
    <div role="alert" className="flex items-start gap-3 rounded-2xl border border-pourri-500/30 bg-pourri-50 p-4 text-pourri-900 dark:bg-pourri-900/30 dark:text-pourri-100">
      <Icone className="mt-0.5 shrink-0" aria-hidden="true" />
      <div>
        <p className="font-semibold">{titre}</p>
        <div className="text-sm">{children}</div>
      </div>
    </div>
  );
}

export function Carte({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <section className={`rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900 ${className}`}>
      {children}
    </section>
  );
}
