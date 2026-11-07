# ADR-023 · Base semántica con nomic y Chroma local

- **Estado:** aceptada (2026-11-07); BM25 sigue como recuperador por defecto. Detalle en las entradas S-09, E-05 y E-06
  de `docs/prompts/bitacora_experimentos.md`.
- **Contexto:** la Fase 1 exige embeddings (C6) y un índice vectorial (C7). La recuperación vigente es léxica (BM25
  con expansión, ADR-005) y Ollama está pospuesto (ADR-022). El corpus Gold tiene 167 fragmentos; el modo de contexto
  `auto` usa selección (unos 21 000 tokens superan el presupuesto de 9000), así que el recuperador influye en el Q&A.
- **Decisión:**
  1. **Embeddings:** `nomic-ai/nomic-embed-text-v1.5` (768 dimensiones) con `sentence-transformers==5.7.0` y
     `transformers==4.57.6`, prefijos `search_document: ` al indexar y `search_query: ` al consultar, y normalización
     L2. Revisiones fijadas: modelo `e9b6763023c676ca8431644204f50c2b100d9aab` y código remoto
     `nomic-ai/nomic-bert-2048@7710840340a098cfb869c4f65e87cf2b1b70caca` (`trust_remote_code=True`, revisado a mano;
     S-09). Por omisión no hay red (`local_files_only`); la descarga es explícita (`indexar-vectores --descargar`).
  2. **Índice:** Chroma 1.5.9 con `PersistentClient` en `data/vectores/` (ignorado en Git), espacio coseno, telemetría
     desactivada y `embedding_function=None` (Chroma no descarga su modelo ONNX). Metadatos: `fragmento_id`, `url`,
     `titulo` y `seccion`.
  3. **Recuperador:** `IndiceChroma` cumple el mismo protocolo `Recuperador` que `IndiceBM25`
     (`buscar(consulta, k) -> list[Resultado]`). `fabrica ask --recuperador bm25|semantico` y
     `FNA_RECUPERADOR`; **BM25 por defecto** (los resultados no muestran una mejora clara).
  4. **Dependencias opcionales y excluyentes:** extras `semantica-cpu` (índice PyTorch CPU) y `semantica-gpu` (índice
     `cu130`), con `torch==2.14.1` en ambos y declarados como conflicto en `[tool.uv]`. CI y `make instalar` no instalan
     ninguno. `cu130` publica wheels de `torch==2.14.1` para `win_amd64` y Linux (cu128 queda como respaldo) e incluye
     sm_120 (Blackwell) en `torch.cuda.get_arch_list()`.
  5. **Dispositivo:** `EMBEDDINGS_DEVICE=auto|cpu|cuda` (por defecto `auto`: `cuda` si `torch.cuda.is_available()`).
     `cuda` sin GPU es un error explícito. El dispositivo, la versión de PyTorch y la GPU quedan en el registro y en
     cada resultado.
- **Resultados** (`evaluacion/resultados/20261107T202956Z_*`, GPU NVIDIA GeForce RTX 5070 Ti Laptop GPU,
  `torch 2.14.1+cu130`):

  | Recuperador | hit@3 | hit@5 | MRR@10 |
  |---|---|---|---|
  | BM25 | 0,8125 | 0,9375 | 0,7646 |
  | Semántico (nomic + Chroma) | 0,8125 | 0,8750 | 0,8281 |

  16 preguntas `respondible` evaluadas (P02, P07 y P08 sin fragmento relevante en Gold). El semántico pone el
  primer relevante en el rango 1 en 13 de 16 preguntas (BM25: 11), pero no encuentra P01 (dirección de la sede)
  entre los 10 primeros. Prefijos (3 consultas × 3 fragmentos): aciertos top-1 3/3 con prefijos y 2/3 sin ellos.

  | Indexación de 167 fragmentos | Carga del modelo | Mediana (1 calentamiento + 3 repeticiones) |
  |---|---|---|
  | `EMBEDDINGS_DEVICE=cpu` | 1,8 s | 16,5 s |
  | `EMBEDDINGS_DEVICE=cuda` | 2,2 s | 1,16 s (unas 14 veces más rápido) |

- **Consecuencias:**
  - Con la variante GPU, `.venv` pasa de 684 a 4135 MiB (+3451 MiB; `torch` ocupa 2934 MiB; descarga de torch: 1,9 GiB);
    el modelo ocupa 523 MiB (`model.safetensors`, 546 938 168 bytes) en
    `~/.cache/huggingface` y el índice `data/vectores/`, 3,3 MiB. La variante CPU descarga unos 0,3 GB (estimación; no
    se instaló en este equipo).
  - `trust_remote_code` ejecuta código de terceros: cualquier cambio de revisión repite la revisión manual (S-09).
  - El código remoto de nomic no funciona con transformers 5 (`get_extended_attention_mask` ya no existe), lo que
    obliga a mantener `sentence-transformers` 5.x y `transformers` 4.x mientras no haya una revisión compatible.
  - `make instalar` o un `uv run` sin `--no-sync` retiran el extra; hay que reinstalar la variante.
  - El criterio de relevancia por hechos admite falsos positivos con números cortos (por ejemplo, «450»); las métricas
    son orientativas para comparar recuperadores, no una evaluación definitiva.
- **Alternativas:**
  - **Ollama** con `nomic-embed-text` como servidor local: pospuesto (ADR-022).
  - **Qdrant** en modo local (`QdrantClient(path=...)`): equivalente para 167 fragmentos; Chroma se eligió por la
    propuesta OpenSpec del Módulo 2 y por su API más simple para metadatos.
  - **Recuperación híbrida** (BM25 + semántico con fusión por rango recíproco): candidata natural, dado que cada
    recuperador acierta donde el otro falla (P01 frente a P11, P15 y P19); queda para un cambio posterior con su propia
    evaluación.
