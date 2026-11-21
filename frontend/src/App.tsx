// Coque de l'application : en-tête, onglets accessibles, thème, état du serveur.
import { Camera, FlaskConical, Info, Moon, ServerOff, ShieldCheck, Sun, Upload } from "lucide-react";
import { Suspense, lazy, useEffect, useRef, useState, type KeyboardEvent } from "react";
import { api } from "./api/client";
import type { EtatSante } from "./api/types";
import { PageAPropos } from "./pages/PageAPropos";
import { PageAnalyse } from "./pages/PageAnalyse";
import { PageWebcam } from "./pages/PageWebcam";
import { Squelette } from "./composants/Messages";
import { useTheme } from "./lib/theme";

// Le Laboratoire (graphiques Recharts) est chargé à la demande : page d'accueil plus légère.
const PageLaboratoire = lazy(() => import("./pages/PageLaboratoire").then((m) => ({ default: m.PageLaboratoire })));

const ONGLETS = [
  { id: "webcam", titre: "Webcam", Icone: Camera },
  { id: "analyse", titre: "Analyser une image", Icone: Upload },
  { id: "labo", titre: "Laboratoire de sécurité", Icone: FlaskConical },
  { id: "apropos", titre: "À propos", Icone: Info },
] as const;
type IdOnglet = (typeof ONGLETS)[number]["id"];

export default function App() {
  const [onglet, setOnglet] = useState<IdOnglet>("analyse");
  const [theme, basculerTheme] = useTheme();
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
      <header className="border-b border-slate-200 bg-white/80 backdrop-blur dark:border-slate-800 dark:bg-slate-950/80">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-4 px-4 py-4 sm:px-6">
          <div className="flex items-center gap-2.5">
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-frais-600 text-white shadow-sm">
              <ShieldCheck aria-hidden="true" />
            </span>
            <div>
              <h1 className="text-lg font-bold leading-tight">FreshRotten Guard</h1>
              <p className="text-xs text-slate-500 dark:text-slate-400">Fruit frais ou pourri · IA défendue</p>
            </div>
          </div>
          <IndicateurServeur sante={sante} />
          <button
            type="button"
            onClick={basculerTheme}
            className="ml-auto rounded-lg p-2 text-slate-600 hover:bg-slate-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-bouclier-500 dark:text-slate-300 dark:hover:bg-slate-800"
            aria-label={theme === "sombre" ? "Passer en mode clair" : "Passer en mode sombre"}
          >
            {theme === "sombre" ? <Sun aria-hidden="true" /> : <Moon aria-hidden="true" />}
          </button>
        </div>
        <nav className="mx-auto max-w-7xl overflow-x-auto px-4 sm:px-6" aria-label="Navigation principale">
          <div role="tablist" className="flex gap-1">
            {ONGLETS.map(({ id, titre, Icone }, i) => (
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
                className={`inline-flex items-center gap-2 whitespace-nowrap border-b-2 px-3 py-3 text-sm font-medium transition focus-visible:outline focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-bouclier-500 ${
                  onglet === id
                    ? "border-frais-600 text-frais-700 dark:border-frais-300 dark:text-frais-300"
                    : "border-transparent text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100"
                }`}
              >
                <Icone size={16} aria-hidden="true" />
                {titre}
              </button>
            ))}
          </div>
        </nav>
      </header>

      {sante === "hors_ligne" && (
        <div role="alert" className="bg-pourri-600 px-4 py-2 text-center text-sm font-medium text-white">
          <ServerOff size={16} className="mr-2 inline" aria-hidden="true" />
          Serveur indisponible : lancez le backend (voir README), la page se reconnectera automatiquement.
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
    sante === "hors_ligne" ? "Serveur hors ligne" : sante.statut === "ok" ? `Modèle ${sante.modele_actif} · défenses actives` : "Seuils non calibrés";
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${
        ok ? "bg-frais-50 text-frais-700 dark:bg-frais-900/40 dark:text-frais-300" : "bg-pourri-50 text-pourri-700 dark:bg-pourri-900/40 dark:text-pourri-300"
      }`}
    >
      <span className={`h-2 w-2 rounded-full ${ok ? "bg-frais-500" : "bg-pourri-500"}`} aria-hidden="true" />
      {texte}
    </span>
  );
}
