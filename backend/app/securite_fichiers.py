"""Validation défensive des fichiers envoyés par les utilisateurs.

Principes :

* on ne se fie **jamais** à l'extension, au nom de fichier ni au Content-Type ;
* on identifie le format par ses **octets magiques**, puis on exige que Pillow
  décode réellement une image du même format ;
* on vérifie les dimensions **avant** de décoder les pixels (bombe de
  décompression) ;
* on refuse SVG, GIF, images animées, polyglottes et fichiers tronqués ;
* on supprime toutes les métadonnées (EXIF, ICC, texte) après avoir appliqué
  l'orientation EXIF, et on convertit proprement en RGB 8 bits ;
* tout se passe **en mémoire** : rien n'est jamais écrit sur le disque.
"""

from __future__ import annotations

import io
import re
import warnings
from dataclasses import dataclass, field

import numpy as np
from PIL import Image, ImageFile, ImageOps, UnidentifiedImageError

# Un fichier tronqué doit lever une erreur, jamais être « complété » en silence.
ImageFile.LOAD_TRUNCATED_IMAGES = False

FORMATS_ACCEPTES = ("JPEG", "PNG", "WEBP")

# Marqueurs textuels qui n'ont rien à faire dans une image : signe de polyglotte.
# On ne garde que des motifs d'au moins 5 octets pour que la probabilité de les
# trouver par hasard dans des données compressées reste négligeable (< 1e-4 par
# fichier de 5 Mo). « <?xml » est exclu : il apparaît dans les métadonnées XMP.
_MARQUEURS_SUSPECTS = re.compile(
    rb"<script|<html|<\?php|<iframe|javascript:|<object|onerror=",
    re.IGNORECASE,
)


class FichierRefuse(Exception):
    """Fichier rejeté. ``code`` est stable (tests, logs) ; ``message`` est montré à l'utilisateur."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass
class ImageValidee:
    """Image décodée, nettoyée (RGB 8 bits, sans métadonnées) et informations associées."""

    image: Image.Image
    format: str
    largeur: int
    hauteur: int
    alertes: list[str] = field(default_factory=list)


def detecter_format(octets: bytes) -> str | None:
    """Identifie le format d'après les octets magiques (``JPEG``, ``PNG``, ``WEBP``) ou ``None``."""
    if octets.startswith(b"\xff\xd8\xff"):
        return "JPEG"
    if octets.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG"
    if len(octets) >= 12 and octets[:4] == b"RIFF" and octets[8:12] == b"WEBP":
        return "WEBP"
    return None


def _decrire_format_refuse(octets: bytes) -> FichierRefuse:
    """Construit un refus explicite pour les formats connus mais interdits."""
    debut = octets[:512].lstrip().lower()
    if octets.startswith((b"GIF87a", b"GIF89a")):
        return FichierRefuse("gif_refuse", "Les GIF ne sont pas acceptés (utilisez JPEG, PNG ou WebP).")
    if debut.startswith(b"<svg") or (debut.startswith(b"<?xml") and b"<svg" in debut):
        return FichierRefuse("svg_refuse", "Les images SVG ne sont pas acceptées.")
    if octets.startswith(b"MZ") or octets.startswith(b"\x7fELF"):
        return FichierRefuse("executable", "Fichier invalide : ce n'est pas une image.")
    if debut.startswith((b"<!doctype", b"<html", b"<?php", b"<script")):
        return FichierRefuse("script", "Fichier invalide : ce n'est pas une image.")
    return FichierRefuse("type_invalide", "Fichier invalide : formats acceptés JPEG, PNG, WebP.")


def _fin_utile(octets: bytes, fmt: str) -> int | None:
    """Position de fin réelle du flux image (pour détecter des données ajoutées après)."""
    if fmt == "JPEG":
        pos = octets.rfind(b"\xff\xd9")
        return None if pos < 0 else pos + 2
    if fmt == "PNG":
        pos = octets.rfind(b"IEND")
        return None if pos < 0 else pos + 8  # type (4) + CRC (4)
    if fmt == "WEBP":
        return int.from_bytes(octets[4:8], "little") + 8
    return None


def detecter_polyglotte(octets: bytes, fmt: str) -> str | None:
    """Renvoie une description si le fichier semble contenir autre chose qu'une image."""
    if _MARQUEURS_SUSPECTS.search(octets):
        return "contenu HTML/script intégré"
    fin = _fin_utile(octets, fmt)
    if fin is None:
        return None  # fichier tronqué : sera refusé au décodage
    reste = octets[fin:]
    # On tolère un léger rembourrage nul (certains appareils photo en ajoutent).
    if len(reste.strip(b"\x00\r\n \t")) > 0:
        if b"PK\x03\x04" in reste or b"PK\x05\x06" in reste:
            return "archive ZIP ajoutée après l'image"
        return "données ajoutées après la fin de l'image"
    return None


