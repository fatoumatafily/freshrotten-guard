// Génération d'une attaque adversariale et comparaison visuelle base / robuste.
import { Download, Swords } from "lucide-react";
import { useState } from "react";
import { ErreurApi, api } from "../../api/client";
import type { ModeAttaque, NomClasse, NomModele, PredictionAttaque, ResultatAttaque, TypeAttaque } from "../../api/types";
import { CLASSES, libelleClasse, pourcent } from "../../lib/libelles";
import { Carte, Chargement, MessageErreur } from "../Messages";
import { ZoneDepot } from "../ZoneDepot";

export function PanneauAttaque() {
  const [fichier, setFichier] = useState<File | null>(null);
  const [attaque, setAttaque] = useState<TypeAttaque>("pgd");
  const [epsilon, setEpsilon] = useState(0.03);
  const [cible, setCible] = useState<NomClasse>("banana_fresh");
  const [mode, setMode] = useState<ModeAttaque>("boite_blanche");
  const [chargement, setChargement] = useState(false);
  const [resultat, setResultat] = useState<ResultatAttaque | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);

  const lancer = async () => {
    if (!fichier) return;
    setChargement(true);
    setErreur(null);
    try {
      setResultat(await api.attaquer(fichier, attaque, epsilon, mode, cible));
    } catch (e) {
      setErreur(e instanceof ErreurApi ? e.message : "Erreur inattendue.");
    } finally {
      setChargement(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
        <ZoneDepot fichier={fichier} onChange={setFichier} libelle="Déposez une photo de fruit à attaquer" />
        <Carte className="space-y-5">
          <fieldset>
            <legend className="mb-2 font-medium">Attaque</legend>
            <div className="grid gap-2 sm:grid-cols-3">
              {(
                [
                  ["fgsm", "FGSM", "Un seul pas de gradient"],
                  ["pgd", "PGD", "10 pas itératifs"],
                  ["pgd_ciblee", "PGD ciblée", "Vers une classe choisie"],
                ] as const
              ).map(([v, titre, aide]) => (
                <label
                  key={v}
                  className={`cursor-pointer rounded-xl border p-3 text-sm transition ${
                    attaque === v
                      ? "border-bouclier-500 bg-bouclier-50 ring-1 ring-bouclier-500 dark:bg-bouclier-900/30"
                      : "border-slate-200 hover:border-slate-300 dark:border-slate-700"
                  }`}
                >
                  <input type="radio" name="attaque" value={v} checked={attaque === v} onChange={() => setAttaque(v)} className="sr-only" />
                  <span className="block font-semibold">{titre}</span>
                  <span className="text-slate-600 dark:text-slate-400">{aide}</span>
                </label>
              ))}
            </div>
          </fieldset>

          <div>
            <label htmlFor="epsilon" className="flex justify-between font-medium">
              <span>Amplitude ε (norme L∞)</span>
              <span className="tabular-nums">
                {epsilon.toFixed(3).replace(".", ",")} ≈ {Math.round(epsilon * 255)}/255
              </span>
            </label>
            <input
              id="epsilon"
              type="range"
              min={0}
              max={0.1}
              step={0.005}
              value={epsilon}
              onChange={(e) => setEpsilon(Number(e.target.value))}
              className="mt-2 w-full accent-bouclier-600"
            />
            <p className="text-xs text-slate-500 dark:text-slate-400">ε = 0,03 : valeur utilisée à l'entraînement adversarial (perturbation quasi invisible).</p>
          </div>

          {attaque === "pgd_ciblee" && (
            <div>
              <label htmlFor="cible" className="font-medium">
                Classe visée
              </label>
              <select
                id="cible"
                value={cible}
                onChange={(e) => setCible(e.target.value as NomClasse)}
                className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800"
              >
                {CLASSES.map((c) => (
                  <option key={c} value={c}>
                    {libelleClasse(c)}
                  </option>
                ))}
              </select>
            </div>
          )}

          <fieldset>
            <legend className="mb-1 font-medium">Mode</legend>
            <div className="flex flex-wrap gap-4 text-sm">
              <label className="flex items-center gap-2">
                <input type="radio" name="mode" checked={mode === "boite_blanche"} onChange={() => setMode("boite_blanche")} className="accent-bouclier-600" />
                Boîte blanche (chaque modèle attaqué avec ses gradients)
              </label>
              <label className="flex items-center gap-2">
                <input type="radio" name="mode" checked={mode === "transfert"} onChange={() => setMode("transfert")} className="accent-bouclier-600" />
                Transfert (image fabriquée contre le modèle de base)
              </label>
            </div>
          </fieldset>

          <button
            type="button"
            onClick={lancer}
            disabled={!fichier || chargement}
            className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-bouclier-600 px-4 py-3 font-semibold text-white shadow-sm hover:bg-bouclier-700 disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bouclier-600"
          >
            <Swords size={18} aria-hidden="true" />
            {chargement ? "Attaque en cours…" : "Lancer l'attaque"}
          </button>
        </Carte>
      </div>

      <div aria-live="polite" aria-busy={chargement}>
        {chargement && <Chargement texte="Calcul des gradients et de l'image adverse…" />}
        {erreur && <MessageErreur>{erreur}</MessageErreur>}
        {resultat && !chargement && <ResultatVisuel r={resultat} />}
      </div>
    </div>
  );
}

function ResultatVisuel({ r }: { r: ResultatAttaque }) {
  return (
    <div className="animate-apparition space-y-4">
      <div className="grid gap-4 md:grid-cols-[minmax(0,2fr)_minmax(0,5fr)_minmax(0,5fr)]">
        <Carte>
          <h3 className="mb-2 text-sm font-semibold">Image originale</h3>
          <Vignette src={r.image_originale} alt="Image originale, 128 × 128 pixels" />
          <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">Entrée 128×128 telle que vue par le modèle.</p>
        </Carte>
        {(["base", "robuste"] as NomModele[]).map((nom) => (
          <ColonneModele key={nom} nom={nom} r={r} />
        ))}
      </div>
    </div>
  );
}

function ColonneModele({ nom, r }: { nom: NomModele; r: ResultatAttaque }) {
  const m = r.modeles[nom];
  const resiste = !m.trompe;
  return (
    <Carte className={resiste ? "ring-1 ring-frais-500/40" : "ring-1 ring-pourri-500/40"}>
      <div className="mb-3 flex items-center justify-between gap-2">
        <h3 className="font-semibold">Modèle {nom === "base" ? "de base" : "robuste"}</h3>
        <span
          className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
            resiste ? "bg-frais-100 text-frais-700 dark:bg-frais-900/50 dark:text-frais-300" : "bg-pourri-100 text-pourri-700 dark:bg-pourri-900/50 dark:text-pourri-300"
          }`}
        >
          {resiste ? "✓ Résiste" : "✗ Trompé"}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <figure>
          <Vignette src={m.perturbation} alt={`Perturbation amplifiée contre le modèle ${nom}`} />
          <figcaption className="mt-1 text-xs text-slate-500 dark:text-slate-400">Perturbation (amplifiée)</figcaption>
        </figure>
        <figure>
          <Vignette src={m.image_attaquee} alt={`Image attaquée pour le modèle ${nom}`} />
          <figcaption className="mt-1 text-xs text-slate-500 dark:text-slate-400">Image attaquée · L∞ = {m.norme_linf}</figcaption>
        </figure>
      </div>
      <dl className="mt-4 space-y-2 text-sm">
        <Ligne titre="Avant attaque" p={m.propre} />
        <Ligne titre="Après attaque" p={m.attaquee} accent={m.trompe ? "pourri" : "frais"} />
        <Ligne titre="Après purification JPEG" p={m.prediction_purifiee} />
        {m.cible_atteinte !== null && (
          <div className="flex justify-between">
            <dt className="text-slate-600 dark:text-slate-400">Cible atteinte</dt>
            <dd className="font-medium">{m.cible_atteinte ? "Oui (attaque réussie)" : "Non (attaque déjouée)"}</dd>
          </div>
        )}
        <div className="flex justify-between">
          <dt className="text-slate-600 dark:text-slate-400">Détection de manipulation</dt>
          <dd className="font-medium">{m.manipulation_detectee ? "⚠ Image signalée" : "Non signalée"}</dd>
        </div>
      </dl>
      <a
        href={m.image_attaquee}
        download={`attaque_${r.attaque}_eps${r.epsilon}_${nom}.png`}
        className="mt-4 inline-flex items-center gap-2 rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800"
      >
        <Download size={16} aria-hidden="true" /> Télécharger l'image attaquée
      </a>
    </Carte>
  );
}

function Ligne({ titre, p, accent }: { titre: string; p: PredictionAttaque; accent?: "frais" | "pourri" }) {
  const couleur = accent === "pourri" ? "text-pourri-700 dark:text-pourri-300" : accent === "frais" ? "text-frais-700 dark:text-frais-300" : "";
  return (
    <div className="flex justify-between gap-3">
      <dt className="text-slate-600 dark:text-slate-400">{titre}</dt>
      <dd className={`text-right font-medium ${couleur}`}>
        {libelleClasse(p.classe)} <span className="tabular-nums text-slate-500 dark:text-slate-400">({pourcent(p.confiance)})</span>
      </dd>
    </div>
  );
}

function Vignette({ src, alt }: { src: string; alt: string }) {
  return <img src={src} alt={alt} className="aspect-square w-full rounded-lg bg-slate-100 object-contain [image-rendering:pixelated] dark:bg-slate-800" />;
}
