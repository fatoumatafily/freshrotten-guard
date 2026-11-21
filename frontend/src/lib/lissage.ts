// Lissage des prédictions webcam : vote majoritaire pondéré par la confiance
// sur les N dernières réponses, pour éviter le clignotement du verdict.
import type { ResultatAnalyse } from "../api/types";

export interface Verdict {
  cle: string; // classe (ex. "banana_fresh") ou "rejet"
  confiance: number; // confiance moyenne des votes gagnants (0 si rejet)
  part: number; // proportion des votes en faveur du gagnant
  dernier: ResultatAnalyse;
}

export function lisser(historique: ResultatAnalyse[]): Verdict | null {
  const dernier = historique.at(-1);
  if (!dernier) return null;
  const poids = new Map<string, { total: number; conf: number; n: number }>();
  for (const r of historique) {
    const cle = r.statut === "ok" && r.classe ? r.classe : "rejet";
    const w = r.statut === "ok" ? Math.max(r.confiance ?? 0, 0.05) : 0.6;
    const p = poids.get(cle) ?? { total: 0, conf: 0, n: 0 };
    p.total += w;
    p.conf += r.confiance ?? 0;
    p.n += 1;
    poids.set(cle, p);
  }
  let meilleur: [string, { total: number; conf: number; n: number }] | null = null;
  for (const e of poids) if (!meilleur || e[1].total > meilleur[1].total) meilleur = e;
  if (!meilleur) return null;
  const [cle, p] = meilleur;
  return {
    cle,
    confiance: cle === "rejet" ? 0 : p.conf / p.n,
    part: p.n / historique.length,
    dernier,
  };
}
