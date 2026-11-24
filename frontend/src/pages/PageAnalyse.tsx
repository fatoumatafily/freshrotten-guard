// Onglet « Analyser une image » : upload, options, verdict, comparaison des modèles.
import { useState } from "react";
import { ErreurApi, api } from "../api/client";
import type { Purification, ResultatAnalyse, ResultatComparaison } from "../api/types";
import { CarteResultat } from "../composants/CarteResultat";
import { Carte, Chargement, MessageErreur } from "../composants/Messages";
import { BadgeVerdict } from "../composants/Verdict";
import { ZoneDepot } from "../composants/ZoneDepot";

type Resultat = { type: "simple"; r: ResultatAnalyse } | { type: "comparaison"; r: ResultatComparaison };

export function PageAnalyse() {
  const [fichier, setFichier] = useState<File | null>(null);
  const [comparer, setComparer] = useState(false);
  const [purification, setPurification] = useState<Purification | "">("");
  const [chargement, setChargement] = useState(false);
  const [resultat, setResultat] = useState<Resultat | null>(null);
  const [erreur, setErreur] = useState<ErreurApi | null>(null);

  const analyser = async () => {
    if (!fichier) return;
    setChargement(true);
    setErreur(null);
    setResultat(null);
    try {
      const p = purification || undefined;
      setResultat(
        comparer ? { type: "comparaison", r: await api.comparer(fichier, p) } : { type: "simple", r: await api.analyser(fichier, { purification: p }) },
      );
    } catch (e) {
      setErreur(e instanceof ErreurApi ? e : new ErreurApi("Erreur inattendue.", "inconnue", 0));
    } finally {
      setChargement(false);
    }
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
      <div className="space-y-4">
        <ZoneDepot
          fichier={fichier}
          onChange={(f) => {
            setFichier(f);
            setResultat(null);
            setErreur(null);
          }}
        />
        <Carte className="space-y-4">
          <label className="flex items-start gap-3">
            <input
              type="checkbox"
              checked={comparer}
              onChange={(e) => setComparer(e.target.checked)}
              className="mt-1 h-4 w-4 rounded border-slate-300 accent-bouclier-600"
            />
            <span>
              <span className="flex items-center gap-1.5 font-medium">
                Comparer les deux modèles
              </span>
              <span className="text-sm text-slate-600 dark:text-slate-400">Modèle de base (99,7 %, fragile) et robuste (96,2 %, défendu).</span>
            </span>
          </label>
          <div>
            <label htmlFor="purification" className="flex items-center gap-1.5 font-medium">
              Purification d'entrée
            </label>
            <select
              id="purification"
              value={purification}
              onChange={(e) => setPurification(e.target.value as Purification | "")}
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800"
            >
              <option value="">Aucune</option>
              <option value="jpeg">Compression JPEG légère (q = 75)</option>
              <option value="bits">Réduction de profondeur (5 bits)</option>
              <option value="median">Filtre médian 3×3</option>
            </select>
          </div>
          <button
            type="button"
            onClick={analyser}
            disabled={!fichier || chargement}
            className="w-full rounded-xl bg-frais-600 px-4 py-3 font-semibold text-white shadow-sm transition hover:bg-frais-700 disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-frais-600"
          >
            {chargement ? "Analyse…" : "Analyser l'image"}
          </button>
        </Carte>
      </div>

      <div aria-live="polite" aria-busy={chargement} className="space-y-4">
        {chargement && <Chargement />}
        {erreur && <CarteErreurFichier erreur={erreur} />}
        {resultat?.type === "simple" && <CarteResultat resultat={resultat.r} detailsOuverts />}
        {resultat?.type === "comparaison" && (
          <div className="grid gap-4 xl:grid-cols-2">
            <CarteResultat resultat={resultat.r.base} titre="Modèle de base" />
            <CarteResultat resultat={resultat.r.robuste} titre="Modèle robuste (production)" />
          </div>
        )}
        {!chargement && !resultat && !erreur && (
          <Carte className="text-slate-600 dark:text-slate-400">
            <p className="font-medium text-slate-800 dark:text-slate-200">Aucun résultat pour l'instant.</p>
            <p className="mt-1 text-sm">
              Choisissez une photo de pomme, de banane ou d'orange. Toute autre image (personne, objet, autre fruit, dessin…) est
              refusée avec une explication.
            </p>
          </Carte>
        )}
      </div>
    </div>
  );
}

function CarteErreurFichier({ erreur }: { erreur: ErreurApi }) {
  if (erreur.code === "serveur_indisponible") {
    return (
      <MessageErreur titre="Serveur indisponible" serveur>
        {erreur.message}
      </MessageErreur>
    );
  }
  if (erreur.statut === 400 || erreur.statut === 413) {
    return (
      <article className="animate-apparition rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="flex flex-wrap items-center gap-3">
          <BadgeVerdict type="rejet" taille="lg" />
          <p className="text-xl font-semibold">Fichier refusé</p>
        </div>
        <p className="mt-3 rounded-lg bg-slate-50 p-3 dark:bg-slate-800/60">
          <span className="font-medium">Raison : </span>
          {erreur.message}
        </p>
        <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">Code : {erreur.code}</p>
      </article>
    );
  }
  return <MessageErreur>{erreur.message}</MessageErreur>;
}
