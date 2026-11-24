// Thème clair / sombre : classe « dark » sur <html>, choix mémorisé (préférence locale uniquement).
import { useCallback, useEffect, useState } from "react";

export type Theme = "clair" | "sombre";

function lireTheme(): Theme {
  return document.documentElement.classList.contains("dark") ? "sombre" : "clair";
}

export function useTheme(): [Theme, () => void] {
  const [theme, setTheme] = useState<Theme>(lireTheme);
  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "sombre");
    try {
      localStorage.setItem("frg-theme", theme === "sombre" ? "dark" : "light");
    } catch {
      /* stockage indisponible : sans conséquence */
    }
  }, [theme]);
  const basculer = useCallback(() => setTheme((t) => (t === "sombre" ? "clair" : "sombre")), []);
  return [theme, basculer];
}

/** Couleurs des séries de graphiques, validées (daltonisme, contraste) pour chaque thème. */
export const SERIES: Record<Theme, { base: string; robuste: string; grille: string; texte: string }> = {
  // Robuste = vert foncé, base = ambre clair : écart de clarté net (lisible en daltonisme et en niveaux de gris).
  clair: { base: "#d4892f", robuste: "#2f6f2a", grille: "#e3e6de", texte: "#474d42" },
  sombre: { base: "#e0a052", robuste: "#8cc47e", grille: "#3b4036", texte: "#c3c8bb" },
};
