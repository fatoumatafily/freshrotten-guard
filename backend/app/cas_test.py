"""Génération (en mémoire) des cas de test de sécurité.

Utilisé par la suite ``tests/securite``, par la galerie « Scénarios d'attaque »
du Laboratoire et par ``scripts/generer_cas_test.py`` (qui les écrit dans
``tests/data/generes/`` pour inspection manuelle).

Note : les « charges utiles » sont volontairement **inertes** (``echo``,
``console.log``, en-tête ``MZ`` sans code). Elles testent exactement les mêmes
défenses — le serveur se fonde sur les octets magiques et les marqueurs, pas
sur la nocivité du contenu — sans déclencher l'antivirus du poste.
"""

from __future__ import annotations

import io
import struct
import zlib
from collections.abc import Callable

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, PngImagePlugin

_GRAINE = 1234


def _encoder(image: Image.Image, fmt: str = "PNG", **options: object) -> bytes:
    tampon = io.BytesIO()
    image.save(tampon, format=fmt, **options)
    return tampon.getvalue()


# ----------------------------------------------------------------- images
def image_uniforme(couleur: tuple[int, int, int], taille: int = 256) -> Image.Image:
    return Image.new("RGB", (taille, taille), couleur)


def image_bruit(taille: int = 256, graine: int = _GRAINE) -> Image.Image:
    rng = np.random.default_rng(graine)
    return Image.fromarray(rng.integers(0, 256, (taille, taille, 3), dtype=np.uint8), "RGB")


def image_texte(taille: int = 320) -> Image.Image:
    """Imitation de capture d'écran de texte."""
    img = Image.new("RGB", (taille, taille), (250, 250, 250))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, taille, 28], fill=(40, 60, 120))
    for ligne in range(13):
        d.text((12, 40 + ligne * 21), f"Ligne {ligne:02d} : lorem ipsum dolor sit amet", fill=(20, 20, 20))
    return img


def dessin_banane(taille: int = 320) -> Image.Image:
    """Dessin « cartoon » de banane : aplats de couleur et contour noir."""
    img = Image.new("RGB", (320, 320), (180, 220, 255))
    d = ImageDraw.Draw(img)
    d.chord([40, 40, 280, 280], start=20, end=160, fill=(255, 225, 40), outline=(0, 0, 0), width=6)
    d.chord([70, 40, 250, 200], start=20, end=160, fill=(180, 220, 255))
    d.rectangle([262, 120, 280, 140], fill=(90, 60, 20))
    return img if taille == 320 else img.resize((taille, taille), Image.BILINEAR)


def dessin_orange(taille: int = 320) -> Image.Image:
    """Dessin « cartoon » d'orange (aplat, contour noir, feuille)."""
    img = Image.new("RGB", (320, 320), (255, 255, 255))
    d = ImageDraw.Draw(img)
    d.ellipse([50, 60, 270, 280], fill=(255, 140, 0), outline=(0, 0, 0), width=6)
    d.polygon([(160, 60), (200, 20), (215, 45)], fill=(40, 160, 40), outline=(0, 0, 0))
    for x, y in [(120, 130), (180, 160), (140, 210)]:
        d.ellipse([x, y, x + 8, y + 8], fill=(230, 110, 0))
    return img if taille == 320 else img.resize((taille, taille), Image.BILINEAR)


def visage_schematique(taille: int = 320) -> Image.Image:
    """Visage simplifié : substitut quand aucune vraie photo n'est fournie dans tests/data/."""
    img = Image.new("RGB", (320, 320), (90, 110, 140))
    d = ImageDraw.Draw(img)
    d.ellipse([70, 40, 250, 270], fill=(224, 180, 150))
    d.ellipse([115, 120, 145, 140], fill=(255, 255, 255))
    d.ellipse([175, 120, 205, 140], fill=(255, 255, 255))
    d.ellipse([125, 124, 137, 136], fill=(40, 30, 20))
    d.ellipse([185, 124, 197, 136], fill=(40, 30, 20))
    d.polygon([(160, 150), (150, 190), (170, 190)], fill=(200, 150, 120))
    d.arc([125, 190, 195, 235], start=10, end=170, fill=(150, 50, 50), width=5)
    d.pieslice([60, 10, 260, 150], start=180, end=360, fill=(60, 40, 20))
    img = img.filter(ImageFilter.GaussianBlur(1))
    return img if taille == 320 else img.resize((taille, taille), Image.BILINEAR)


# ---------------------------------------------------------- fichiers piégés
def jpeg_valide(taille: int = 200) -> bytes:
    return _encoder(dessin_orange(taille), "JPEG", quality=90)


def faux_exe() -> bytes:
    """En-tête d'exécutable Windows (« MZ ») renommé en .jpg — aucun code."""
    return b"MZ" + bytes(126)


def faux_php() -> bytes:
    return b"<?php echo 'test FreshRotten'; ?>\n"


def faux_html() -> bytes:
    return b"<!DOCTYPE html><html><body><script>console.log('test')</script></body></html>"


def svg_script() -> bytes:
    return (
        b'<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">'
        b'<script>console.log(1)</script><circle cx="50" cy="50" r="40" fill="orange"/></svg>'
    )


def gif_anime() -> bytes:
    images = [image_uniforme(c, 64) for c in [(255, 0, 0), (0, 255, 0), (0, 0, 255)]]
    tampon = io.BytesIO()
    images[0].save(tampon, format="GIF", save_all=True, append_images=images[1:], duration=100, loop=0)
    return tampon.getvalue()


