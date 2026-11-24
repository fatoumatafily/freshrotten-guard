// Rapport de la suite automatisée (make test-securite), servi par GET /api/rapport-securite.
import { useEffect, useState } from "react";
import { ErreurApi, api } from "../../api/client";
import type { RapportSecurite as Rapport } from "../../api/types";
import { Carte, Squelette } from "../Messages";

export function RapportSecurite() {
  const [rapport, setRapport] = useState<Rapport | null>(null);
  const [absent, setAbsent] = useState<string | null>(null);
  useEffect(() => {
    api.rapportSecurite().then(setRapport, (e: unknown) => setAbsent(e instanceof ErreurApi ? e.message : "Indisponible"));
  }, []);
  if (absent) return <Carte className="text-sm text-slate-600 dark:text-slate-400">{absent}</Carte>;
  if (!rapport) return <Squelette />;
  const echecs = rapport.resultats.filter((r) => !r.reussi && !r.details.limite_connue).length;
  return (
    <Carte>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="font-semibold">Rapport de la suite de sécurité</h3>
        <p className="text-sm text-slate-500 dark:text-slate-400">Généré le {rapport.date}</p>
      </div>
      <p className="mt-2 text-2xl font-bold">
        {rapport.reussis} / {rapport.total} <span className="text-base font-normal">scénarios réussis</span>
      </p>
      <p className="text-sm text-slate-600 dark:text-slate-400">
        {echecs === 0 ? "Aucun échec." : `${echecs} échec${echecs > 1 ? "s" : ""}.`}
        {(rapport.limites_connues ?? 0) > 0 && ` ${rapport.limites_connues} limite(s) connue(s) documentée(s).`}
      </p>
      <details className="mt-3">
        <summary className="cursor-pointer text-sm font-medium text-bouclier-600 hover:underline dark:text-bouclier-300">Voir le détail</summary>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left dark:border-slate-700">
                <th className="py-2 pr-3 font-medium">Scénario</th>
                <th className="py-2 pr-3 font-medium">Attendu</th>
                <th className="py-2 pr-3 font-medium">Obtenu</th>
                <th className="py-2 font-medium">Résultat</th>
              </tr>
            </thead>
            <tbody>
              {rapport.resultats.map((r) => (
                <tr key={r.id} className="border-b border-slate-100 align-top dark:border-slate-800">
                  <td className="py-2 pr-3">
                    <span className="block text-xs text-slate-500 dark:text-slate-400">{r.categorie}</span>
                    {r.menace}
                  </td>
                  <td className="py-2 pr-3">{r.attendu}</td>
                  <td className="py-2 pr-3 break-words">{r.obtenu}</td>
                  <td className="py-2 whitespace-nowrap">{r.reussi ? "✅ Réussi" : r.details.limite_connue ? "⚠️ Limite connue" : "❌ Échec"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </Carte>
  );
}
