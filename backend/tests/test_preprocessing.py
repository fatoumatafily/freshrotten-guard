"""Le prétraitement central doit être strictement identique à celui de l'entraînement."""

import io

import numpy as np
from app.attaques import module_origine
from app.cas_test import dessin_orange, image_bruit
from app.preprocessing import tenseur_vers_image, vers_tenseur_gardien, vers_tenseur_modele
from PIL import Image


def _png(img: Image.Image) -> bytes:
    t = io.BytesIO()
    img.save(t, format="PNG")
    return t.getvalue()


def test_identique_a_charger_image_d_origine():
    for img in (image_bruit(300), dessin_orange(431), image_bruit(97).convert("L")):
        attendu = module_origine().charger_image(io.BytesIO(_png(img)))
        obtenu = vers_tenseur_modele(Image.open(io.BytesIO(_png(img))))
        assert obtenu.shape == (1, 128, 128, 3)
        assert obtenu.dtype == np.float32
        np.testing.assert_array_equal(obtenu, attendu)


def test_plage_et_forme_gardien():
    x = vers_tenseur_gardien(image_bruit(50))
    assert x.shape == (1, 224, 224, 3)
    assert x.min() >= -1.0 and x.max() <= 1.0


def test_aller_retour_sans_perte():
    x = vers_tenseur_modele(image_bruit(128))
    np.testing.assert_array_equal(vers_tenseur_modele(tenseur_vers_image(x)), x)
