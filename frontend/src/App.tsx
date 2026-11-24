// Coque de l'application : en-tête, onglets accessibles, thème, état du serveur.
import { Moon, ServerOff, Sun } from "lucide-react";
import { Suspense, lazy, useEffect, useRef, useState, type KeyboardEvent } from "react";
import { api } from "./api/client";
import type { EtatSante } from "./api/types";
import { EVENEMENT_DECONNEXION, effacerSession, lireSession, type Session } from "./lib/session";
import { PageAPropos } from "./pages/PageAPropos";
import { PageConnexion } from "./pages/PageConnexion";
import { PageAnalyse } from "./pages/PageAnalyse";
import { PageWebcam } from "./pages/PageWebcam";
import { Squelette } from "./composants/Messages";
import { useTheme } from "./lib/theme";

// Le Laboratoire (graphiques Recharts) est chargé à la demande : page d'accueil plus légère.
const PageLaboratoire = lazy(() => import("./pages/PageLaboratoire").then((m) => ({ default: m.PageLaboratoire })));

const ONGLETS = [
  { id: "webcam", titre: "Webcam" },
  { id: "analyse", titre: "Analyser une image" },
  { id: "labo", titre: "Laboratoire de sécurité" },
  { id: "apropos", titre: "À propos" },
] as const;
type IdOnglet = (typeof ONGLETS)[number]["id"];

export default function App() {
  const [theme, basculerTheme] = useTheme();
  const [session, setSession] = useState<Session | null>(lireSession);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    const expiree = () => {
      setSession(null);
      setMessage("Votre session a expiré : reconnectez-vous.");
    };
    window.addEventListener(EVENEMENT_DECONNEXION, expiree);
    return () => window.removeEventListener(EVENEMENT_DECONNEXION, expiree);
  }, []);

  if (!session) {
    return (
      <PageConnexion
        theme={theme}
        basculerTheme={basculerTheme}
        message={message}
        onConnecte={(s) => {
          setMessage(null);
          setSession(s);
        }}
      />
    );
  }
  return (
    <Application
      theme={theme}
      basculerTheme={basculerTheme}
      session={session}
      onDeconnexion={() => {
        effacerSession();
        setMessage("Vous êtes déconnecté.");
        setSession(null);
      }}
    />
  );
}

