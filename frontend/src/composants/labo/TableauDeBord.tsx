// Tableau de bord des métriques (resultats.json, robustesse naturelle, calibration), recréé en interactif.
import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../../api/client";
import type { Metriques } from "../../api/types";
import { pourcent } from "../../lib/libelles";
import { SERIES, type Theme } from "../../lib/theme";
import { Carte, MessageErreur, Squelette } from "../Messages";

const fmtPct = (v: number) => `${Math.round(v * 100)} %`;

export function TableauDeBord({ theme }: { theme: Theme }) {
  const [m, setM] = useState<Metriques | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  useEffect(() => {
    api.metriques().then(setM, (e: Error) => setErreur(e.message));
  }, []);

  if (erreur) return <MessageErreur titre="Métriques indisponibles">{erreur}</MessageErreur>;
  if (!m?.entrainement) return <Squelette lignes={6} />;

  const c = SERIES[theme];
  const e = m.entrainement;
  const courbe = e.courbe_epsilon.eps.map((eps, i) => ({
    eps,
    base_fgsm: e.courbe_epsilon.base_fgsm[i],
    base_pgd: e.courbe_epsilon.base_pgd[i],
    robuste_fgsm: e.courbe_epsilon.defendu_fgsm[i],
    robuste_pgd: e.courbe_epsilon.defendu_pgd[i],
  }));
  const barres = [
    { nom: "Images propres", base: e.modele_base.accuracy_propre ?? 0, robuste: e.modele_defendu.accuracy_propre ?? 0 },
    { nom: "FGSM ε=0,03", base: e.modele_base.accuracy_fgsm ?? 0, robuste: e.modele_defendu.accuracy_fgsm ?? 0 },
    { nom: "PGD ε=0,03", base: e.modele_base.accuracy_pgd ?? 0, robuste: e.modele_defendu.accuracy_pgd ?? 0 },
    {
      nom: "Résistance à PGD ciblée",
      base: 1 - (e.modele_base.reussite_attaque_ciblee ?? 0),
      robuste: 1 - (e.modele_defendu.reussite_attaque_ciblee ?? 0),
    },
  ];
  const axe = { stroke: c.texte, fontSize: 12, tickLine: false };
  const infobulle = {
    contentStyle: {
      background: theme === "sombre" ? "#0f172a" : "#ffffff",
      border: `1px solid ${c.grille}`,
      borderRadius: 8,
      color: c.texte,
    },
    formatter: (v: number) => pourcent(v),
  };

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Tuile titre="Précision propre (robuste)" valeur={e.modele_defendu.accuracy_propre ?? 0} note={`base : ${pourcent(e.modele_base.accuracy_propre)}`} />
        <Tuile titre="Sous PGD ε=0,03 (robuste)" valeur={e.modele_defendu.accuracy_pgd ?? 0} note={`base : ${pourcent(e.modele_base.accuracy_pgd)}`} />
        <Tuile titre="Sous FGSM ε=0,03 (robuste)" valeur={e.modele_defendu.accuracy_fgsm ?? 0} note={`base : ${pourcent(e.modele_base.accuracy_fgsm)}`} />
        <Tuile
          titre="Réussite PGD ciblée (robuste)"
          valeur={e.modele_defendu.reussite_attaque_ciblee ?? 0}
          note={`base : ${pourcent(e.modele_base.reussite_attaque_ciblee)}`}
        />
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <Carte>
          <h3 className="font-semibold">Précision en fonction de ε</h3>
          <p className="mb-3 text-sm text-slate-600 dark:text-slate-400">Trait plein : FGSM, pointillés : PGD. Le modèle de base s'effondre dès ε = 0,01.</p>
          <div className="h-72">
            <ResponsiveContainer>
              <LineChart data={courbe} margin={{ top: 22, right: 16, bottom: 4, left: 0 }}>
                <CartesianGrid stroke={c.grille} vertical={false} />
                <XAxis dataKey="eps" {...axe} tickFormatter={(v: number) => v.toString().replace(".", ",")} />
                <YAxis {...axe} domain={[0, 1]} tickFormatter={fmtPct} width={48} />
                <Tooltip {...infobulle} labelFormatter={(v) => `ε = ${String(v).replace(".", ",")}`} />
                <Legend wrapperStyle={{ fontSize: 12, color: c.texte }} />
                <ReferenceLine x={0.03} stroke={c.texte} strokeDasharray="2 4" label={{ value: "ε entraînement", fill: c.texte, fontSize: 11, position: "top" }} />
                <Line dataKey="robuste_fgsm" name="Robuste, FGSM" stroke={c.robuste} strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 6 }} />
                <Line dataKey="robuste_pgd" name="Robuste, PGD" stroke={c.robuste} strokeWidth={2} strokeDasharray="6 4" dot={{ r: 4 }} activeDot={{ r: 6 }} />
                <Line dataKey="base_fgsm" name="Base, FGSM" stroke={c.base} strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 6 }} />
                <Line dataKey="base_pgd" name="Base, PGD" stroke={c.base} strokeWidth={2} strokeDasharray="6 4" dot={{ r: 4 }} activeDot={{ r: 6 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <TableDonnees
            titre="Données de la courbe"
            entetes={["ε", "Base FGSM", "Base PGD", "Robuste FGSM", "Robuste PGD"]}
            lignes={courbe.map((d) => [String(d.eps), d.base_fgsm, d.base_pgd, d.robuste_fgsm, d.robuste_pgd])}
          />
        </Carte>

        <Carte>
          <h3 className="font-semibold">Base vs robuste</h3>
          <p className="mb-3 text-sm text-slate-600 dark:text-slate-400">Le robuste perd 3,5 points sur images propres mais gagne 79 points sous PGD.</p>
          <div className="h-72">
            <ResponsiveContainer>
              <BarChart data={barres} margin={{ top: 8, right: 8, bottom: 4, left: 0 }} barGap={2}>
                <CartesianGrid stroke={c.grille} vertical={false} />
                <XAxis dataKey="nom" {...axe} interval={0} fontSize={11} />
                <YAxis {...axe} domain={[0, 1]} tickFormatter={fmtPct} width={48} />
                <Tooltip {...infobulle} cursor={{ fill: c.grille, opacity: 0.4 }} />
                <Legend wrapperStyle={{ fontSize: 12, color: c.texte }} />
                <Bar dataKey="base" name="Modèle de base" fill={c.base} radius={[4, 4, 0, 0]} maxBarSize={36} />
                <Bar dataKey="robuste" name="Modèle robuste" fill={c.robuste} radius={[4, 4, 0, 0]} maxBarSize={36} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <TableDonnees titre="Données des barres" entetes={["Mesure", "Base", "Robuste"]} lignes={barres.map((b) => [b.nom, b.base, b.robuste])} />
        </Carte>
      </div>

      {m.robustesse && <Robustesse m={m} theme={theme} />}
      {m.calibration && <Calibration calibration={m.calibration} />}
    </div>
  );
}

