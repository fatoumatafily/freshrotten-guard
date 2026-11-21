# Rapport de la suite de tests de sécurité — FreshRotten Guard

Généré le 2026-11-21 01:08:50 par `make test-securite`. **50/50 scénarios réussis.**

## Hors domaine

| Scénario | Attendu | Obtenu | Résultat |
|---|---|---|---|
| Image noire | Rejet « aucun fruit pris en charge » | Rejet : Image trop sombre : éclairez davantage le fruit. | ✅ |
| Image blanche | Rejet « aucun fruit pris en charge » | Rejet : Image trop claire ou surexposée. | ✅ |
| Image grise uniforme | Rejet « aucun fruit pris en charge » | Rejet : Image presque uniforme : aucun objet visible. | ✅ |
| Aplat orange (couleur d'orange sans fruit) | Rejet « aucun fruit pris en charge » | Rejet : Image presque uniforme : aucun objet visible. | ✅ |
| Bruit aléatoire | Rejet « aucun fruit pris en charge » | Rejet : Ce n'est pas un fruit pris en charge (pomme, banane ou orange). | ✅ |
| Capture d'écran de texte | Rejet « aucun fruit pris en charge » | Rejet : Dessin ou image de synthèse détecté : seules les photos de fruits sont analysées. | ✅ |
| Dessin animé de banane | Rejet « aucun fruit pris en charge » | Rejet : Dessin ou image de synthèse détecté : seules les photos de fruits sont analysées. | ✅ |
| Dessin animé d'orange | Rejet « aucun fruit pris en charge » | Rejet : Dessin ou image de synthèse détecté : seules les photos de fruits sont analysées. | ✅ |
| Visage (schématique) | Rejet « aucun fruit pris en charge » | Rejet : Dessin ou image de synthèse détecté : seules les photos de fruits sont analysées. | ✅ |

## Fruits valides (contrôle)

| Scénario | Attendu | Obtenu | Résultat |
|---|---|---|---|
| Photo valide : apple_fresh | Accepté : apple_fresh | Accepté : apple_fresh (0.928) | ✅ |
| Photo valide : apple_rotten | Accepté : apple_rotten | Accepté : apple_rotten (0.955) | ✅ |
| Photo valide : banana_fresh | Accepté : banana_fresh | Accepté : banana_fresh (0.998) | ✅ |
| Photo valide : banana_rotten | Accepté : banana_rotten | Accepté : banana_rotten (1.0) | ✅ |
| Photo valide : orange_fresh | Accepté : orange_fresh | Accepté : orange_fresh (0.997) | ✅ |
| Photo valide : orange_rotten | Accepté : orange_rotten | Accepté : orange_rotten (0.706) | ✅ |

## Fichiers malveillants

| Scénario | Attendu | Obtenu | Résultat |
|---|---|---|---|
| Exécutable .exe renommé en .jpg | Refusé (executable) | Refusé (executable) : Fichier invalide : ce n'est pas une image. | ✅ |
| Script PHP renommé en .jpg | Refusé (script) | Refusé (script) : Fichier invalide : ce n'est pas une image. | ✅ |
| Page HTML renommée en .jpg | Refusé (script) | Refusé (script) : Fichier invalide : ce n'est pas une image. | ✅ |
| SVG contenant un script | Refusé (svg_refuse) | Refusé (svg_refuse) : Les images SVG ne sont pas acceptées. | ✅ |
| GIF animé | Refusé (gif_refuse) | Refusé (gif_refuse) : Les GIF ne sont pas acceptés (utilisez JPEG, PNG ou WebP). | ✅ |
| WebP animé | Refusé (image_animee) | Refusé (image_animee) : Les images animées ne sont pas acceptées. | ✅ |
| Bombe de décompression (50 000 × 50 000 px) | Refusé (bombe_decompression) | Refusé (bombe_decompression) : Image refusée : dimensions trop grandes. | ✅ |
| Polyglotte JPEG + ZIP | Refusé (polyglotte) | Refusé (polyglotte) : Fichier invalide : contenu suspect détecté dans l'image. | ✅ |
| Polyglotte JPEG + HTML | Refusé (polyglotte) | Refusé (polyglotte) : Fichier invalide : contenu suspect détecté dans l'image. | ✅ |
| PNG avec <script> dans les métadonnées | Refusé (polyglotte) | Refusé (polyglotte) : Fichier invalide : contenu suspect détecté dans l'image. | ✅ |
| JPEG tronqué | Refusé (fichier_corrompu) | Refusé (fichier_corrompu) : Fichier invalide ou corrompu. | ✅ |
| JPEG corrompu | Refusé (fichier_corrompu) | Refusé (fichier_corrompu) : Fichier invalide ou corrompu. | ✅ |

## Formats particuliers

| Scénario | Attendu | Obtenu | Résultat |
|---|---|---|---|
| Png transparent | Accepté, RGB 8 bits, métadonnées supprimées | Accepté, converti en RGB (transparence_aplatie_sur_blanc) | ✅ |
| Jpeg cmjn | Accepté, RGB 8 bits, métadonnées supprimées | Accepté, converti en RGB (cmjn_converti) | ✅ |
| Png gris | Accepté, RGB 8 bits, métadonnées supprimées | Accepté, converti en RGB (aucune alerte) | ✅ |
| Png 16 bits | Accepté, RGB 8 bits, métadonnées supprimées | Accepté, converti en RGB (profondeur_16_bits_convertie) | ✅ |
| Jpeg exif oriente | Accepté, RGB 8 bits, métadonnées supprimées | Accepté, converti en RGB (metadonnees_exif_supprimees, orientation_exif_appliquee) | ✅ |

## Attaques adversariales

| Scénario | Attendu | Obtenu | Résultat |
|---|---|---|---|
| PGD ε=0,03 contre le modèle de base | Le modèle de base est trompé | Trompé : prédit apple_rotten (1.00) | ✅ |
| PGD ε=0,03 contre le modèle robuste | Le modèle robuste résiste | Résiste : prédit apple_fresh (0.55) | ✅ |
| PGD ciblée : banane pourrie → « fraîche » (base) | Le modèle de base est trompé (cible atteinte) | Cible atteinte : prédit banana_fresh (0.51) | ✅ |
| PGD ciblée : banane pourrie → « fraîche » (robuste) | Le modèle robuste résiste (cible manquée) | Cible manquée : prédit banana_rotten (1.00) | ✅ |
| Détection d'une image adverse (base, PGD ε=0,03) | Image signalée (manipulée) ou rejetée | Signalée (ok, alertes : ['image_possiblement_manipulee']) | ✅ |
| Purification JPEG contre PGD ε=0,02 (base) | Trompé sans défense, prédiction correcte restaurée avec JPEG | Sans purification : apple_rotten → avec JPEG : apple_fresh (1.00) | ✅ |

## Manipulation des couleurs

| Scénario | Attendu | Obtenu | Résultat |
|---|---|---|---|
| Décalage de teinte : banane pourrie « rafraîchie » | Pas classée « fraîche » (pourrie ou rejet) | Accepté : banana_rotten (1.0) | ✅ |

## Robustesse naturelle

| Scénario | Attendu | Obtenu | Résultat |
|---|---|---|---|
| Miroir horizontal (orange pourrie) | Toujours « orange_rotten » | Accepté : orange_rotten (0.696) | ✅ |
| Rotation 20° (orange pourrie) | Toujours « orange_rotten » | Accepté : orange_rotten (0.532) | ✅ |
| Luminosité −35 % (orange pourrie) | Toujours « orange_rotten » | Accepté : orange_rotten (0.654) | ✅ |
| Contraste +50 % (orange pourrie) | Toujours « orange_rotten » | Accepté : orange_rotten (0.548) | ✅ |
| Flou gaussien r=2 (orange pourrie) | Toujours « orange_rotten » | Accepté : orange_rotten (0.707) | ✅ |
| Bruit gaussien σ=12 (orange pourrie) | Toujours « orange_rotten » | Accepté : orange_rotten (0.657) | ✅ |
| Compression JPEG forte (q=15) (orange pourrie) | Toujours « orange_rotten » | Accepté : orange_rotten (0.68) | ✅ |
| Recadrage 80 % centré (orange pourrie) | Toujours « orange_rotten » | Accepté : orange_rotten (0.796) | ✅ |

## Modèle et serveur

| Scénario | Attendu | Obtenu | Résultat |
|---|---|---|---|
| Extraction du modèle (fuite d'information) | Probabilités arrondies, aucun logit | Probabilités à 3 décimales max, logits exposés : non | ✅ |
| Fichier modèle altéré (1 octet) | Altération détectée | Empreinte modifiée détectée (b1792d6bc3c4…) | ✅ |
| Modèle piégé (couche Lambda = code arbitraire) | Chargement refusé | Chargement refusé (ValueError) | ✅ |
