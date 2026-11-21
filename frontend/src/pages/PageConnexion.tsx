// Page de connexion : accès réservé aux comptes configurés côté serveur.
import { Eye, EyeOff, LockKeyhole, LogIn, Moon, ShieldCheck, Sun } from "lucide-react";
import { useId, useState, type FormEvent } from "react";
import { ErreurApi, api } from "../api/client";
import { enregistrerSession, type Session } from "../lib/session";
import type { Theme } from "../lib/theme";

interface Props {
  onConnecte: (s: Session) => void;
  theme: Theme;
  basculerTheme: () => void;
  message?: string | null;
}

export function PageConnexion({ onConnecte, theme, basculerTheme, message }: Props) {
  const [identifiant, setIdentifiant] = useState("");
  const [motDePasse, setMotDePasse] = useState("");
  const [visible, setVisible] = useState(false);
  const [chargement, setChargement] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);
  const idErreur = useId();

  const soumettre = async (e: FormEvent) => {
    e.preventDefault();
    if (!identifiant || !motDePasse) return;
    setChargement(true);
    setErreur(null);
    try {
      const session = await api.connexion(identifiant.trim(), motDePasse);
      enregistrerSession(session);
      setMotDePasse("");
      onConnecte(session);
    } catch (err) {
      setErreur(err instanceof ErreurApi ? err.message : "Connexion impossible.");
      setMotDePasse("");
    } finally {
      setChargement(false);
    }
  };

  const champ =
    "mt-1 w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-base shadow-sm outline-none transition focus:border-frais-500 focus:ring-2 focus:ring-frais-500/30 dark:border-slate-700 dark:bg-slate-800";

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-gradient-to-br from-frais-50 via-slate-50 to-bouclier-50 px-4 py-10 dark:from-slate-950 dark:via-slate-950 dark:to-bouclier-900/40">
      <button
        type="button"
        onClick={basculerTheme}
        className="absolute right-4 top-4 rounded-lg p-2 text-slate-600 hover:bg-white/60 focus-visible:outline focus-visible:outline-2 focus-visible:outline-bouclier-500 dark:text-slate-300 dark:hover:bg-slate-800"
        aria-label={theme === "sombre" ? "Passer en mode clair" : "Passer en mode sombre"}
      >
        {theme === "sombre" ? <Sun aria-hidden="true" /> : <Moon aria-hidden="true" />}
      </button>

      <main className="w-full max-w-md animate-apparition">
        <div className="mb-6 text-center">
          <span className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-frais-600 text-white shadow-md">
            <ShieldCheck size={30} aria-hidden="true" />
          </span>
          <h1 className="mt-4 text-2xl font-bold">FreshRotten Guard</h1>
          <p className="mt-1 text-slate-600 dark:text-slate-400">Fruit frais ou pourri · IA défendue</p>
        </div>

        <form
          onSubmit={soumettre}
          noValidate
          aria-describedby={erreur ? idErreur : undefined}
          className="space-y-5 rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-lg backdrop-blur sm:p-8 dark:border-slate-800 dark:bg-slate-900/90"
        >
          <div>
            <h2 className="flex items-center gap-2 text-lg font-semibold">
              <LockKeyhole size={18} aria-hidden="true" /> Connexion
            </h2>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">Accès réservé. Connectez-vous pour utiliser l'application.</p>
          </div>

          {message && !erreur && (
            <p role="status" className="rounded-lg bg-slate-100 px-3 py-2 text-sm dark:bg-slate-800">
              {message}
            </p>
          )}

          <div>
            <label htmlFor="identifiant" className="text-sm font-medium">
              Identifiant
            </label>
            <input
              id="identifiant"
              name="username"
              autoComplete="username"
              autoCapitalize="none"
              spellCheck={false}
              required
              maxLength={64}
              value={identifiant}
              onChange={(e) => setIdentifiant(e.target.value)}
              className={champ}
              autoFocus
            />
          </div>

          <div>
            <label htmlFor="mot-de-passe" className="text-sm font-medium">
              Mot de passe
            </label>
            <div className="relative">
              <input
                id="mot-de-passe"
                name="password"
                type={visible ? "text" : "password"}
                autoComplete="current-password"
                required
                maxLength={256}
                value={motDePasse}
                onChange={(e) => setMotDePasse(e.target.value)}
                className={`${champ} pr-11`}
              />
              <button
                type="button"
                onClick={() => setVisible((v) => !v)}
                className="absolute right-1.5 top-1/2 -translate-y-1/2 rounded-lg p-2 text-slate-500 hover:text-slate-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-bouclier-500 dark:hover:text-slate-200"
                aria-label={visible ? "Masquer le mot de passe" : "Afficher le mot de passe"}
                aria-pressed={visible}
              >
                {visible ? <EyeOff size={18} aria-hidden="true" /> : <Eye size={18} aria-hidden="true" />}
              </button>
            </div>
          </div>

          {erreur && (
            <p id={idErreur} role="alert" className="rounded-lg border border-pourri-500/30 bg-pourri-50 px-3 py-2 text-sm font-medium text-pourri-800 dark:bg-pourri-900/30 dark:text-pourri-200">
              {erreur}
            </p>
          )}

          <button
            type="submit"
            disabled={chargement || !identifiant || !motDePasse}
            className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-frais-600 px-4 py-3 font-semibold text-white shadow-sm transition hover:bg-frais-700 disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-frais-600"
          >
            <LogIn size={18} aria-hidden="true" />
            {chargement ? "Connexion…" : "Se connecter"}
          </button>
        </form>

        <p className="mt-6 text-center text-xs text-slate-500 dark:text-slate-400">
          Session valable 8 h, effacée à la fermeture de l'onglet. 5 tentatives par minute au maximum.
        </p>
      </main>
    </div>
  );
}
