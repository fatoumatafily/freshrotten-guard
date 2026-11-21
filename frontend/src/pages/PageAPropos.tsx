// Page « À propos » : fonctionnement, limites, confidentialité.
import { Carte } from "../composants/Messages";

export function PageAPropos() {
  return (
    <div className="mx-auto max-w-3xl space-y-5 leading-relaxed">
      <Carte>
        <h2 className="text-xl font-bold">Comment ça marche ?</h2>
        <ol className="mt-3 list-decimal space-y-2 pl-5">
          <li>
            <strong>Validation du fichier</strong> : octets magiques, décodage réel, dimensions (bombe de décompression), refus des
            SVG, GIF, images animées et polyglottes, suppression des métadonnées.
          </li>
          <li>
            <strong>Contrôles de qualité</strong> : image trop sombre, trop claire, uniforme ou floue.
          </li>
          <li>
            <strong>Gardien sémantique</strong> : un réseau MobileNetV2 pré-entraîné sur ImageNet vérifie que l'image ressemble aux
            pommes, bananes et oranges du jeu d'entraînement, et qu'aucune personne n'est détectée.
          </li>
          <li>
            <strong>Classification</strong> par un réseau convolutif entraîné de façon adversariale (96,2 % de précision, 79,6 %
            sous attaque PGD).
          </li>
          <li>
            <strong>Incertitude et cohérence</strong> : confiance, entropie, score d'énergie, et accord entre le gardien et le
            modèle sur le fruit vu.
          </li>
        </ol>
      </Carte>
      <Carte>
        <h2 className="text-xl font-bold">Pourquoi tant de défenses ?</h2>
        <p className="mt-2">
          Un classifieur à 6 classes répond <em>toujours</em> l'une d'elles. Sans protection, une image de bruit est classée
          « banane pourrie » à 100 %. Chaque couche couvre les angles morts des autres. Le détail des menaces et des tests est dans{" "}
          <code>SECURITY.md</code>.
        </p>
      </Carte>
      <Carte>
        <h2 className="text-xl font-bold">Limites connues</h2>
        <ul className="mt-2 list-disc space-y-1 pl-5">
          <li>Seules les pommes, bananes et oranges sont prises en charge ; un fruit très proche (mandarine, pomme rouge très atypique) peut être refusé.</li>
          <li>Les photos du jeu d'entraînement ont des fonds assez uniformes : une photo très différente peut être rejetée par prudence.</li>
          <li>Plusieurs fruits sur la même image donnent un résultat peu fiable.</li>
          <li>Un attaquant qui connaît les défenses peut adapter son attaque (attaque adaptative) ; la robustesse n'est jamais absolue.</li>
          <li>Les attaques physiques (autocollant coloré, photo affichée sur un écran) ne sont que partiellement couvertes.</li>
        </ul>
      </Carte>
      <Carte>
        <h2 className="text-xl font-bold">Confidentialité</h2>
        <p className="mt-2">
          Les images (upload et webcam) sont traitées <strong>uniquement en mémoire</strong> et oubliées aussitôt : aucune image
          n'est écrite sur le disque, ni conservée dans les journaux. Les journaux de sécurité ne contiennent que le type
          d'événement, l'horodatage et une empreinte (hachage salé) de l'adresse IP. La caméra ne s'active qu'après votre clic.
        </p>
      </Carte>
    </div>
  );
}
