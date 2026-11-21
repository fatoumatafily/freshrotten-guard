// Libellés français des classes, fruits, alertes et contrôles.
import type { NomClasse } from "../api/types";

export const FRUITS: Record<string, string> = { apple: "Pomme", banana: "Banane", orange: "Orange" };
export const ETATS: Record<string, string> = { fresh: "Frais", rotten: "Pourri" };

export const CLASSES: NomClasse[] = [
  "apple_fresh",
  "apple_rotten",
  "banana_fresh",
  "banana_rotten",
  "orange_fresh",
  "orange_rotten",
];

export function libelleClasse(classe: string): string {
  const [fruit = "", etat = ""] = classe.split("_");
  const f = FRUITS[fruit] ?? fruit;
  // Accord : « Pomme fraîche », « Banane pourrie », « Orange fraîche ».
  const e = etat === "fresh" ? "fraîche" : etat === "rotten" ? "pourrie" : etat;
  return `${f} ${e}`;
}

export const ALERTES: Record<string, string> = {
  image_possiblement_manipulee: "Image possiblement manipulée (la prédiction change après purification)",
  metadonnees_exif_supprimees: "Métadonnées EXIF supprimées",
  orientation_exif_appliquee: "Orientation EXIF appliquée",
  transparence_aplatie_sur_blanc: "Transparence aplatie sur fond blanc",
  cmjn_converti: "Image CMJN convertie en RGB",
  profondeur_16_bits_convertie: "Image 16 bits convertie en 8 bits",
};

export const CONTROLES: Record<string, string> = {
  luminosite_min: "Luminosité minimale",
  luminosite_max: "Luminosité maximale",
  contraste: "Contraste (image non uniforme)",
  nettete: "Netteté (variance du Laplacien)",
  couleurs: "Photo (nombre de couleurs distinctes)",
  personne: "Détection de personne",
  gardien_distance: "Gardien sémantique (distance au domaine)",
  autre_fruit: "Autre fruit (ImageNet)",
  confiance: "Confiance du modèle",
  entropie: "Entropie des probabilités",
  energie: "Score d'énergie",
  coherence: "Cohérence gardien / modèle",
  manipulation: "Détection de manipulation",
};

export const ATTAQUES: Record<string, string> = { fgsm: "FGSM", pgd: "PGD (10 pas)", pgd_ciblee: "PGD ciblée" };

export function pourcent(x: number | null | undefined, decimales = 1): string {
  if (x === null || x === undefined || Number.isNaN(x)) return "—";
  return `${(x * 100).toFixed(decimales).replace(".", ",")} %`;
}

export type TypeVerdict = "frais" | "pourri" | "rejet";

export function typeVerdict(statut: "ok" | "rejet", etat: string | null): TypeVerdict {
  if (statut === "rejet") return "rejet";
  return etat === "fresh" ? "frais" : "pourri";
}
