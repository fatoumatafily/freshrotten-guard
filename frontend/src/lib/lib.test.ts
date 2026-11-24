import type { ResultatAnalyse } from "../api/types";
import { verifierFichier, TAILLE_MAX_OCTETS } from "./fichiers";
import { libelleClasse, pourcent, typeVerdict } from "./libelles";
import { lisser } from "./lissage";

function resultat(partiel: Partial<ResultatAnalyse>): ResultatAnalyse {
  return {
    statut: "ok",
    modele: "robuste",
    fruit: null,
    etat: null,
    classe: null,
    confiance: null,
    probabilites: {},
    raison_rejet: null,
    code_rejet: null,
    alertes: [],
    controles: [],
    purification: null,
    duree_ms: 1,
    ...partiel,
  };
}

describe("libellés", () => {
  it("accorde le fruit et l'état en français", () => {
    expect(libelleClasse("apple_fresh")).toBe("Pomme fraîche");
    expect(libelleClasse("banana_rotten")).toBe("Banane pourrie");
  });

  it("formate les pourcentages à la française", () => {
    expect(pourcent(0.9621)).toBe("96,2 %");
    expect(pourcent(null)).toBe("—");
    expect(pourcent(Number.NaN)).toBe("—");
  });

  it("déduit le type de verdict", () => {
    expect(typeVerdict("rejet", "fresh")).toBe("rejet");
    expect(typeVerdict("ok", "fresh")).toBe("frais");
    expect(typeVerdict("ok", "rotten")).toBe("pourri");
  });
});

describe("lissage webcam", () => {
  it("renvoie null sans historique", () => {
    expect(lisser([])).toBeNull();
  });

  it("garde la classe majoritaire malgré une réponse isolée", () => {
    const h = [
      resultat({ classe: "banana_fresh", confiance: 0.9 }),
      resultat({ classe: "banana_fresh", confiance: 0.8 }),
      resultat({ classe: "apple_rotten", confiance: 0.7 }),
    ];
    const v = lisser(h);
    expect(v?.cle).toBe("banana_fresh");
    expect(v?.part).toBeCloseTo(2 / 3);
    expect(v?.confiance).toBeCloseTo(0.85);
    expect(v?.dernier).toBe(h[2]);
  });

  it("regroupe les rejets avec une confiance nulle", () => {
    const v = lisser([resultat({ statut: "rejet" }), resultat({ statut: "rejet" })]);
    expect(v?.cle).toBe("rejet");
    expect(v?.confiance).toBe(0);
  });
});

describe("contrôle des fichiers côté navigateur", () => {
  const fichier = (taille: number, type: string) => {
    const f = new File(["x"], "image", { type });
    Object.defineProperty(f, "size", { value: taille });
    return f;
  };

  it("accepte JPEG, PNG et WebP", () => {
    expect(verifierFichier(fichier(1000, "image/jpeg"))).toBeNull();
    expect(verifierFichier(fichier(1000, "image/webp"))).toBeNull();
  });

  it("refuse les fichiers vides, trop gros ou d'un autre format", () => {
    expect(verifierFichier(fichier(0, "image/png"))).toMatch(/vide/);
    expect(verifierFichier(fichier(TAILLE_MAX_OCTETS + 1, "image/png"))).toMatch(/volumineux/);
    expect(verifierFichier(fichier(1000, "image/gif"))).toMatch(/Format/);
  });
});
