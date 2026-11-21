// Types alignés sur les schémas Pydantic du backend (backend/app/api/schemas.py).

export type NomModele = "base" | "robuste";
export type NomClasse =
  | "apple_fresh"
  | "apple_rotten"
  | "banana_fresh"
  | "banana_rotten"
  | "orange_fresh"
  | "orange_rotten";
export type TypeAttaque = "fgsm" | "pgd" | "pgd_ciblee";
export type ModeAttaque = "boite_blanche" | "transfert";
export type Purification = "jpeg" | "bits" | "median";

export interface Controle {
  nom: string;
  reussi: boolean;
  valeur: number | null;
  seuil: number | null;
  message: string;
}

export interface ResultatAnalyse {
  statut: "ok" | "rejet";
  modele: NomModele;
  fruit: "apple" | "banana" | "orange" | null;
  etat: "fresh" | "rotten" | null;
  classe: NomClasse | null;
  confiance: number | null;
  probabilites: Record<string, number>;
  raison_rejet: string | null;
  code_rejet: string | null;
  alertes: string[];
  controles: Controle[];
  purification: Purification | null;
  duree_ms: number;
}

export interface ResultatComparaison {
  base: ResultatAnalyse;
  robuste: ResultatAnalyse;
}

export interface PredictionAttaque {
  classe: NomClasse;
  confiance: number;
  probabilites: Record<string, number>;
}

export interface ResultatModeleAttaque {
  propre: PredictionAttaque;
  attaquee: PredictionAttaque;
  trompe: boolean;
  cible_atteinte: boolean | null;
  manipulation_detectee: boolean;
  prediction_purifiee: PredictionAttaque;
  image_attaquee: string;
  perturbation: string;
  norme_linf: number;
}

export interface ResultatAttaque {
  attaque: TypeAttaque;
  epsilon: number;
  cible: NomClasse | null;
  mode: ModeAttaque;
  image_originale: string;
  modeles: Record<NomModele, ResultatModeleAttaque>;
  duree_ms: number;
}

export interface EtatSante {
  statut: "ok" | "degrade";
  modeles: Record<string, boolean>;
  modele_actif: NomModele;
  empreintes_verifiees: boolean;
  seuils_calibres: boolean;
  version: string;
}

export interface Scenario {
  id: string;
  categorie: string;
  titre: string;
  description: string;
  attendu: string;
  disponible: boolean;
}

export interface ResultatScenario {
  id: string;
  titre: string;
  attendu: string;
  obtenu: string;
  reussi: boolean;
  details: Record<string, unknown>;
  duree_ms: number;
}

export interface MetriquesEntrainement {
  eps: number;
  modele_base: Record<string, number>;
  modele_defendu: Record<string, number>;
  courbe_epsilon: {
    eps: number[];
    base_fgsm: number[];
    base_pgd: number[];
    defendu_fgsm: number[];
    defendu_pgd: number[];
  };
}

export interface Metriques {
  entrainement: MetriquesEntrainement | null;
  robustesse: Robustesse | null;
  calibration: Record<string, unknown> | null;
}

export interface Robustesse {
  date: string;
  n_images: number;
  transformations: Record<string, { titre: string; base: number; robuste: number }>;
  purification: Record<string, { titre: string; propre_base: number; propre_robuste: number; pgd_base: number; pgd_robuste: number }>;
}

export interface RapportSecurite {
  date: string;
  total: number;
  reussis: number;
  limites_connues?: number;
  resultats: {
    id: string;
    categorie: string;
    menace: string;
    attendu: string;
    obtenu: string;
    reussi: boolean;
    details: Record<string, unknown>;
  }[];
}
