// Contrôles côté navigateur (confort d'utilisation). Le serveur revérifie TOUT :
// ces contrôles ne sont jamais une défense de sécurité à eux seuls.

export const TAILLE_MAX_OCTETS = 5 * 1024 * 1024;
export const TYPES_ACCEPTES = ["image/jpeg", "image/png", "image/webp"] as const;

export function verifierFichier(f: File): string | null {
  if (f.size === 0) return "Fichier vide.";
  if (f.size > TAILLE_MAX_OCTETS) return "Fichier trop volumineux (5 Mo maximum).";
  if (!(TYPES_ACCEPTES as readonly string[]).includes(f.type)) return "Format non accepté : utilisez JPEG, PNG ou WebP.";
  return null;
}
