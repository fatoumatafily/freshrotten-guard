// Onglet « Webcam » : analyse en direct de la zone de visée, avec lissage et bouton « Figer ».
import { Camera, CameraOff, EyeOff, Pause, Play, Snowflake } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { ErreurApi, api } from "../api/client";
import type { ResultatAnalyse } from "../api/types";
import { CarteResultat } from "../composants/CarteResultat";
import { JaugeConfiance } from "../composants/JaugeConfiance";
import { Carte, MessageErreur } from "../composants/Messages";
import { BadgeVerdict } from "../composants/Verdict";
import { libelleClasse, pourcent, typeVerdict } from "../lib/libelles";
import { lisser } from "../lib/lissage";

const PART_CADRE = 0.6; // côté du cadre de visée = 60 % du plus petit côté de la vidéo
const TAILLE_HISTORIQUE = 5;

type EtatCamera = "inactive" | "demande" | "active" | "refusee" | "absente" | "erreur";

export function PageWebcam() {
  const video = useRef<HTMLVideoElement>(null);
  const flux = useRef<MediaStream | null>(null);
  const [etat, setEtat] = useState<EtatCamera>("inactive");
  const [intervalle, setIntervalle] = useState(400);
  const [enPause, setEnPause] = useState(false);
  const [historique, setHistorique] = useState<ResultatAnalyse[]>([]);
  const [fige, setFige] = useState<{ image: string; resultat: ResultatAnalyse } | null>(null);
  const [erreurReseau, setErreurReseau] = useState<string | null>(null);
  const [cadre, setCadre] = useState({ l: 60, h: 60 });
  const derniereImage = useRef<string | null>(null);

  const arreter = useCallback(() => {
    flux.current?.getTracks().forEach((t) => t.stop());
    flux.current = null;
  }, []);

  useEffect(() => arreter, [arreter]);

  const demarrer = async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      setEtat("erreur");
      return;
    }
    setEtat("demande");
    try {
      const f = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment", width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      });
      flux.current = f;
      setEtat("active");
      setHistorique([]);
      setFige(null);
    } catch (e) {
      const nom = e instanceof DOMException ? e.name : "";
      setEtat(nom === "NotAllowedError" || nom === "SecurityError" ? "refusee" : nom === "NotFoundError" ? "absente" : "erreur");
    }
  };

  // Branche le flux sur la balise vidéo une fois celle-ci affichée.
  useEffect(() => {
    if (etat === "active" && video.current && flux.current) {
      video.current.srcObject = flux.current;
      void video.current.play().catch(() => undefined);
    }
  }, [etat]);

  /** Capture uniquement la zone du cadre de visée (en mémoire, jamais stockée). */
  const capturer = useCallback(async (): Promise<Blob | null> => {
    const v = video.current;
    if (!v || v.videoWidth === 0) return null;
    const cote = Math.round(Math.min(v.videoWidth, v.videoHeight) * PART_CADRE);
    const x = Math.round((v.videoWidth - cote) / 2);
    const y = Math.round((v.videoHeight - cote) / 2);
    setCadre({ l: (cote / v.videoWidth) * 100, h: (cote / v.videoHeight) * 100 });
    const canvas = document.createElement("canvas");
    canvas.width = Math.min(cote, 512);
    canvas.height = canvas.width;
    const ctx = canvas.getContext("2d");
    if (!ctx) return null;
    ctx.drawImage(v, x, y, cote, cote, 0, 0, canvas.width, canvas.height);
    derniereImage.current = canvas.toDataURL("image/jpeg", 0.85);
    return new Promise((resoudre) => canvas.toBlob((b) => resoudre(b), "image/jpeg", 0.9));
  }, []);

  // Boucle d'analyse : une seule requête à la fois, puis attente de « intervalle » ms.
  useEffect(() => {
    if (etat !== "active" || enPause || fige) return;
    let actif = true;
    let minuteur: number | undefined;
    const controleur = new AbortController();

    const tour = async () => {
      if (!actif) return;
      try {
        const image = await capturer();
        if (image && actif) {
          const r = await api.analyser(image, { source: "webcam", signal: controleur.signal });
          if (!actif) return;
          setErreurReseau(null);
          setHistorique((h) => [...h, r].slice(-TAILLE_HISTORIQUE));
        }
      } catch (e) {
        if (!actif || (e instanceof DOMException && e.name === "AbortError")) return;
        setErreurReseau(e instanceof ErreurApi ? e.message : "Erreur réseau.");
      }
      if (actif) minuteur = window.setTimeout(tour, intervalle);
    };
    minuteur = window.setTimeout(tour, 150);
    return () => {
      actif = false;
      controleur.abort();
      window.clearTimeout(minuteur);
    };
  }, [etat, enPause, fige, intervalle, capturer]);

  const verdict = lisser(historique);
  const figer = () => {
    if (!verdict || !derniereImage.current) return;
    setFige({ image: derniereImage.current, resultat: verdict.dernier });
  };

  if (etat !== "active") {
    return <EcranAutorisation etat={etat} onDemarrer={demarrer} />;
  }

  const typeAffiche = verdict ? (verdict.cle === "rejet" ? "rejet" : typeVerdict("ok", verdict.cle.endsWith("fresh") ? "fresh" : "rotten")) : null;

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]">
      <div className="space-y-3">
        <div className="relative overflow-hidden rounded-2xl bg-black shadow-sm">
          <video ref={video} playsInline muted className="block h-auto w-full" aria-label="Flux de la caméra" />
          {/* Cadre de visée : seule cette zone est envoyée au serveur. */}
          <div
            aria-hidden="true"
            className={`pointer-events-none absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-xl border-4 shadow-[0_0_0_9999px_rgba(0,0,0,0.45)] transition-colors ${
              typeAffiche === "frais" ? "border-frais-500" : typeAffiche === "pourri" ? "border-pourri-500" : "border-white/80"
            }`}
            style={{ width: `${cadre.l}%`, height: `${cadre.h}%` }}
          />
          <p className="absolute bottom-3 left-1/2 -translate-x-1/2 rounded-full bg-black/60 px-3 py-1 text-xs text-white">
            Placez le fruit dans le cadre
          </p>
          {fige && <img src={fige.image} alt="Image figée" className="absolute inset-0 m-auto h-full object-contain" />}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {fige ? (
            <Bouton onClick={() => setFige(null)} icone={<Play size={16} />}>
              Reprendre le direct
            </Bouton>
          ) : (
            <>
              <Bouton onClick={figer} icone={<Snowflake size={16} />} disabled={!verdict} principal>
                Figer
              </Bouton>
              <Bouton onClick={() => setEnPause((p) => !p)} icone={enPause ? <Play size={16} /> : <Pause size={16} />}>
                {enPause ? "Reprendre" : "Pause"}
              </Bouton>
            </>
          )}
          <Bouton
            onClick={() => {
              arreter();
              setEtat("inactive");
              setHistorique([]);
              setFige(null);
            }}
            icone={<CameraOff size={16} />}
          >
            Couper la caméra
          </Bouton>
          <label className="ml-auto flex items-center gap-2 text-sm">
            <span>Cadence</span>
            <input
              type="range"
              min={300}
              max={1000}
              step={50}
              value={intervalle}
              onChange={(e) => setIntervalle(Number(e.target.value))}
              aria-valuetext={`${intervalle} millisecondes`}
              className="accent-bouclier-600"
            />
            <span className="w-16 tabular-nums">{intervalle} ms</span>
          </label>
        </div>
        <p className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
          <EyeOff size={14} aria-hidden="true" />
          Confidentialité : les images sont analysées en mémoire puis oubliées. Rien n'est stocké, ni sur le serveur ni dans les
          journaux.
        </p>
      </div>

      <div className="space-y-4">
        {erreurReseau && <MessageErreur titre="Analyse interrompue">{erreurReseau}</MessageErreur>}
        {fige ? (
          <CarteResultat resultat={fige.resultat} titre="Instant figé" detailsOuverts />
        ) : (
          <Carte>
            <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">En direct</h2>
            <div aria-live="polite" aria-atomic="true">
              {!verdict || !typeAffiche ? (
                <p className="text-slate-600 dark:text-slate-400">{enPause ? "En pause." : "Analyse en cours…"}</p>
              ) : verdict.cle === "rejet" ? (
                <div className="space-y-2">
                  <BadgeVerdict type="rejet" taille="lg" />
                  <p className="text-xl font-semibold">Aucun fruit reconnu</p>
                  <p className="text-sm text-slate-600 dark:text-slate-400">{verdict.dernier.raison_rejet}</p>
                </div>
              ) : (
                <div className="space-y-3">
                  <BadgeVerdict type={typeAffiche} taille="lg" />
                  <p className="text-2xl font-bold">{libelleClasse(verdict.cle)}</p>
                  <JaugeConfiance valeur={verdict.confiance} type={typeAffiche} libelle="Confiance moyenne" />
                </div>
              )}
            </div>
            {verdict && (
              <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
                Lissage sur {historique.length} image(s) : {pourcent(verdict.part, 0)} des votes.
              </p>
            )}
          </Carte>
        )}
      </div>
    </div>
  );
}

