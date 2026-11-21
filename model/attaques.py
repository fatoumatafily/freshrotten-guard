"""Prétraitement et attaques adversariales (FGSM, PGD), utilisés par l'application web."""
import numpy as np
import tensorflow as tf
import keras
from PIL import Image

perte = keras.losses.CategoricalCrossentropy()


def charger_image(fichier, img_size=(128, 128)):
    """Chemin ou fichier uploadé -> tableau (1, H, W, 3), pixels entre 0 et 1 (comme à l'entraînement)."""
    img = Image.open(fichier).convert("RGB").resize(tuple(img_size), Image.NEAREST)
    x = np.asarray(img, dtype="float32") / 255.0
    return np.expand_dims(x, axis=0)


def one_hot(indice, nb_classes):
    y = np.zeros((1, nb_classes), dtype="float32")
    y[0, indice] = 1.0
    return y


def gradient_entree(modele, x, y):
    x = tf.convert_to_tensor(x)
    with tf.GradientTape() as tape:
        tape.watch(x)
        loss = perte(y, modele(x, training=False))
    return tape.gradient(loss, x)


def fgsm(modele, x, y, eps):
    x = tf.convert_to_tensor(x)
    x_adv = x + eps * tf.sign(gradient_entree(modele, x, y))
    return tf.clip_by_value(x_adv, 0.0, 1.0).numpy()


def pgd(modele, x, y, eps, alpha=None, steps=10, cible=False):
    """cible=False : y = vraie classe (on s'en éloigne). cible=True : y = classe visée (on s'en rapproche)."""
    if alpha is None:
        alpha = 2.5 * eps / steps
    x = tf.convert_to_tensor(x)
    x_adv = tf.clip_by_value(x + tf.random.uniform(tf.shape(x), -eps, eps), 0.0, 1.0)
    for _ in range(steps):
        grad = gradient_entree(modele, x_adv, y)
        x_adv = x_adv - alpha * tf.sign(grad) if cible else x_adv + alpha * tf.sign(grad)
        x_adv = tf.clip_by_value(x_adv, x - eps, x + eps)
        x_adv = tf.clip_by_value(x_adv, 0.0, 1.0)
    return x_adv.numpy()