function Application({
  theme,
  basculerTheme,
  session,
  onDeconnexion,
}: {
  theme: ReturnType<typeof useTheme>[0];
  basculerTheme: () => void;
  session: Session;
  onDeconnexion: () => void;
}) {
  const [onglet, setOnglet] = useState<IdOnglet>("analyse");
  const [sante, setSante] = useState<EtatSante | null | "hors_ligne">(null);
  const refs = useRef<Record<string, HTMLButtonElement | null>>({});

  useEffect(() => {
    const verifier = () => api.sante().then(setSante, () => setSante("hors_ligne"));
    void verifier();
    const t = window.setInterval(verifier, 15000);
    return () => window.clearInterval(t);
  }, []);

  // Navigation clavier des onglets (flèches, Début, Fin) selon le motif ARIA « tabs ».
  const clavier = (e: KeyboardEvent<HTMLButtonElement>, i: number) => {
    const n = ONGLETS.length;
    const cible = { ArrowRight: (i + 1) % n, ArrowLeft: (i - 1 + n) % n, Home: 0, End: n - 1 }[e.key];
    if (cible === undefined) return;
    e.preventDefault();
    const id = ONGLETS[cible]!.id;
    setOnglet(id);
    refs.current[id]?.focus();
  };

  return (
    <div className="min-h-screen">
      <a href="#contenu" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-white focus:px-4 focus:py-2 focus:text-slate-900">
        Aller au contenu
      </a>
      <header className="border-b border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-950">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-4 px-4 py-4 sm:px-6">
          <div>
            <h1 className="text-xl font-bold tracking-tight">
              <span className="text-frais-600 dark:text-frais-300">Fresh</span>
              <span className="text-pourri-600 dark:text-pourri-300">Rotten</span> Guard
            </h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">Pomme, banane, orange : fraîche ou pourrie ?</p>
          </div>
          <div className="ml-auto">
            <IndicateurServeur sante={sante} />
          </div>
          <span className="hidden text-sm text-slate-600 sm:inline dark:text-slate-300">
            {session.identifiant}
          </span>
          <button
            type="button"
            onClick={onDeconnexion}
            className="rounded-lg px-3 py-1.5 text-sm font-medium text-slate-700 ring-1 ring-slate-300 hover:bg-slate-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-bouclier-500 dark:text-slate-200 dark:ring-slate-700 dark:hover:bg-slate-800"
          >
            Se déconnecter
          </button>
          <button
            type="button"
            onClick={basculerTheme}
            className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-bouclier-500 dark:text-slate-300 dark:hover:bg-slate-800"
            aria-label={theme === "sombre" ? "Passer en mode clair" : "Passer en mode sombre"}
          >
            {theme === "sombre" ? <Sun aria-hidden="true" /> : <Moon aria-hidden="true" />}
          </button>
        </div>
        <nav className="mx-auto max-w-7xl overflow-x-auto px-4 sm:px-6" aria-label="Navigation principale">
          <div role="tablist" className="flex gap-1">
            {ONGLETS.map(({ id, titre }, i) => (
              <button
                key={id}
                ref={(el) => {
                  refs.current[id] = el;
                }}
                id={`onglet-${id}`}
                role="tab"
                type="button"
                aria-selected={onglet === id}
                aria-controls="contenu"
                tabIndex={onglet === id ? 0 : -1}
                onClick={() => setOnglet(id)}
                onKeyDown={(e) => clavier(e, i)}
                className={`whitespace-nowrap border-b-2 px-3 py-3 text-[15px] font-medium transition focus-visible:outline focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-bouclier-500 ${
                  onglet === id
                    ? "border-slate-900 text-slate-900 dark:border-slate-100 dark:text-slate-100"
                    : "border-transparent text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100"
                }`}
              >
                {titre}
              </button>
            ))}
          </div>
        </nav>
      </header>

      {sante === "hors_ligne" && (
        <div role="alert" className="bg-pourri-600 px-4 py-2 text-center text-sm font-medium text-white">
          <ServerOff size={16} className="mr-2 inline" aria-hidden="true" />
          Serveur indisponible : lancez le backend (voir README.md), la page se reconnectera automatiquement.
        </div>
      )}

      <main id="contenu" role="tabpanel" aria-labelledby={`onglet-${onglet}`} className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
        {onglet === "webcam" && <PageWebcam />}
        {onglet === "analyse" && <PageAnalyse />}
        {onglet === "labo" && (
          <Suspense fallback={<Squelette lignes={6} />}>
            <PageLaboratoire theme={theme} />
          </Suspense>
        )}
        {onglet === "apropos" && <PageAPropos />}
      </main>
      <footer className="mx-auto max-w-7xl px-4 pb-8 text-xs text-slate-500 sm:px-6 dark:text-slate-400">
        Aucune image n'est stockée. Projet pédagogique de sécurité de l'IA.
      </footer>
    </div>
  );
}

function IndicateurServeur({ sante }: { sante: EtatSante | null | "hors_ligne" }) {
  if (sante === null) return null;
  const ok = sante !== "hors_ligne" && sante.statut === "ok";
  const texte =
    sante === "hors_ligne" ? "Serveur hors ligne" : sante.statut === "ok" ? `Modèle ${sante.modele_actif}, défenses actives` : "Seuils non calibrés";
  return (
    <span
      className={`inline-flex items-center gap-1.5 text-sm ${
        ok ? "text-slate-600 dark:text-slate-300" : "text-pourri-700 dark:text-pourri-300"
      }`}
    >
      <span className={`h-2 w-2 rounded-full ${ok ? "bg-frais-500" : "bg-pourri-500"}`} aria-hidden="true" />
      {texte}
    </span>
  );
}
