#!/usr/bin/env python3
"""Microservicio de detección NSFW para LatamBOT (corre en la Raspberry Pi).

Combina DOS modelos para cubrir foto real Y anime/dibujo:
  - NudeNet (onnxruntime): desnudez en fotos reales.
  - imgutils anime_rating (dghs-imgutils): rating estilo Danbooru para anime
    (safe/r15/r18) → detecta rule 34 / hentai que NudeNet no ve.

El bot (EC2) le manda la URL de una imagen por Tailscale y responde
{"nsfw": bool, "score": float, "clase": str|null, "motor": str}.
Corre en la Pi (4 GB) para no cargar el EC2 (2 GB). Fail-open si algo falla.
Se corre como systemd nsfw-detector.service con el venv ~/nsfw-venv2.
"""
import json
import os
import tempfile
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from nudenet import NudeDetector

try:
    from imgutils.validate import anime_rating_score
except Exception:
    anime_rating_score = None

DET = NudeDetector()
PORT = int(os.getenv("NSFW_PORT", "8092"))
BIND = os.getenv("NSFW_BIND", "127.0.0.1")
THRESH = float(os.getenv("NSFW_THRESHOLD", "0.55"))       # umbral NudeNet (foto real)
ANIME_R18 = float(os.getenv("ANIME_R18_THRESHOLD", "0.55"))  # umbral rating r18 (anime)

# Clases de NudeNet que marcan contenido explícito (partes expuestas).
UNSAFE = {
    "FEMALE_GENITALIA_EXPOSED",
    "MALE_GENITALIA_EXPOSED",
    "ANUS_EXPOSED",
    "FEMALE_BREAST_EXPOSED",
    "BUTTOCKS_EXPOSED",
}


def analizar(url):
    tmp = tempfile.NamedTemporaryFile(suffix=".img", delete=False).name
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "LatamBOT-NSFW"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = r.read()
        with open(tmp, "wb") as fo:
            fo.write(data)

        # 1) NudeNet — foto real
        peor, clase = 0.0, None
        try:
            for d in DET.detect(tmp):
                if d.get("class") in UNSAFE and d.get("score", 0) >= THRESH and d["score"] > peor:
                    peor, clase = d["score"], d["class"]
        except Exception:
            pass

        # 2) anime rating — dibujo/hentai (safe / r15 sugestivo / r18 explícito)
        safe, r15, r18 = 1.0, 0.0, 0.0
        if anime_rating_score is not None:
            try:
                sc = anime_rating_score(tmp)
                safe = float(sc.get("safe", 1.0))
                r15 = float(sc.get("r15", 0.0))
                r18 = float(sc.get("r18", 0.0))
            except Exception:
                pass

        # Devuelve puntajes CRUDOS; el bot decide según el nivel del servidor.
        return {
            "nudenet_clase": clase,
            "nudenet_score": round(peor, 3),
            "safe": round(safe, 3),
            "r15": round(r15, 3),
            "r18": round(r18, 3),
        }
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        q = parse_qs(urlparse(self.path).query)
        url = (q.get("url") or [""])[0]
        if not url:
            self._send(400, {"error": "falta ?url="})
            return
        # Anti-SSRF basico: solo http(s) publico, sin localhost/metadata.
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                raise ValueError("scheme")
            host = (parsed.hostname or "").lower()
            if not host or host in ("localhost", "metadata.google.internal") or host.endswith(".local"):
                raise ValueError("host")
            if host.startswith("127.") or host.startswith("10.") or host.startswith("192.168.") or host.startswith("169.254."):
                raise ValueError("private")
            if host.startswith("172."):
                second = int(host.split(".")[1])
                if 16 <= second <= 31:
                    raise ValueError("private")
        except Exception:
            self._send(400, {"error": "url no permitida"})
            return
        try:
            self._send(200, analizar(url))
        except Exception as e:
            self._send(500, {"error": str(e)})

    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print("[nsfw] NudeNet + anime_rating listos, escuchando en %s:%d" % (BIND, PORT))
    ThreadingHTTPServer((BIND, PORT), Handler).serve_forever()
