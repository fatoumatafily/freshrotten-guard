// Session utilisateur : jeton gardé en sessionStorage (effacé à la fermeture de l'onglet).
// Pas de cookie : le frontend (Vercel) et l'API (Hugging Face) sont sur deux domaines.

export interface Session {
  jeton: string;
  identifiant: string;
  expire_le: number; // horodatage Unix (secondes)
}

const CLE = "frg-session";
export const EVENEMENT_DECONNEXION = "frg:deconnexion";

export function lireSession(): Session | null {
  try {
    const brut = sessionStorage.getItem(CLE);
    if (!brut) return null;
    const s = JSON.parse(brut) as Session;
    if (typeof s.jeton !== "string" || s.expire_le * 1000 <= Date.now()) {
      sessionStorage.removeItem(CLE);
      return null;
    }
    return s;
  } catch {
    return null;
  }
}

export function enregistrerSession(s: Session): void {
  try {
    sessionStorage.setItem(CLE, JSON.stringify(s));
  } catch {
    /* stockage indisponible : la session ne survivra pas à un rechargement */
  }
  memoire = s;
}

export function effacerSession(): void {
  try {
    sessionStorage.removeItem(CLE);
  } catch {
    /* rien */
  }
  memoire = null;
}

let memoire: Session | null = null;

/** Jeton courant (mémoire d'abord, puis sessionStorage). */
export function jetonCourant(): string | null {
  return (memoire ?? lireSession())?.jeton ?? null;
}