def webp_anime() -> bytes:
    images = [image_uniforme(c, 64) for c in [(255, 140, 0), (250, 220, 40)]]
    tampon = io.BytesIO()
    images[0].save(tampon, format="WEBP", save_all=True, append_images=images[1:], duration=100)
    return tampon.getvalue()


def _chunk_png(type_: bytes, donnees: bytes) -> bytes:
    return struct.pack(">I", len(donnees)) + type_ + donnees + struct.pack(">I", zlib.crc32(type_ + donnees))


def bombe_decompression(cote: int = 50_000) -> bytes:
    """Vrai PNG 1 bit de ``cote``×``cote`` pixels (2,5 milliards) ne pesant que quelques centaines de Ko."""
    octets_ligne = 1 + (cote + 7) // 8
    compresseur = zlib.compressobj(9)
    bloc = bytes(octets_ligne) * 1000
    morceaux = [compresseur.compress(bloc) for _ in range(cote // 1000)]
    morceaux.append(compresseur.flush())
    ihdr = struct.pack(">IIBBBBB", cote, cote, 1, 0, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk_png(b"IHDR", ihdr)
        + _chunk_png(b"IDAT", b"".join(morceaux))
        + _chunk_png(b"IEND", b"")
    )


def polyglotte_jpeg_zip() -> bytes:
    """JPEG valide suivi d'une archive ZIP vide (s'ouvre comme image ET comme archive)."""
    return jpeg_valide() + b"PK\x05\x06" + bytes(18)


def polyglotte_jpeg_html() -> bytes:
    return jpeg_valide() + b"<html><script>console.log('polyglotte')</script></html>"


def png_avec_script_dans_texte() -> bytes:
    """PNG valide dont un chunk tEXt contient une balise script."""
    meta = PngImagePlugin.PngInfo()
    meta.add_text("Comment", "<script>console.log('test')</script>")
    return _encoder(dessin_orange(128), "PNG", pnginfo=meta)


def jpeg_tronque() -> bytes:
    donnees = _encoder(image_bruit(256), "JPEG", quality=95)
    return donnees[: len(donnees) // 2]


def jpeg_corrompu() -> bytes:
    donnees = bytearray(_encoder(image_bruit(256), "JPEG", quality=95))
    rng = np.random.default_rng(_GRAINE)
    debut, fin = 600, len(donnees) - 2  # on garde le marqueur de fin FFD9 d'origine
    alea = rng.integers(0, 256, fin - debut, dtype=np.uint8).tobytes().replace(b"\xff\xd9", b"\xff\x00")
    donnees[debut:fin] = alea
    return bytes(donnees)


def png_transparent() -> bytes:
    img = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    ImageDraw.Draw(img).ellipse([30, 30, 170, 170], fill=(255, 140, 0, 255))
    return _encoder(img, "PNG")


def jpeg_cmjn() -> bytes:
    return _encoder(dessin_orange(200).convert("CMYK"), "JPEG", quality=90)


def png_gris() -> bytes:
    return _encoder(dessin_orange(200).convert("L"), "PNG")


def png_16_bits() -> bytes:
    gris = np.asarray(dessin_orange(200).convert("L"), dtype=np.uint16) * 257
    return _encoder(Image.fromarray(gris, mode="I;16"), "PNG")


def jpeg_exif_oriente() -> bytes:
    """JPEG 200×100 avec EXIF Orientation=6 (rotation 90°) et une balise fabricant."""
    img = Image.new("RGB", (200, 100), (255, 140, 0))
    exif = Image.Exif()
    exif[0x0112] = 6
    exif[0x010F] = "Fabricant-Test"
    return _encoder(img, "JPEG", exif=exif.tobytes(), quality=90)


def gros_fichier(octets: int) -> bytes:
    """JPEG valide suivi de rembourrage nul jusqu'à ``octets`` octets (dépasse la limite de taille)."""
    base = jpeg_valide()
    return base + bytes(max(0, octets - len(base)))


FICHIERS_PIEGES: dict[str, Callable[[], bytes]] = {
    "faux_exe.jpg": faux_exe,
    "faux_php.jpg": faux_php,
    "faux_html.jpg": faux_html,
    "svg_script.svg": svg_script,
    "gif_anime.gif": gif_anime,
    "webp_anime.webp": webp_anime,
    "bombe_decompression.png": bombe_decompression,
    "polyglotte_jpeg_zip.jpg": polyglotte_jpeg_zip,
    "polyglotte_jpeg_html.jpg": polyglotte_jpeg_html,
    "png_script_texte.png": png_avec_script_dans_texte,
    "jpeg_tronque.jpg": jpeg_tronque,
    "jpeg_corrompu.jpg": jpeg_corrompu,
}

FICHIERS_PARTICULIERS: dict[str, Callable[[], bytes]] = {
    "png_transparent.png": png_transparent,
    "jpeg_cmjn.jpg": jpeg_cmjn,
    "png_gris.png": png_gris,
    "png_16_bits.png": png_16_bits,
    "jpeg_exif_oriente.jpg": jpeg_exif_oriente,
}

IMAGES_HORS_DOMAINE: dict[str, Callable[[], Image.Image]] = {
    "noire.png": lambda: image_uniforme((0, 0, 0)),
    "blanche.png": lambda: image_uniforme((255, 255, 255)),
    "grise.png": lambda: image_uniforme((128, 128, 128)),
    "orange_uniforme.png": lambda: image_uniforme((255, 140, 0)),
    "bruit.png": image_bruit,
    "capture_texte.png": image_texte,
    "dessin_banane.png": dessin_banane,
    "dessin_orange.png": dessin_orange,
    "visage_schematique.png": visage_schematique,
}
