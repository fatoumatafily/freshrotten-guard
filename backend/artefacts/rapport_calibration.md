# Rapport de calibration des seuils hors domaine

Généré le 2026-11-21 01:00 par `scripts/calibrer_seuils.py`. Seuils choisis sur la moitié A du test, évalués sur la moitié B (jamais vue).

Images valides : {"train_gardien": 1500, "test_A": 1349, "test_B": 1349}. Taux de faux rejets visés : {"gardien": 0.02, "incertitude": 0.005, "autre_fruit": 0.005, "qualite": 0.0025}.

## Seuils retenus

| Seuil | Valeur |
|---|---|
| `luminosite_min` | 0.12 |
| `luminosite_max` | 0.97 |
| `contraste_min` | 0.04 |
| `nettete_min` | 4.861 |
| `distance_max` | 1035 |
| `autre_fruit_min` | 0.7803 |
| `divergence_manipulation` | 0.809 |
| `base.confiance_min` | 0.8524 |
| `base.entropie_max` | 0.4203 |
| `base.energie_max` | -5.503 |
| `robuste.confiance_min` | 0.418 |
| `robuste.entropie_max` | 1.177 |
| `robuste.energie_max` | -2.723 |

Le gardien identifie le bon fruit dans **99.7%** des images valides (moitié B). Faux positifs du détecteur de visages sur fruits : 0.74%.

## Modèle robuste

* **Taux de faux rejets** (images valides rejetées) : **8.2%**
  * dont images que le modèle classait **correctement** : 5.8% ; **erreurs du modèle interceptées** : 71.4%
* Précision sans filtre : 96.4% — sur les images acceptées : 98.9%

| Jeu d'images invalides | n | Fausses acceptations | Raison principale du rejet |
|---|---|---|---|
| synthetiques | 29 | **0.0%** | hors_domaine |
| cifar_personnes | 200 | **0.0%** | trop_floue |
| cifar_animaux | 200 | **0.0%** | trop_floue |
| cifar_vehicules | 200 | **0.0%** | trop_floue |
| cifar_autres_fruits_legumes | 200 | **0.0%** | trop_floue |
| cifar_objets_scenes | 200 | **0.0%** | trop_floue |

Taux de rejet par couche (seule) :

| Couche | Valides (faux rejets) | synthetiques | cifar_personnes | cifar_animaux | cifar_vehicules | cifar_autres_fruits_legumes | cifar_objets_scenes |
|---|---|---|---|---|---|---|---|
| luminosite_min | 0.2% | 3.4% | 0.5% | 0.0% | 0.0% | 0.0% | 0.5% |
| luminosite_max | 0.0% | 3.4% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| contraste | 0.0% | 13.8% | 0.0% | 0.0% | 0.0% | 0.5% | 0.0% |
| nettete | 0.7% | 13.8% | 100.0% | 97.5% | 97.0% | 99.0% | 96.5% |
| couleurs | 0.0% | 27.6% | 3.0% | 0.5% | 4.5% | 0.5% | 3.5% |
| personne | 0.7% | 0.0% | 37.0% | 3.5% | 3.0% | 2.0% | 0.5% |
| gardien_distance | 2.4% | 89.7% | 100.0% | 100.0% | 100.0% | 85.5% | 98.0% |
| autre_fruit | 0.5% | 0.0% | 0.0% | 0.0% | 0.0% | 2.0% | 0.0% |
| confiance | 0.5% | 0.0% | 2.0% | 3.0% | 0.0% | 7.5% | 2.0% |
| entropie | 0.4% | 0.0% | 3.5% | 3.5% | 1.0% | 11.5% | 3.0% |
| energie | 0.5% | 6.9% | 8.0% | 12.5% | 6.5% | 28.5% | 7.5% |
| coherence | 2.8% | 44.8% | 48.0% | 36.5% | 32.5% | 50.0% | 46.0% |

## Modèle base

* **Taux de faux rejets** (images valides rejetées) : **6.4%**
  * dont images que le modèle classait **correctement** : 6.0% ; **erreurs du modèle interceptées** : 100.0%
* Précision sans filtre : 99.6% — sur les images acceptées : 100.0%

| Jeu d'images invalides | n | Fausses acceptations | Raison principale du rejet |
|---|---|---|---|
| synthetiques | 29 | **0.0%** | hors_domaine |
| cifar_personnes | 200 | **0.0%** | trop_floue |
| cifar_animaux | 200 | **0.0%** | trop_floue |
| cifar_vehicules | 200 | **0.0%** | trop_floue |
| cifar_autres_fruits_legumes | 200 | **0.0%** | trop_floue |
| cifar_objets_scenes | 200 | **0.0%** | trop_floue |

Taux de rejet par couche (seule) :

| Couche | Valides (faux rejets) | synthetiques | cifar_personnes | cifar_animaux | cifar_vehicules | cifar_autres_fruits_legumes | cifar_objets_scenes |
|---|---|---|---|---|---|---|---|
| luminosite_min | 0.2% | 3.4% | 0.5% | 0.0% | 0.0% | 0.0% | 0.5% |
| luminosite_max | 0.0% | 3.4% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| contraste | 0.0% | 13.8% | 0.0% | 0.0% | 0.0% | 0.5% | 0.0% |
| nettete | 0.7% | 13.8% | 100.0% | 97.5% | 97.0% | 99.0% | 96.5% |
| couleurs | 0.0% | 27.6% | 3.0% | 0.5% | 4.5% | 0.5% | 3.5% |
| personne | 0.7% | 0.0% | 37.0% | 3.5% | 3.0% | 2.0% | 0.5% |
| gardien_distance | 2.4% | 89.7% | 100.0% | 100.0% | 100.0% | 85.5% | 98.0% |
| autre_fruit | 0.5% | 0.0% | 0.0% | 0.0% | 0.0% | 2.0% | 0.0% |
| confiance | 1.1% | 10.3% | 39.0% | 49.0% | 33.0% | 31.0% | 40.5% |
| entropie | 1.2% | 10.3% | 45.5% | 51.0% | 38.0% | 34.0% | 41.5% |
| energie | 0.8% | 13.8% | 62.0% | 66.5% | 56.5% | 53.0% | 64.5% |
| coherence | 0.3% | 44.8% | 56.5% | 46.5% | 39.0% | 53.5% | 48.0% |

## Limites

* Les images CIFAR-100 font 32×32 pixels (agrandies) : elles sont floues, la couche « netteté » en rejette une partie. Ajoutez de vraies photos dans `tests/data/reelles/<categorie>/` puis relancez.
* Le dataset a des fonds assez homogènes : une photo de fruit très différente (fond chargé, plusieurs fruits) peut être rejetée par prudence (faux rejet) plutôt que mal classée.
