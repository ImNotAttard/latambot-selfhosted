# ==============================================================================
# LatamBOT - imagen Docker lista para Railway / cualquier host con Docker
# ==============================================================================
FROM python:3.12-slim

# ffmpeg es necesario para l!dl / l!mp3 / audio de voz; ca-certificates para HTTPS.
# Las fuentes (liberation/dejavu-extra/freefont/noto/droid) son para el generador
# de imagenes de l!quote (tipografias + emoji/unicode) y l!bienvenida.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg ca-certificates \
       fonts-liberation fonts-dejavu-extra fonts-freefont-ttf \
       fonts-noto-core fonts-noto-color-emoji fonts-droid-fallback \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DATA_DIR=/data

WORKDIR /app

# Instalar dependencias primero para aprovechar la cache de capas.
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# deno: runtime de JavaScript que yt-dlp necesita para resolver las firmas de YouTube
# (sin esto, "Only images are available" y las descargas de YouTube fallan).
# Capa separada DESPUÉS de pip para no invalidar la cache pesada de dependencias.
RUN python -c "import urllib.request,zipfile,io,platform,os; \
arch=('aarch64-unknown-linux-gnu' if platform.machine() in ('aarch64','arm64') else 'x86_64-unknown-linux-gnu'); \
data=urllib.request.urlopen('https://github.com/denoland/deno/releases/latest/download/deno-'+arch+'.zip').read(); \
zipfile.ZipFile(io.BytesIO(data)).extractall('/usr/local/bin'); \
os.chmod('/usr/local/bin/deno',0o755)" \
    && /usr/local/bin/deno --version

# yt-dlp-ejs: scripts solucionadores de los "challenges" de YouTube (firmas/n).
# Junto con deno, hace que las descargas de YouTube funcionen. Capa separada para
# no invalidar la cache pesada de pip.
RUN pip install --no-cache-dir yt-dlp-ejs

# Copiar el resto del proyecto.
COPY . .

# Asegurar que el entrypoint sea ejecutable y con saltos de línea Unix (LF).
RUN sed -i 's/\r$//' /app/docker-entrypoint.sh && chmod +x /app/docker-entrypoint.sh

# La base de datos vive en un volumen persistente montado en /data.
VOLUME ["/data"]

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["python", "latambot.py"]
