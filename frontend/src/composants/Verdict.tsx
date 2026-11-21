// Badge de verdict : couleur + icône + texte (jamais la couleur seule).
import { Ban, Leaf, TriangleAlert } from "lucide-react";

import type { TypeVerdict } from "../lib/libelles";

const STYLES: Record<TypeVerdict, { classe: string; Icone: typeof Leaf; texte: string }> = {
  frais: {
    classe: "bg-frais-50 text-frais-700 ring-frais-500/30 dark:bg-frais-900/40 dark:text-frais-300",
    Icone: Leaf,
    texte: "Frais",
  },
  pourri: {
    classe: "bg-pourri-50 text-pourri-700 ring-pourri-500/30 dark:bg-pourri-900/40 dark:text-pourri-300",
    Icone: TriangleAlert,
    texte: "Pourri",
  },
  rejet: {
    classe: "bg-slate-100 text-slate-700 ring-slate-400/40 dark:bg-slate-800 dark:text-slate-200",
    Icone: Ban,
    texte: "Rejeté",
  },
};

export function BadgeVerdict({ type, taille = "md" }: { type: TypeVerdict; taille?: "sm" | "md" | "lg" }) {
  const { classe, Icone, texte } = STYLES[type];
  const t = { sm: "text-xs px-2 py-0.5 gap-1", md: "text-sm px-3 py-1 gap-1.5", lg: "text-lg px-4 py-1.5 gap-2" }[taille];
  const i = { sm: 14, md: 16, lg: 22 }[taille];
  return (
    <span className={`inline-flex items-center rounded-full font-semibold ring-1 ring-inset ${classe} ${t}`}>
      <Icone size={i} aria-hidden="true" />
      {texte}
    </span>
  );
}
