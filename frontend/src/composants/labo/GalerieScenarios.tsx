// Galerie « Scénarios d'attaque » : un bouton par scénario → attendu / obtenu / ✅ ou ❌.
import { CircleCheck, CircleX, LoaderCircle, Play } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { ErreurApi, api } from "../../api/client";
import type { ResultatScenario, Scenario } from "../../api/types";
import { Carte, MessageErreur, Squelette } from "../Messages";

export function GalerieScenarios() {
  const [scenarios, setScenarios] = useState<Scenario[] | null>(null);
  const [resultats, setResultats] = useState<Record<string, ResultatScenario | "en_cours" | string>>({});
  const [erreur, setErreur] = useState<string | null>(null);
  const [toutEnCours, setToutEnCours] = useState(false);

  useEffect(() => {
    api.scenarios().then(setScenarios, (e: Error) => setErreur(e.message));
  }, []);

  const parCategorie = useMemo(() => {
    const g = new Map<string, Scenario[]>();
    for (const s of scenarios ?? []) g.set(s.categorie, [...(g.get(s.categorie) ?? []), s]);
    return [...g];
  }, [scenarios]);

  const lancer = async (id: string) => {
    setResultats((r) => ({ ...r, [id]: "en_cours" }));
    try {
      const res = await api.executerScenario(id);
      setResultats((r) => ({ ...r, [id]: res }));
    } catch (e) {
      setResultats((r) => ({ ...r, [id]: e instanceof ErreurApi ? e.message : "Erreur" }));
    }
  };

  const toutLancer = async () => {
    setToutEnCours(true);
    for (const s of scenarios ?? []) if (s.disponible) await lancer(s.id); // séquentiel : respecte la limite de débit
    setToutEnCours(false);
  };

  if (erreur) return <MessageErreur titre="Scénarios indisponibles">{erreur}</MessageErreur>;
  if (!scenarios) return <Squelette lignes={5} />;

  const termines = Object.values(resultats).filter((r): r is ResultatScenario => typeof r === "object");
  const reussis = termines.filter((r) => r.reussi).length;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={toutLancer}
          disabled={toutEnCours}
          className="inline-flex items-center gap-2 rounded-xl bg-bouclier-600 px-4 py-2.5 font-semibold text-white hover:bg-bouclier-700 disabled:opacity-60 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bouclier-600"
        >
          <Play size={16} aria-hidden="true" /> {toutEnCours ? "Exécution…" : "Tout lancer"}
        </button>
        <p aria-live="polite" className="text-sm text-slate-600 dark:text-slate-400">
          {termines.length > 0 && `${reussis} / ${termines.length} scénarios réussis`}
        </p>
      </div>
      {parCategorie.map(([categorie, liste]) => (
        <section key={categorie}>
          <h3 className="mb-2 font-semibold">{categorie}</h3>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {liste.map((s) => (
              <CarteScenario key={s.id} s={s} r={resultats[s.id]} onLancer={() => void lancer(s.id)} />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}

function CarteScenario({ s, r, onLancer }: { s: Scenario; r: ResultatScenario | "en_cours" | string | undefined; onLancer: () => void }) {
  const fini = typeof r === "object";
  return (
    <Carte className={`flex flex-col !p-4 ${fini ? (r.reussi ? "ring-1 ring-frais-500/50" : "ring-1 ring-pourri-500/50") : ""}`}>
      <div className="flex items-start justify-between gap-2">
        <h4 className="font-medium">{s.titre}</h4>
        <button
          type="button"
          onClick={onLancer}
          disabled={!s.disponible || r === "en_cours"}
          aria-label={`Lancer le scénario : ${s.titre}`}
          className="shrink-0 rounded-lg border border-slate-300 p-1.5 hover:bg-slate-50 disabled:opacity-40 dark:border-slate-700 dark:hover:bg-slate-800"
        >
          {r === "en_cours" ? <LoaderCircle size={16} className="animate-spin" aria-hidden="true" /> : <Play size={16} aria-hidden="true" />}
        </button>
      </div>
      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{s.description}</p>
      <dl className="mt-3 space-y-1 text-sm">
        <div>
          <dt className="inline font-medium">Attendu : </dt>
          <dd className="inline">{s.attendu}</dd>
        </div>
        {!s.disponible && <dd className="text-xs text-slate-500">Image de démonstration absente (scripts/generer_cas_test.py).</dd>}
        {fini && (
          <div className="flex items-start gap-1.5">
            {r.reussi ? (
              <CircleCheck size={16} className="mt-0.5 shrink-0 text-frais-600 dark:text-frais-300" aria-label="Réussi" />
            ) : (
              <CircleX size={16} className="mt-0.5 shrink-0 text-pourri-600 dark:text-pourri-300" aria-label="Échec" />
            )}
            <span>
              <dt className="inline font-medium">Obtenu : </dt>
              <dd className="inline break-words">{r.obtenu}</dd>
            </span>
          </div>
        )}
        {typeof r === "string" && r !== "en_cours" && <dd className="text-pourri-700 dark:text-pourri-300">{r}</dd>}
      </dl>
    </Carte>
  );
}
