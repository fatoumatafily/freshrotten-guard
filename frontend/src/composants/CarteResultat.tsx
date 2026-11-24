// Carte de résultat : verdict en grand, confiance, alertes, détails repliables.
import { ChevronDown, CircleCheck, CircleX, ShieldAlert } from "lucide-react";
import type { ResultatAnalyse } from "../api/types";
import { ALERTES, CONTROLES, libelleClasse } from "../lib/libelles";
import { JaugeConfiance } from "./JaugeConfiance";
import { Probabilites } from "./Probabilites";
import { typeVerdict } from "../lib/libelles";
import { BadgeVerdict } from "./Verdict";

interface Props {
  resultat: ResultatAnalyse;
  titre?: string;
  detailsOuverts?: boolean;
}

export function CarteResultat({ resultat, titre, detailsOuverts = false }: Props) {
  const type = typeVerdict(resultat.statut, resultat.etat);
  const alertesAffichees = resultat.alertes.filter((a) => ALERTES[a]);
  const brute = Object.entries(resultat.probabilites).sort((a, b) => b[1] - a[1])[0];

  return (
    <article className="animate-apparition rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      {titre && <h3 className="mb-3 font-semibold">{titre}</h3>}
      <div className="flex flex-wrap items-center gap-3">
        <BadgeVerdict type={type} taille="lg" />
        {resultat.statut === "ok" ? (
          <p className="text-2xl font-bold">
            {resultat.classe ? libelleClasse(resultat.classe) : null}
          </p>
        ) : (
          <p className="text-xl font-semibold">Aucun fruit pris en charge détecté</p>
        )}
      </div>

      {resultat.statut === "rejet" && (
        <p className="mt-3 rounded-lg bg-slate-50 p-3 text-slate-700 dark:bg-slate-800/60 dark:text-slate-200">
          <span className="font-medium">Raison : </span>
          {resultat.raison_rejet}
        </p>
      )}

      {resultat.statut === "ok" && resultat.confiance !== null && (
        <div className="mt-4">
          <JaugeConfiance valeur={resultat.confiance} type={type} />
        </div>
      )}

      {alertesAffichees.length > 0 && (
        <ul className="mt-4 space-y-1">
          {alertesAffichees.map((a) => (
            <li
              key={a}
              className={`flex items-start gap-2 text-sm ${a === "image_possiblement_manipulee" ? "font-medium text-pourri-700 dark:text-pourri-300" : "text-slate-600 dark:text-slate-400"}`}
            >
              <ShieldAlert size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
              {ALERTES[a]}
            </li>
          ))}
        </ul>
      )}

      <details className="group mt-4" open={detailsOuverts}>
        <summary className="flex cursor-pointer list-none items-center gap-1 text-sm font-medium text-bouclier-600 hover:underline dark:text-bouclier-300">
          <ChevronDown size={16} className="transition-transform group-open:rotate-180" aria-hidden="true" />
          Détails : probabilités et contrôles de sécurité
        </summary>
        <div className="mt-3 grid gap-5 md:grid-cols-2">
          <section>
            <h4 className="mb-2 text-sm font-semibold">Probabilités (modèle {resultat.modele})</h4>
            <Probabilites probabilites={resultat.probabilites} mise_en_avant={resultat.classe} />
            {resultat.statut === "rejet" && brute && (
              <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                Sans les défenses, le modèle aurait répondu « {libelleClasse(brute[0])} » : c'est pour cela qu'un softmax
                seul ne suffit pas.
              </p>
            )}
          </section>
          <section>
            <h4 className="mb-2 text-sm font-semibold">Contrôles de sécurité</h4>
            <ul className="space-y-1.5 text-sm">
              {resultat.controles.map((c) => (
                <li key={c.nom} className="flex items-start gap-2">
                  {c.reussi ? (
                    <CircleCheck size={16} className="mt-0.5 shrink-0 text-frais-600 dark:text-frais-300" aria-label="réussi" />
                  ) : (
                    <CircleX size={16} className="mt-0.5 shrink-0 text-pourri-600 dark:text-pourri-300" aria-label="échec" />
                  )}
                  <span>
                    <span className="font-medium">{CONTROLES[c.nom] ?? c.nom}</span>
                    {c.valeur !== null && (
                      <span className="tabular-nums text-slate-500 dark:text-slate-400">
                        {" "}
                        ({c.valeur}
                        {c.seuil !== null && ` / seuil ${c.seuil}`})
                      </span>
                    )}
                    {!c.reussi && <span className="block text-slate-600 dark:text-slate-400">{c.message}</span>}
                  </span>
                </li>
              ))}
            </ul>
            <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">Analyse en {Math.round(resultat.duree_ms)} ms.</p>
          </section>
        </div>
      </details>
    </article>
  );
}
