// Page de connexion : accès réservé aux comptes configurés côté serveur.
import { Eye, EyeOff, Moon, Sun } from "lucide-react";
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
    "mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-base outline-none focus:border-slate-900 focus:ring-1 focus:ring-slate-900 dark:border-slate-700 dark:bg-slate-900 dark:focus:border-slate-100 dark:focus:ring-slate-100";

  return (
    <div className="relative flex min-h-screen items-center justify-center px-4 py-10">
      <button
        type="button"
        onClick={basculerTheme}
        className="absolute right-4 top-4 rounded-lg p-2 text-slate-600 hover:bg-slate-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-bouclier-500 dark:text-slate-300 dark:hover:bg-slate-800"
        aria-label={theme === "sombre" ? "Passer en mode clair" : "Passer en mode sombre"}
      >
        {theme === "sombre" ? <Sun aria-hidden="true" /> : <Moon aria-hidden="true" />}
      </button>

      <main className="w-full max-w-sm">
        <h1 className="text-2xl font-bold tracking-tight">
          <span className="text-frais-600 dark:text-frais-300">Fresh</span>
          <span className="text-pourri-600 dark:text-pourri-300">Rotten</span> Guard
        </h1>
        <p className="mt-1 text-slate-600 dark:text-slate-400">Connectez-vous pour utiliser l'application.</p>

        <form
          onSubmit={soumettre}
          noValidate
          aria-describedby={erreur ? idErreur : undefined}
          className="mt-6 space-y-4 rounded-xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900"
        >
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
                className="absolute right-1.5 top-1/2 -translate-y-1/2 rounded-lg p-2 text-slate-500 hover:text-slate-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-bouclier-500 dark:hover:text-slate-100"
                aria-label={visible ? "Masquer le mot de passe" : "Afficher le mot de passe"}
                aria-pressed={visible}
              >
                {visible ? <EyeOff size={18} aria-hidden="true" /> : <Eye size={18} aria-hidden="true" />}
              </button>
            </div>
          </div>

          {erreur && (
            <p
              id={idErreur}
              role="alert"
              className="rounded-lg bg-pourri-50 px-3 py-2 text-sm font-medium text-pourri-700 dark:bg-pourri-900/40 dark:text-pourri-300"
            >
              {erreur}
            </p>
          )}

          <button
            type="submit"
            disabled={chargement || !identifiant || !motDePasse}
            className="w-full rounded-lg bg-slate-900 px-4 py-2.5 font-semibold text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-900 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white"
          >
            {chargement ? "Connexion…" : "Se connecter"}
          </button>
        </form>

        <p className="mt-4 text-sm text-slate-500 dark:text-slate-400">
          La session dure 8 heures et s'efface à la fermeture de l'onglet.
        </p>
      </main>
    </div>
  );
}
