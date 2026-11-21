// Client HTTP typé. Toutes les requêtes passent par /api (même origine : proxy Vite ou Nginx).
import type {
  EtatSante,
  Metriques,
  ModeAttaque,
  NomClasse,
  NomModele,
  Purification,
  RapportSecurite,
  ResultatAnalyse,
  ResultatAttaque,
  ResultatComparaison,
  ResultatScenario,
  Scenario,
  TypeAttaque,
} from "./types";

export class ErreurApi extends Error {
  readonly code: string;
  readonly statut: number;
  constructor(message: string, code: string, statut: number) {
    super(message);
    this.code = code;
    this.statut = statut;
  }
}

const MESSAGES_STATUT: Record<number, string> = {
  413: "Fichier trop volumineux.",
  429: "Trop de requêtes : patientez quelques secondes.",
  503: "Serveur occupé : réessayez dans un instant.",
};

async function requete<T>(chemin: string, init?: RequestInit & { signal?: AbortSignal }): Promise<T> {
  let reponse: Response;
  try {
    reponse = await fetch(`/api${chemin}`, { ...init, credentials: "omit" });
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") throw e;
    throw new ErreurApi("Serveur injoignable : vérifiez que le backend est lancé.", "serveur_indisponible", 0);
  }
  if (!reponse.ok) {
    let detail = MESSAGES_STATUT[reponse.status] ?? "La requête a échoué.";
    let code = `http_${reponse.status}`;
    try {
      const corps = (await reponse.json()) as { detail?: unknown; code?: unknown };
      if (typeof corps.detail === "string") detail = corps.detail;
      if (typeof corps.code === "string") code = corps.code;
    } catch {
      /* corps non JSON : message générique */
    }
    throw new ErreurApi(detail, code, reponse.status);
  }
  return (await reponse.json()) as T;
}

function formulaire(fichier: Blob, champs: Record<string, string | undefined> = {}): FormData {
  const f = new FormData();
  // Nom neutre : le serveur l'ignore de toute façon.
  f.append("fichier", fichier, "image");
  for (const [k, v] of Object.entries(champs)) if (v !== undefined) f.append(k, v);
  return f;
}

function parametres(p: Record<string, string | undefined>): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(p)) if (v) q.set(k, v);
  const s = q.toString();
  return s ? `?${s}` : "";
}

export const api = {
  sante: (signal?: AbortSignal) => requete<EtatSante>("/sante", { signal }),
  metriques: () => requete<Metriques>("/metriques"),
  rapportSecurite: () => requete<RapportSecurite>("/rapport-securite"),
  scenarios: () => requete<Scenario[]>("/scenarios"),
  executerScenario: (id: string) => requete<ResultatScenario>(`/scenarios/${encodeURIComponent(id)}`, { method: "POST" }),

  analyser: (
    fichier: Blob,
    options: { modele?: NomModele; purification?: Purification; source?: "upload" | "webcam"; signal?: AbortSignal } = {},
  ) =>
    requete<ResultatAnalyse>(
      `/analyser${parametres({ modele: options.modele, purification: options.purification, source: options.source })}`,
      { method: "POST", body: formulaire(fichier), signal: options.signal },
    ),

  comparer: (fichier: Blob, purification?: Purification) =>
    requete<ResultatComparaison>(`/analyser/comparer${parametres({ purification })}`, {
      method: "POST",
      body: formulaire(fichier),
    }),

  attaquer: (fichier: Blob, attaque: TypeAttaque, epsilon: number, mode: ModeAttaque, cible?: NomClasse) =>
    requete<ResultatAttaque>("/attaque", {
      method: "POST",
      body: formulaire(fichier, {
        attaque,
        epsilon: epsilon.toFixed(4),
        mode,
        cible: attaque === "pgd_ciblee" ? cible : undefined,
      }),
    }),
};
