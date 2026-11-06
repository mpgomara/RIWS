"""Envia input.jsonl como un lote (Batch) al LLM del IRLab y guarda las respuestas.

input.jsonl tiene una peticion por linea. Las peticiones no llevan campo
"model": el modelo lo fija el servidor.

Pasos: 1) preparar input.jsonl (lo haceis vosotros), 2) subirlo,
3) crear el batch, 4) esperar a que termine, 5) descargar y leer los resultados.

Uso:
    export IRLAB_API_KEY="sk-..."        # Linux / macOS
    $env:IRLAB_API_KEY = "sk-..."        # Windows (PowerShell)
    python irlab_batch.py
"""

import getpass
import json
import os
import time
from pathlib import Path

from openai import OpenAI

BASE_URL = "https://inference.irlab.org/v1"
POLL_SECONDS = 15            # cada cuanto se pregunta por el estado

api_key = os.environ.get("IRLAB_API_KEY") or getpass.getpass("Token: ")
client = OpenAI(api_key=api_key, base_url=BASE_URL)
carpeta = Path(__file__).parent

# 1) El fichero de entrada: una peticion por linea.
input_path = carpeta / "input.jsonl"
if not input_path.is_file():
    raise SystemExit(f"No se encuentra el fichero de entrada: {input_path}")

# 2) y 3) Subir el fichero y crear el batch.
with input_path.open("rb") as f:
    subido = client.files.create(file=f, purpose="batch")
batch = client.batches.create(
    input_file_id=subido.id,
    endpoint="/v1/chat/completions",
    completion_window="24h",   # plazo maximo, no el tiempo esperado
)
print(f"Batch {batch.id} enviado. Estado: {batch.status}")

# 4) Esperar sin saturar el servidor.
terminales = {"completed", "failed", "cancelled", "expired"}
while batch.status not in terminales:
    time.sleep(POLL_SECONDS)
    batch = client.batches.retrieve(batch.id)
    print(f"Estado: {batch.status}  {batch.request_counts}")

if batch.status != "completed":
    raise SystemExit(f"El batch termino como '{batch.status}': {batch.errors}")

# 5) Guardar la salida en bruto ANTES de procesarla.
#    Si el procesado falla, no hay que repetir (ni pagar) el batch.
if batch.output_file_id:
    salida = client.files.content(batch.output_file_id).text
    (carpeta / "output.jsonl").write_text(salida, encoding="utf-8")
else:
    salida = ""
if batch.error_file_id:
    errores = client.files.content(batch.error_file_id).text
    (carpeta / "errors.jsonl").write_text(errores, encoding="utf-8")
    print("Algunas peticiones fallaron: ver errors.jsonl")

# El orden de la salida NO tiene por que ser el de la entrada:
# cada respuesta se identifica por su custom_id.
total = 0
for linea in salida.splitlines():
    r = json.loads(linea)
    cid = r["custom_id"]
    if r.get("error") or r["response"]["status_code"] != 200:
        print(f"{cid}: ERROR {r.get('error') or r['response']['body']}")
        continue
    cuerpo = r["response"]["body"]
    respuesta = cuerpo["choices"][0]["message"]["content"]
    total += cuerpo.get("usage", {}).get("total_tokens", 0)
    print(f"{cid} -> {respuesta.strip()}")
print(f"Tokens gastados en este batch: {total}")
