"""Tests unitaires de la validation des fichiers (voir aussi tests/securite/)."""

import pytest
from app import cas_test
from app.securite_fichiers import FichierRefuse, detecter_format, valider_et_decoder

LIMITES = dict(taille_max=5 * 1024 * 1024, pixels_max=40_000_000, dimension_max=8000)


def valider(octets: bytes):
    return valider_et_decoder(octets, **LIMITES)


@pytest.mark.parametrize(
    ("nom", "code"),
    [
        ("faux_exe.jpg", "executable"),
        ("faux_php.jpg", "script"),
        ("faux_html.jpg", "script"),
        ("svg_script.svg", "svg_refuse"),
        ("gif_anime.gif", "gif_refuse"),
        ("webp_anime.webp", "image_animee"),
        ("bombe_decompression.png", "bombe_decompression"),
        ("polyglotte_jpeg_zip.jpg", "polyglotte"),
        ("polyglotte_jpeg_html.jpg", "polyglotte"),
        ("png_script_texte.png", "polyglotte"),
        ("jpeg_tronque.jpg", "fichier_corrompu"),
        ("jpeg_corrompu.jpg", "fichier_corrompu"),
    ],
)
def test_fichiers_pieges_refuses(nom, code):
    with pytest.raises(FichierRefuse) as exc:
        valider(cas_test.FICHIERS_PIEGES[nom]())
    assert exc.value.code == code


def test_vide_et_trop_gros():
    with pytest.raises(FichierRefuse, match="fichier_vide"):
        valider(b"")
    with pytest.raises(FichierRefuse, match="fichier_trop_gros"):
        valider(cas_test.gros_fichier(6 * 1024 * 1024))


def test_jpeg_valide_accepte_sans_metadonnees():
    res = valider(cas_test.jpeg_valide())
    assert res.format == "JPEG" and res.image.mode == "RGB"
    assert res.image.info == {}


@pytest.mark.parametrize("nom", list(cas_test.FICHIERS_PARTICULIERS))
def test_formats_particuliers_convertis_en_rgb(nom):
    res = valider(cas_test.FICHIERS_PARTICULIERS[nom]())
    assert res.image.mode == "RGB"
    assert not res.image.getexif()


def test_transparence_aplatie_sur_blanc():
    res = valider(cas_test.png_transparent())
    assert "transparence_aplatie_sur_blanc" in res.alertes
    assert res.image.getpixel((2, 2)) == (255, 255, 255)


def test_16_bits_ne_sature_pas():
    res = valider(cas_test.png_16_bits())
    assert "profondeur_16_bits_convertie" in res.alertes
    bas, haut = res.image.convert("L").getextrema()
    assert bas < 200, "l'image 16 bits ne doit pas devenir toute blanche"


def test_orientation_exif_appliquee():
    res = valider(cas_test.jpeg_exif_oriente())
    assert (res.largeur, res.hauteur) == (100, 200)
    assert "orientation_exif_appliquee" in res.alertes
    assert "metadonnees_exif_supprimees" in res.alertes


def test_detection_format_par_octets_magiques():
    assert detecter_format(cas_test.jpeg_valide()) == "JPEG"
    assert detecter_format(cas_test.png_gris()) == "PNG"
    assert detecter_format(cas_test.faux_exe()) is None