function Robustesse({ m, theme }: { m: Metriques; theme: Theme }) {
  const r = m.robustesse;
  if (!r) return null;
  const c = SERIES[theme];
  const donnees = Object.values(r.transformations).map((t) => ({ nom: t.titre, base: t.base, robuste: t.robuste }));
  return (
    <div className="grid gap-6 xl:grid-cols-2">
      <Carte>
        <h3 className="font-semibold">Robustesse naturelle</h3>
        <p className="mb-3 text-sm text-slate-600 dark:text-slate-400">
          Précision (sans filtre hors domaine) sur {r.n_images} images de test transformées.
        </p>
        <div className="h-80">
          <ResponsiveContainer>
            <BarChart data={donnees} layout="vertical" margin={{ top: 0, right: 16, bottom: 0, left: 8 }} barGap={2}>
              <CartesianGrid stroke={c.grille} horizontal={false} />
              <XAxis type="number" domain={[0, 1]} tickFormatter={fmtPct} stroke={c.texte} fontSize={12} />
              <YAxis type="category" dataKey="nom" width={150} stroke={c.texte} fontSize={11} tickLine={false} />
              <Tooltip formatter={(v: number) => pourcent(v)} cursor={{ fill: c.grille, opacity: 0.4 }} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="base" name="Modèle de base" fill={c.base} radius={[0, 4, 4, 0]} maxBarSize={14} />
              <Bar dataKey="robuste" name="Modèle robuste" fill={c.robuste} radius={[0, 4, 4, 0]} maxBarSize={14} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Carte>
      <Carte>
        <h3 className="font-semibold">Coût et effet de la purification d'entrée</h3>
        <p className="mb-3 text-sm text-slate-600 dark:text-slate-400">
          Précision sur images propres et sous PGD ε=0,03 (attaquant qui ignore la purification).
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left dark:border-slate-700">
                <th className="py-2 pr-3 font-medium">Purification</th>
                <th className="py-2 pr-3 text-right font-medium">Base propre</th>
                <th className="py-2 pr-3 text-right font-medium">Base PGD</th>
                <th className="py-2 pr-3 text-right font-medium">Robuste propre</th>
                <th className="py-2 text-right font-medium">Robuste PGD</th>
              </tr>
            </thead>
            <tbody className="tabular-nums">
              {Object.entries(r.purification).map(([k, p]) => (
                <tr key={k} className="border-b border-slate-100 dark:border-slate-800">
                  <th scope="row" className="py-2 pr-3 text-left font-normal">{p.titre}</th>
                  <td className="py-2 pr-3 text-right">{pourcent(p.propre_base)}</td>
                  <td className="py-2 pr-3 text-right">{pourcent(p.pgd_base)}</td>
                  <td className="py-2 pr-3 text-right">{pourcent(p.propre_robuste)}</td>
                  <td className="py-2 text-right">{pourcent(p.pgd_robuste)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Carte>
    </div>
  );
}

interface RapportModele {
  taux_faux_rejets: number;
  precision_sur_acceptes: number;
  precision_sans_filtre: number;
  negatifs: Record<string, { n: number; fausses_acceptations: number }>;
}

const LIBELLES_NEGATIFS: Record<string, string> = {
  synthetiques: "Images synthétiques (bruit, aplats, texte, dessins)",
  cifar_personnes: "Personnes (CIFAR-100)",
  cifar_animaux: "Animaux (CIFAR-100)",
  cifar_vehicules: "Véhicules (CIFAR-100)",
  cifar_autres_fruits_legumes: "Autres fruits et légumes (CIFAR-100)",
  cifar_objets_scenes: "Objets et scènes (CIFAR-100)",
};

function Calibration({ calibration }: { calibration: Record<string, unknown> }) {
  const modeles = calibration.modeles as Record<string, RapportModele> | undefined;
  const r = modeles?.robuste;
  if (!r) return null;
  return (
    <Carte>
      <h3 className="font-semibold">Détection hors domaine (calibration du {String(calibration.date)})</h3>
      <p className="mb-3 text-sm text-slate-600 dark:text-slate-400">
        Modèle robuste, seuils choisis sur une moitié du jeu de test, évalués sur l'autre moitié. Faux rejets d'images valides :{" "}
        <strong>{pourcent(r.taux_faux_rejets)}</strong>, précision sur les images acceptées : <strong>{pourcent(r.precision_sur_acceptes)}</strong>{" "}
        (sans filtre : {pourcent(r.precision_sans_filtre)}).
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-left dark:border-slate-700">
              <th className="py-2 pr-3 font-medium">Images invalides</th>
              <th className="py-2 pr-3 text-right font-medium">Nombre</th>
              <th className="py-2 text-right font-medium">Fausses acceptations</th>
            </tr>
          </thead>
          <tbody className="tabular-nums">
            {Object.entries(r.negatifs).map(([g, v]) => (
              <tr key={g} className="border-b border-slate-100 dark:border-slate-800">
                <th scope="row" className="py-2 pr-3 text-left font-normal">{LIBELLES_NEGATIFS[g] ?? g.replace(/_/g, " ")}</th>
                <td className="py-2 pr-3 text-right">{v.n}</td>
                <td className="py-2 text-right font-medium">{pourcent(v.fausses_acceptations)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Carte>
  );
}

function Tuile({ titre, valeur, note }: { titre: string; valeur: number; note: string }) {
  return (
    <Carte>
      <p className="text-sm text-slate-600 dark:text-slate-400">{titre}</p>
      <p className="mt-1 text-3xl font-bold tabular-nums">{pourcent(valeur)}</p>
      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{note}</p>
    </Carte>
  );
}

function TableDonnees({ titre, entetes, lignes }: { titre: string; entetes: string[]; lignes: (string | number | undefined)[][] }) {
  return (
    <details className="mt-3 text-sm">
      <summary className="cursor-pointer text-bouclier-600 hover:underline dark:text-bouclier-300">Voir le tableau ({titre.toLowerCase()})</summary>
      <div className="mt-2 overflow-x-auto">
        <table className="w-full tabular-nums">
          <thead>
            <tr className="border-b border-slate-200 dark:border-slate-700">
              {entetes.map((e) => (
                <th key={e} className="py-1 pr-3 text-left font-medium">{e}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {lignes.map((l, i) => (
              <tr key={i} className="border-b border-slate-100 dark:border-slate-800">
                {l.map((v, j) => (
                  <td key={j} className="py-1 pr-3">{typeof v === "number" ? pourcent(v) : v}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}
