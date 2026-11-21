// Zone de glisser-déposer accessible au clavier, avec aperçu.
import { ImageIcon, Upload } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";
import { verifierFichier } from "../lib/fichiers";

interface Props {
  fichier: File | null;
  onChange: (f: File | null) => void;
  libelle?: string;
}

export function ZoneDepot({ fichier, onChange, libelle = "Déposez une image de fruit" }: Props) {
  const [survol, setSurvol] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);
  const [apercu, setApercu] = useState<string | null>(null);
  const entree = useRef<HTMLInputElement>(null);
  const idAide = useId();

  useEffect(() => {
    if (!fichier) {
      setApercu(null);
      return;
    }
    const url = URL.createObjectURL(fichier);
    setApercu(url);
    return () => URL.revokeObjectURL(url);
  }, [fichier]);

  const choisir = (f: File | undefined) => {
    if (!f) return;
    const e = verifierFichier(f);
    setErreur(e);
    onChange(e ? null : f);
  };

  return (
    <div>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setSurvol(true);
        }}
        onDragLeave={() => setSurvol(false)}
        onDrop={(e) => {
          e.preventDefault();
          setSurvol(false);
          choisir(e.dataTransfer.files[0]);
        }}
        className={`relative flex min-h-56 flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed p-6 text-center transition-colors ${
          survol
            ? "border-frais-500 bg-frais-50 dark:bg-frais-900/20"
            : "border-slate-300 bg-white hover:border-slate-400 dark:border-slate-700 dark:bg-slate-900"
        }`}
      >
        {apercu ? (
          <img src={apercu} alt="Aperçu de l'image sélectionnée" className="max-h-64 rounded-lg object-contain shadow-sm" />
        ) : (
          <>
            <ImageIcon size={40} className="text-slate-400" aria-hidden="true" />
            <p className="font-medium">{libelle}</p>
          </>
        )}
        <button
          type="button"
          onClick={() => entree.current?.click()}
          className="inline-flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bouclier-500 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white"
          aria-describedby={idAide}
        >
          <Upload size={16} aria-hidden="true" />
          {fichier ? "Changer d'image" : "Choisir un fichier"}
        </button>
        <p id={idAide} className="text-xs text-slate-500 dark:text-slate-400">
          JPEG, PNG ou WebP · 5 Mo maximum · glisser-déposer accepté
        </p>
        <input
          ref={entree}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          className="sr-only"
          tabIndex={-1}
          aria-hidden="true"
          onChange={(e) => {
            choisir(e.target.files?.[0]);
            e.target.value = "";
          }}
        />
      </div>
      {erreur && (
        <p role="alert" className="mt-2 text-sm font-medium text-pourri-700 dark:text-pourri-300">
          {erreur}
        </p>
      )}
    </div>
  );
}
