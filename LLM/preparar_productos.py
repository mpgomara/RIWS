
import json
from pathlib import Path
from elasticsearch import Elasticsearch

# ==========================================
# CONFIGURACIÓN
# ==========================================

es = Elasticsearch("http://localhost:9200")
INDICE = "componentes"

CARPETA = Path(__file__).parent
ARCHIVO_SALIDA = CARPETA / "input.jsonl"

# ==========================================
# 1. RECUPERAR PRODUCTOS
# ==========================================

respuesta = es.search(
    index=INDICE,
    query={"match_all": {}},
    size=3
)

productos = respuesta["hits"]["hits"]

print(f"Productos recuperados: {len(productos)}")

# ==========================================
# 2. DEFINIR INSTRUCCIONES PARA EL LLM
# ==========================================

INSTRUCCION = """
Eres un asistente especializado en componentes informáticos.

Analiza el producto proporcionado y devuelve exclusivamente
un objeto JSON con los siguientes campos:

- categoria: categoría general del producto
- tipo: tipo específico de componente
- marca: fabricante del producto
- caracteristicas: lista de características técnicas
- palabras_clave: lista de términos útiles para buscarlo

Utiliza únicamente la información proporcionada.
No inventes características técnicas.
Si un dato no está disponible, utiliza null
o una lista vacía según corresponda.

No incluyas explicaciones ni bloques Markdown.
"""

# ==========================================
# 3. GENERAR PETICIONES JSONL
# ==========================================

with ARCHIVO_SALIDA.open("w", encoding="utf-8") as archivo:

    for producto in productos:

        datos = producto["_source"]
        identificador = producto["_id"]

        nombre = datos.get("nombre", "")
        descripcion = datos.get("descripcion", "")
        marca = datos.get("marca", "")
        categoria = datos.get("categoria", "")

        contenido = f"""
Nombre: {nombre}
Descripción: {descripcion}
Marca: {marca}
Categoría original: {categoria}
"""

        peticion = {
            "custom_id": f"producto_{identificador}",
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {
                "messages": [
                    {
                        "role": "system",
                        "content": INSTRUCCION
                    },
                    {
                        "role": "user",
                        "content": contenido
                    }
                ],
                "temperature": 0,
                "max_tokens": 250
            }
        }

        archivo.write(
            json.dumps(peticion, ensure_ascii=False) + "\n"
        )

        print(f"Preparado: {nombre}")

print(f"\nArchivo generado: {ARCHIVO_SALIDA}")