def _convertir_en_rgb(img: Image.Image, alertes: list[str]) -> Image.Image:
    """Convertit tous les modes Pillow courants en RGB 8 bits, proprement."""
    mode = img.mode
    if mode in ("I;16", "I;16B", "I;16L", "I;16N", "I"):
        # Niveaux de gris 16 bits : convert("RGB") saturerait tout au blanc.
        tableau = np.asarray(img, dtype=np.float64)
        maxi = 65535.0 if mode.startswith("I;16") or tableau.max() > 255 else 255.0
        img = Image.fromarray(np.clip(tableau / maxi * 255.0, 0, 255).astype("uint8"), mode="L")
        alertes.append("profondeur_16_bits_convertie")
        mode = "L"
    if mode == "F":
        tableau = np.asarray(img, dtype=np.float64)
        img = Image.fromarray(np.clip(tableau, 0, 255).astype("uint8"), mode="L")
        mode = "L"
    if mode == "P":
        img = img.convert("RGBA")
        mode = "RGBA"
    if mode in ("RGBA", "LA", "PA") or (mode == "RGB" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        if rgba.getchannel("A").getextrema()[0] < 255:
            alertes.append("transparence_aplatie_sur_blanc")
        fond = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        return Image.alpha_composite(fond, rgba).convert("RGB")
    if mode == "CMYK":
        alertes.append("cmjn_converti")
    if mode != "RGB":
        img = img.convert("RGB")
    return img


def valider_et_decoder(
    octets: bytes,
    *,
    taille_max: int,
    pixels_max: int,
    dimension_max: int,
    dimension_min: int = 32,
) -> ImageValidee:
    """Valide un fichier reçu et renvoie l'image nettoyée, ou lève :class:`FichierRefuse`."""
    if not octets:
        raise FichierRefuse("fichier_vide", "Fichier vide.")
    if len(octets) > taille_max:
        raise FichierRefuse(
            "fichier_trop_gros", f"Fichier trop volumineux (max {taille_max // (1024 * 1024)} Mo)."
        )

    fmt = detecter_format(octets)
    if fmt is None:
        raise _decrire_format_refuse(octets)

    suspect = detecter_polyglotte(octets, fmt)
    if suspect:
        raise FichierRefuse("polyglotte", "Fichier invalide : contenu suspect détecté dans l'image.")

    Image.MAX_IMAGE_PIXELS = pixels_max
    try:
        with warnings.catch_warnings():
            # Pillow émet un simple avertissement entre 1× et 2× la limite : on le traite en erreur.
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            img = Image.open(io.BytesIO(octets), formats=[fmt])
            # 1) Dimensions lues dans l'en-tête, AVANT tout décodage des pixels.
            largeur, hauteur = img.size
            if largeur * hauteur > pixels_max or max(largeur, hauteur) > dimension_max:
                raise FichierRefuse(
                    "bombe_decompression",
                    "Image refusée : dimensions trop grandes.",
                )
            if min(largeur, hauteur) < dimension_min:
                raise FichierRefuse("image_trop_petite", "Image trop petite pour être analysée.")
            # 2) Images animées / multi-images refusées (WebP animé, APNG…).
            if getattr(img, "n_frames", 1) > 1 or getattr(img, "is_animated", False):
                raise FichierRefuse("image_animee", "Les images animées ne sont pas acceptées.")
            # 3) Décodage complet : détecte fichiers corrompus ou tronqués.
            img.load()
    except FichierRefuse:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise FichierRefuse("bombe_decompression", "Image refusée : dimensions trop grandes.") from exc
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError, EOFError) as exc:
        raise FichierRefuse("fichier_corrompu", "Fichier invalide ou corrompu.") from exc

    if img.format != fmt:
        raise FichierRefuse("type_incoherent", "Fichier invalide : format incohérent.")

    alertes: list[str] = []
    exif = img.getexif()
    if exif:
        alertes.append("metadonnees_exif_supprimees")
    orientee = img
    if exif.get(0x0112, 1) not in (0, 1):  # balise Orientation
        try:
            orientee = ImageOps.exif_transpose(img)
            alertes.append("orientation_exif_appliquee")
        except Exception:  # EXIF malformé : on ignore l'orientation plutôt que d'échouer
            orientee = img

    rgb = _convertir_en_rgb(orientee, alertes)
    # Copie « nue » des pixels : aucune métadonnée (EXIF, ICC, texte PNG) n'est conservée.
    propre = Image.frombytes("RGB", rgb.size, rgb.tobytes())
    return ImageValidee(propre, fmt, propre.width, propre.height, alertes)
