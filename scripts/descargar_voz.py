"""Descarga una voz de Piper desde el catálogo oficial ``rhasspy/piper-voices`` (Hugging Face).

Uso:
    uv run --no-sync python scripts/descargar_voz.py                      # es_MX-claude-high (femenina)
    uv run --no-sync python scripts/descargar_voz.py --voz es_MX-ald-medium  # masculina
    uv run --no-sync python scripts/descargar_voz.py --dir otra/carpeta

- Solo admite las voces revisadas por el proyecto (lista ``VOCES``) y sus licencias quedan en
  LICENCIAS_TERCEROS.md.
- Descarga el modelo ``.onnx``, su configuración ``.onnx.json`` y la ``MODEL_CARD`` a la carpeta de voces
  (por defecto ``FNA_VOZ_DIR`` o ``data/voces``, ignorada por git).
- Verifica el tamaño y el MD5 de cada archivo contra ``voices.json`` del catálogo antes de dejarlo en su
  lugar; un archivo que ya existe y coincide no se vuelve a descargar.
- Requiere red: se ejecuta a mano, nunca desde las pruebas.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import requests

from fabrica_autopartes.core.config import obtener_configuracion

CATALOGO = "https://huggingface.co/rhasspy/piper-voices/resolve/main"
VOCES = {
    "es_MX-claude-high": "femenina, Apache-2.0 (voz por defecto)",
    "es_MX-ald-medium": "masculina, Unlicense",
}
TIEMPO_ESPERA_S = 60
BLOQUE = 1 << 20


def _md5(ruta: Path) -> str:
    resumen = hashlib.md5(usedforsecurity=False)
    with ruta.open("rb") as archivo:
        for bloque in iter(lambda: archivo.read(BLOQUE), b""):
            resumen.update(bloque)
    return resumen.hexdigest()


def _coincide(ruta: Path, tamano: int, md5: str) -> bool:
    return ruta.is_file() and ruta.stat().st_size == tamano and _md5(ruta) == md5


def _descargar(sesion: requests.Session, ruta_remota: str, destino: Path, tamano: int, md5: str) -> None:
    if _coincide(destino, tamano, md5):
        print(f"  {destino.name}: ya descargado y verificado")
        return
    temporal = destino.with_name(destino.name + ".parcial")
    with sesion.get(f"{CATALOGO}/{ruta_remota}", stream=True, timeout=TIEMPO_ESPERA_S) as respuesta:
        respuesta.raise_for_status()
        with temporal.open("wb") as archivo:
            for bloque in respuesta.iter_content(BLOQUE):
                archivo.write(bloque)
    if not _coincide(temporal, tamano, md5):
        temporal.unlink(missing_ok=True)
        raise SystemExit(
            f"Error de integridad en {destino.name}: el tamaño o el MD5 no coinciden con el catálogo."
        )
    temporal.replace(destino)
    print(f"  {destino.name}: {tamano / 1_000_000:.1f} MB, MD5 verificado")


def main(argumentos: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description="Descarga una voz de Piper para IGNIS.")
    analizador.add_argument("--voz", choices=sorted(VOCES), default="es_MX-claude-high")
    analizador.add_argument(
        "--dir", type=Path, default=None, help="Carpeta de destino (por defecto FNA_VOZ_DIR)"
    )
    args = analizador.parse_args(argumentos)

    destino = args.dir or obtener_configuracion().dir_voces
    destino.mkdir(parents=True, exist_ok=True)
    sesion = requests.Session()
    sesion.headers["User-Agent"] = "FNA-KB/1.0 (descarga de voz Piper)"

    catalogo = sesion.get(f"{CATALOGO}/voices.json", timeout=TIEMPO_ESPERA_S)
    catalogo.raise_for_status()
    voz = catalogo.json().get(args.voz)
    if not voz:
        raise SystemExit(f"La voz {args.voz} no está en el catálogo de Piper.")

    print(f"Voz {args.voz} ({VOCES[args.voz]}) → {destino}")
    for ruta_remota, datos in voz["files"].items():
        nombre = Path(ruta_remota).name
        archivo = destino / (f"{args.voz}.MODEL_CARD" if nombre == "MODEL_CARD" else nombre)
        _descargar(sesion, ruta_remota, archivo, int(datos["size_bytes"]), str(datos["md5_digest"]))
    print(f"Listo. Para usarla: FNA_VOZ_MODELO={args.voz}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
