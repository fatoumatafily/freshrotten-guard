// Onglet « Laboratoire de sécurité » : démonstration pour le jury.
import { FlaskConical, Gauge, ShieldCheck, Swords } from "lucide-react";
import { useState } from "react";
import { GalerieScenarios } from "../composants/labo/GalerieScenarios";
import { PanneauAttaque } from "../composants/labo/PanneauAttaque";
import { RapportSecurite } from "../composants/labo/RapportSecurite";
import { TableauDeBord } from "../composants/labo/TableauDeBord";
import type { Theme } from "../lib/theme";

const SECTIONS = [
  { id: "attaque", titre: "Attaque adversariale", Icone: Swords },
  { id: "metriques", titre: "Tableau de bord", Icone: Gauge },
  { id: "scenarios", titre: "Scénarios d'attaque", Icone: FlaskConical },
  { id: "rapport", titre: "Rapport", Icone: ShieldCheck },
] as const;

type IdSection = (typeof SECTIONS)[number]["id"];

export function PageLaboratoire({ theme }: { theme: Theme }) {
  const [section, setSection] = useState<IdSection>("attaque");
  return (
    <div className="space-y-6">
      <div className="rounded-2xl bg-gradient-to-br from-bouclier-600 to-bouclier-900 p-6 text-white shadow-sm">
        <h2 className="flex items-center gap-2 text-2xl font-bold">
          <ShieldCheck aria-hidden="true" /> Laboratoire de sécurité
        </h2>
        <p className="mt-1 max-w-3xl text-bouclier-100">
          Attaquez le modèle, observez le modèle de base se faire tromper et le modèle robuste résister, puis rejouez tous les
          scénarios de menace.
        </p>
      </div>
      <nav aria-label="Sections du laboratoire" className="flex flex-wrap gap-2">
        {SECTIONS.map(({ id, titre, Icone }) => (
          <button
            key={id}
            type="button"
            onClick={() => setSection(id)}
            aria-pressed={section === id}
            className={`inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bouclier-500 ${
              section === id
                ? "bg-bouclier-600 text-white"
                : "bg-white text-slate-700 ring-1 ring-slate-200 hover:bg-slate-50 dark:bg-slate-900 dark:text-slate-200 dark:ring-slate-700 dark:hover:bg-slate-800"
            }`}
          >
            <Icone size={16} aria-hidden="true" /> {titre}
          </button>
        ))}
      </nav>
      {section === "attaque" && <PanneauAttaque />}
      {section === "metriques" && <TableauDeBord theme={theme} />}
      {section === "scenarios" && <GalerieScenarios />}
      {section === "rapport" && <RapportSecurite />}
    </div>
  );
}
