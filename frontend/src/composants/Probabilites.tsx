import { libelleClasse, pourcent } from "../lib/libelles";

export function Probabilites({ probabilites, mise_en_avant }: { probabilites: Record<string, number>; mise_en_avant?: string | null }) {
  const lignes = Object.entries(probabilites).sort((a, b) => b[1] - a[1]);
  return (
    <table className="w-full text-sm">
      <caption className="sr-only">Probabilités des 6 classes</caption>
      <tbody>
        {lignes.map(([classe, p]) => {
          const frais = classe.endsWith("fresh");
          return (
            <tr key={classe} className={classe === mise_en_avant ? "font-semibold" : ""}>
              <th scope="row" className="w-36 py-1 pr-3 text-left font-normal text-slate-700 dark:text-slate-300">
                {libelleClasse(classe)}
              </th>
              <td className="py-1">
                <div className="h-2 rounded-full bg-slate-100 dark:bg-slate-800" aria-hidden="true">
                  <div
                    className={`h-full rounded-full ${frais ? "bg-frais-500" : "bg-pourri-500"}`}
                    style={{ width: `${Math.max(p * 100, 0.5)}%` }}
                  />
                </div>
              </td>
              <td className="w-20 py-1 pl-3 text-right tabular-nums">{pourcent(p)}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
