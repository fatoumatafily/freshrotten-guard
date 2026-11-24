// Onglet « Laboratoire de sécurité » : démonstration pour le jury.
import { useState } from "react";
import { GalerieScenarios } from "../composants/labo/GalerieScenarios";
import { PanneauAttaque } from "../composants/labo/PanneauAttaque";
import { RapportSecurite } from "../composants/labo/RapportSecurite";
import { TableauDeBord } from "../composants/labo/TableauDeBord";
import type { Theme } from "../lib/theme";

const SECTIONS = [
  { id: "attaque", titre: "Attaquer une photo" },
  { id: "scenarios", titre: "Scénarios" },
  { id: "metriques", titre: "Mesures" },
  { id: "rapport", titre: "Rapport de tests" },
] as const;

type IdSection = (typeof SECTIONS)[number]["id"];

export function PageLaboratoire({ theme }: { theme: Theme }) {
  const [section, setSection] = useState<IdSection>("attaque");
  return (
    <div className="space-y-6">
      <div className="max-w-2xl">
        <h2 className="text-2xl font-bold tracking-tight">Laboratoire de sécurité</h2>
        <p className="mt-1 text-slate-600 dark:text-slate-400">
          Modifiez une photo de façon invisible pour tromper l'IA : le modèle de base se trompe, le modèle robuste tient bon.
        </p>
      </div>
      <nav aria-label="Sections du laboratoire" className="flex flex-wrap gap-x-6 border-b border-slate-200 dark:border-slate-800">
        {SECTIONS.map(({ id, titre }) => (
          <button
            key={id}
            type="button"
            onClick={() => setSection(id)}
            aria-pressed={section === id}
            className={`-mb-px border-b-2 py-2 text-sm font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bouclier-500 ${
              section === id
                ? "border-slate-900 text-slate-900 dark:border-slate-100 dark:text-slate-100"
                : "border-transparent text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100"
            }`}
          >
            {titre}
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
