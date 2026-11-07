# Comparación de recuperadores: BM25 frente a semántico (nomic + Chroma)

Banco: `evaluacion/preguntas.yaml`; 16 preguntas `respondible` evaluadas (excluidas sin fragmento relevante: P02, P07, P08).
Relevante: fragmento con al menos `minimo` de los `hechos` de la pregunta.

| Recuperador | hit@3 | hit@5 | MRR@10 |
|---|---|---|---|
| bm25 | 0.8125 | 0.9375 | 0.7646 |
| semantico | 0.8125 | 0.8750 | 0.8281 |

## Rango del primer fragmento relevante por pregunta

| Pregunta | bm25 | semantico |
|---|---|---|
| P01 | 1 | — |
| P03 | 2 | 4 |
| P04 | 1 | 1 |
| P05 | 1 | 1 |
| P06 | 1 | 1 |
| P09 | 1 | 1 |
| P10 | 1 | 1 |
| P11 | 5 | 1 |
| P12 | 1 | 1 |
| P13 | 1 | 1 |
| P14 | 1 | 1 |
| P15 | 5 | 1 |
| P16 | 1 | 1 |
| P17 | 1 | 1 |
| P18 | — | — |
| P19 | 3 | 1 |

## Tiempo de indexación (167 fragmentos; 1 calentamiento descartado, mediana de 3)

| Dispositivo | Carga del modelo (s) | Repeticiones (s) | Mediana (s) |
|---|---|---|---|
| cpu | 1.826 | 30.168, 16.473, 16.226 | 16.473 |
| cuda | 2.218 | 1.136, 1.172, 1.160 | 1.160 |

Entorno: modelo=nomic-ai/nomic-embed-text-v1.5, revision=e9b6763023c676ca8431644204f50c2b100d9aab, dispositivo=cuda, torch=2.14.1+cu130, cuda_disponible=True, gpu=NVIDIA GeForce RTX 5070 Ti Laptop GPU, cuda=13.0
