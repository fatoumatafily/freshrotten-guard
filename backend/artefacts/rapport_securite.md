# Rapport de la suite de tests de sécurité — FreshRotten Guard

Généré le 2026-11-21 10:50:21 par `make test-securite`. **75/75 scénarios réussis.**

## Serveur web et API

| Scénario | Attendu | Obtenu | Résultat |
|---|---|---|---|
| En-têtes de sécurité HTTP | CSP, nosniff, frame-ancestors, Referrer/Permissions-Policy | Tous les en-têtes présents, en-tête Server masqué | ✅ |
| CORS : origine non autorisée | Aucun en-tête Access-Control-Allow-Origin | Origine pirate refusée, origine du frontend autorisée | ✅ |
| Corps de requête de 20 Mo | 413 avant traitement | HTTP 413 : Requête trop volumineuse. | ✅ |
| Fichier de 5,5 Mo (limite 5 Mo) | 400 fichier_trop_gros | HTTP 413 : requete_trop_grosse | ✅ |
| Upload de 4 Mo (au-delà du seuil de mise sur disque par défaut de Starlette) | Aucun basculement sur disque | Traitement entièrement en mémoire (0 basculement sur disque) | ✅ |
| Rafale de 13 requêtes /api/attaque en 1 minute (limite 12) | 429 à partir de la 13e | Codes : 12 × 200 puis 429 | ✅ |
| Endpoints d'attaque plus limités que l'analyse | limite attaque < limite analyse | attaque 12/minute, comparer 60/minute, analyse 240/minute | ✅ |
| Messages d'erreur sans détail interne | Aucune trace, aucun écho des entrées | 404 → « Ressource introuvable. », 422 → « Paramètres invalides. » | ✅ |
| Exception interne | 500 générique, pile d'appels seulement dans les logs | HTTP 500 : Erreur interne du serveur. | ✅ |
| Journalisation des rejets | Événement JSON, IP hachée, ni image ni nom de fichier | Journal : {"horodatage": "2026-11-21T10:50:09+00:00", "evenement": "rejet_fichier", "ip_hachee": "6739a3c3b736754e", "code": "script", "taille": 34} | ✅ |
| Déni de service : file d'inférence saturée / inférence trop longue | 503 immédiat | File pleine → serveur_occupe, délai dépassé → delai_depasse | ✅ |
| Documentation API (Swagger) | Schéma OpenAPI disponible et validé | 10 routes documentées | ✅ |

## Fichiers malveillants

| Scénario | Attendu | Obtenu | Résultat |
|---|---|---|---|
| Exécutable envoyé avec Content-Type image/jpeg | 400 executable | HTTP 400 : Fichier invalide : ce n'est pas une image. | ✅ |
| Nom de fichier malveillant « ../../etc/passwd » | Nom ignoré, jamais renvoyé | Analyse normale, nom absent de la réponse, aucun fichier créé | ✅ |
| Nom de fichier malveillant « <script>alert(1)</script>.png » | Nom ignoré, jamais renvoyé | Analyse normale, nom absent de la réponse, aucun fichier créé | ✅ |
| Nom de fichier malveillant « ..\..\win.ini » | Nom ignoré, jamais renvoyé | Analyse normale, nom absent de la réponse, aucun fichier créé | ✅ |
| Nom de fichier malveillant « aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa » | Nom ignoré, jamais renvoyé | Analyse normale, nom absent de la réponse, aucun fichier créé | ✅ |
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

## Modèle et serveur

| Scénario | Attendu | Obtenu | Résultat |
|---|---|---|---|
| Démarrage avec un fichier .keras altéré | Refus de charger (IntegriteCompromise) | Refusé : Empreinte invalide pour FreshRotten_model.keras : attendue 219baea2f4b… | ✅ |
| Extraction du modèle (fuite d'information) | Probabilités arrondies, aucun logit | Probabilités à 3 décimales max, logits exposés : non | ✅ |
| Fichier modèle altéré (1 octet) | Altération détectée | Empreinte modifiée détectée (b1792d6bc3c4…) | ✅ |
| Modèle piégé (couche Lambda = code arbitraire) | Chargement refusé | Chargement refusé (ValueError) | ✅ |

## Authentification

| Scénario | Attendu | Obtenu | Résultat |
|---|---|---|---|
| Accès aux routes sans être connecté | 401 sur toutes les routes protégées | 6 routes → 401 ; /api/sante reste publique | ✅ |
| Mauvais mot de passe / identifiant inconnu | Même message générique (pas d'énumération) | 401 : « Identifiant ou mot de passe incorrect. » dans les deux cas | ✅ |
| Force brute : 6 tentatives en 1 minute | 429 à la 6e tentative | Codes : [401, 401, 401, 401, 401, 429] | ✅ |
| Jeton falsifié (identité modifiée, signature conservée) | 401 | Signature invalide → 401 ; jeton mal formé → 401 | ✅ |
| Jeton expiré | 401 | Refusé après 8 h, accepté avant | ✅ |
| Stockage et journalisation des mots de passe | Empreinte scrypt salée ; jamais en clair | Sel aléatoire (2 empreintes différentes), mot de passe absent des journaux | ✅ |
| Connexion avec le bon mot de passe | Jeton valable, accès aux routes | Jeton émis, expiration dans 8 h | ✅ |

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
| Photo valide : apple_fresh | Accepté : apple_fresh | Accepté : apple_fresh (0.999) | ✅ |
| Photo valide : apple_rotten | Accepté : apple_rotten | Accepté : apple_rotten (0.949) | ✅ |
| Photo valide : banana_fresh | Accepté : banana_fresh | Accepté : banana_fresh (1.0) | ✅ |
| Photo valide : banana_rotten | Accepté : banana_rotten | Accepté : banana_rotten (1.0) | ✅ |
| Photo valide : orange_fresh | Accepté : orange_fresh | Accepté : orange_fresh (0.999) | ✅ |
| Photo valide : orange_rotten | Accepté : orange_rotten | Accepté : orange_rotten (1.0) | ✅ |

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
| PGD ε=0,03 contre le modèle robuste | Le modèle robuste résiste | Résiste : prédit apple_fresh (0.99) | ✅ |
| PGD ciblée : banane pourrie → « fraîche » (base) | Le modèle de base est trompé (cible atteinte) | Cible atteinte : prédit banana_fresh (0.86) | ✅ |
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
| Miroir horizontal (orange pourrie) | Toujours « orange_rotten » | Accepté : orange_rotten (1.0) | ✅ |
| Rotation 20° (orange pourrie) | Toujours « orange_rotten » | Accepté : orange_rotten (1.0) | ✅ |
| Luminosité −35 % (orange pourrie) | Toujours « orange_rotten » | Accepté : orange_rotten (0.915) | ✅ |
| Contraste +50 % (orange pourrie) | Toujours « orange_rotten » | Accepté : orange_rotten (1.0) | ✅ |
| Flou gaussien r=2 (orange pourrie) | Toujours « orange_rotten » | Accepté : orange_rotten (1.0) | ✅ |
| Bruit gaussien σ=12 (orange pourrie) | Toujours « orange_rotten » | Accepté : orange_rotten (1.0) | ✅ |
| Compression JPEG forte (q=15) (orange pourrie) | Toujours « orange_rotten » | Accepté : orange_rotten (1.0) | ✅ |
| Recadrage 80 % centré (orange pourrie) | Toujours « orange_rotten » | Accepté : orange_rotten (1.0) | ✅ |