function EcranAutorisation({ etat, onDemarrer }: { etat: EtatCamera; onDemarrer: () => void }) {
  const messages: Partial<Record<EtatCamera, { titre: string; texte: string }>> = {
    refusee: {
      titre: "Accès à la caméra refusé",
      texte: "Autorisez la caméra dans les réglages du navigateur (icône à gauche de l'adresse), puis réessayez.",
    },
    absente: { titre: "Aucune caméra détectée", texte: "Branchez une webcam ou utilisez l'onglet « Analyser une image »." },
    erreur: {
      titre: "Caméra indisponible",
      texte: "Le navigateur n'a pas pu ouvrir la caméra (elle est peut-être utilisée par une autre application, ou la page n'est pas servie en HTTPS / localhost).",
    },
  };
  const m = messages[etat];
  return (
    <Carte className="mx-auto max-w-2xl space-y-4 text-center">
      <Camera size={44} className="mx-auto text-frais-600" aria-hidden="true" />
      <h2 className="text-xl font-semibold">Analyse en direct par webcam</h2>
      <p className="text-slate-600 dark:text-slate-300">
        La caméra sert uniquement à analyser le fruit placé dans le cadre de visée. Seule cette zone est envoyée, une image
        toutes les 300 à 1000 ms. <strong>Aucune image n'est enregistrée</strong>, ni sur le serveur, ni dans les journaux.
      </p>
      {m && (
        <MessageErreur titre={m.titre} serveur={false}>
          {m.texte}
        </MessageErreur>
      )}
      <button
        type="button"
        onClick={onDemarrer}
        disabled={etat === "demande"}
        className="inline-flex items-center gap-2 rounded-xl bg-frais-600 px-5 py-3 font-semibold text-white shadow-sm hover:bg-frais-700 disabled:opacity-60 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-frais-600"
      >
        <Camera size={18} aria-hidden="true" />
        {etat === "demande" ? "En attente d'autorisation…" : "Activer la caméra"}
      </button>
    </Carte>
  );
}

function Bouton({
  children,
  onClick,
  icone,
  disabled,
  principal,
}: {
  children: React.ReactNode;
  onClick: () => void;
  icone: React.ReactNode;
  disabled?: boolean;
  principal?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bouclier-500 ${
        principal
          ? "bg-bouclier-600 text-white hover:bg-bouclier-700"
          : "border border-slate-300 bg-white hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:hover:bg-slate-800"
      }`}
    >
      <span aria-hidden="true">{icone}</span>
      {children}
    </button>
  );
}
