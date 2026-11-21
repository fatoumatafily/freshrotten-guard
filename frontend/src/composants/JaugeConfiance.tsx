import { pourcent } from "../lib/libelles";
import type { TypeVerdict } from "../lib/libelles";

const COULEURS: Record<TypeVerdict, string> = {
  frais: "bg-frais-500",
  pourri: "bg-pourri-500",
  rejet: "bg-slate-400",
};

export function JaugeConfiance({ valeur, type, libelle = "Confiance" }: { valeur: number; type: TypeVerdict; libelle?: string }) {
  const v = Math.max(0, Math.min(1, valeur));
  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between text-sm">
        <span className="text-slate-600 dark:text-slate-300">{libelle}</span>
        <span className="font-semibold tabular-nums">{pourcent(v)}</span>
      </div>
      <div
        role="meter"
        aria-label={libelle}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(v * 100)}
        className="h-2.5 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700"
      >
        <div className={`h-full rounded-full transition-[width] duration-500 ease-out ${COULEURS[type]}`} style={{ width: `${v * 100}%` }} />
      </div>
    </div>
  );
}
