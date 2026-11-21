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
  clair: { base: "#c2410c", robuste: "#4f46e5", grille: "#e2e8f0", texte: "#475569" },
  sombre: { base: "#ea580c", robuste: "#6366f1", grille: "#334155", texte: "#cbd5e1" },
};
