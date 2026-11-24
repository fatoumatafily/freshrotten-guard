# Image du backend FreshRotten Guard (contexte de build : racine du projet).
# Compatible Hugging Face Spaces (utilisateur 1000, port 7860).
# Construction locale : docker build -f backend/Dockerfile -t freshrotten-guard .
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TF_CPP_MIN_LOG_LEVEL=2 \
    TF_ENABLE_ONEDNN_OPTS=0

RUN apt-get update && apt-get install -y --no-install-recommends libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 app

WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --upgrade pip && pip install -r backend/requirements.txt

USER app
ENV HOME=/home/app
# Poids ImageNet du gardien téléchargés à la construction, empreinte SHA-256 vérifiée.
RUN python -c "import keras; keras.utils.get_file('mobilenet_v2_weights_tf_dim_ordering_tf_kernels_1.0_224.h5', \
    'https://storage.googleapis.com/tensorflow/keras-applications/mobilenet_v2/mobilenet_v2_weights_tf_dim_ordering_tf_kernels_1.0_224.h5', \
    cache_subdir='models', file_hash='3e195a2857356cfc092cbbb460beb2a5bce279015d7792598b8d3d9e451902e3')"

COPY --chown=app model/ model/
COPY --chown=app backend/app/ backend/app/
COPY --chown=app backend/artefacts/ backend/artefacts/
COPY --chown=app backend/pyproject.toml backend/

WORKDIR /app/backend
EXPOSE 7860
# --proxy-headers : derrière le proxy de l'hébergeur, l'IP réelle sert à la limitation de débit.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860} --proxy-headers --forwarded-allow-ips='*' --no-server-header"]
