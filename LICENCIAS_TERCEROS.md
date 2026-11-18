# Licencias de terceros

El código del repositorio se distribuye bajo licencia MIT ([`LICENSE`](LICENSE)). Esta página registra los
componentes de terceros cuya licencia exige una nota específica. El resto de dependencias conserva su propia
licencia (`uv tree`, `npm ls`).

## Síntesis de voz de IGNIS (`POST /api/v1/tts`)

| Componente | Uso | Licencia | Fuente |
|---|---|---|---|
| Piper (`piper-tts` 1.8.0) | Motor de síntesis de voz neuronal, ejecutado dentro del proceso de la API | GPL-3.0-or-later | https://github.com/OHF-Voice/piper1-gpl |
| ONNX Runtime (`onnxruntime`) | Inferencia del modelo de voz (dependencia de Piper) | MIT | https://github.com/microsoft/onnxruntime |
| Voz `es_MX-claude-high` (por defecto, femenina) | Modelo ONNX de la voz | Apache-2.0 (según su MODEL_CARD) | https://huggingface.co/rhasspy/piper-voices/tree/main/es/es_MX/claude/high |
| Voz `es_MX-ald-medium` (alternativa, masculina) | Modelo ONNX de la voz | Unlicense (según su MODEL_CARD) | https://huggingface.co/rhasspy/piper-voices/tree/main/es/es_MX/ald/medium |

### Nota sobre la GPL de Piper
- El repositorio **no redistribuye Piper**: se declara como dependencia en `pyproject.toml` y `uv` lo descarga
  desde PyPI en cada instalación. El código del repositorio sigue bajo licencia MIT.
- Los modelos de voz tampoco se versionan: `scripts/descargar_voz.py` los descarga a `data/voces/` (ignorado por
  Git), verifica su tamaño y su MD5 contra el catálogo `voices.json` y guarda junto a cada modelo su `MODEL_CARD`.
- Si en algún momento se distribuye una imagen o un paquete que incluya Piper (por ejemplo, una imagen Docker en
  el M3), ese conjunto distribuido queda sujeto a las obligaciones de la GPL-3.0 (entre ellas, ofrecer el código
  fuente de Piper y conservar su licencia).
