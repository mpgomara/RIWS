
import json
import re
import hashlib
from pathlib import Path

from elasticsearch import Elasticsearch, helpers
import sys

RAIZ_PROYECTO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ_PROYECTO / "pruebasCopilot"))

from paginaWeb import product_category


# ==========================================
# 1. CONFIGURACIÓN
# ==========================================

RUTA_JSON = (
    Path(__file__).resolve().parent.parent
    / "pruebasCopilot"
    / "ldlc.json"
)

NOMBRE_INDICE = "componentes"
URL_ELASTICSEARCH = "http://localhost:9200"


# ==========================================
# 2. FUNCIONES DE LIMPIEZA
# ==========================================

def limpiar_texto(texto):
    """Elimina saltos de línea y espacios repetidos."""
    return " ".join(str(texto or "").split())


def extraer_precio(texto):
    """Extrae el primer precio en euros encontrado."""
    coincidencia = re.search(
        r"(\d[\d.,]*)\s*€\s*(\d{2})",
        texto
    )

    if not coincidencia:
        return None

    euros = int(
        coincidencia.group(1)
        .replace(".", "")
        .replace(",", "")
    )

    centimos = int(coincidencia.group(2))

    return euros + centimos / 100


def limpiar_marca(texto):
    """Elimina palabras duplicadas en marcas simples."""
    palabras = limpiar_texto(texto).split()

    if len(palabras) == 2 and palabras[0] == palabras[1]:
        return palabras[0]

    return " ".join(palabras)


# ==========================================
# 3. LEER PRODUCTOS DE LDLC
# ==========================================

with open(RUTA_JSON, encoding="utf-8") as archivo:
    productos = json.load(archivo)

print("Productos originales:", len(productos))


# ==========================================
# 4. PREPARAR DOCUMENTOS
# ==========================================

documentos = []

for producto in productos:

    caracteristicas = producto.get("caracteristicas", {})
    ficha = caracteristicas.get("ficha_tecnica", {})

    ficha_limpia = {
        clave: limpiar_texto(valor)
        for clave, valor in ficha.items()
    }

    marca = limpiar_marca(ficha_limpia.get("Marca", ""))
    ficha_limpia["Marca"] = marca

    documento = {
        "nombre": limpiar_texto(
            producto.get("nombre", "")
        ),
        "precio": extraer_precio(
            producto.get("precio") or ""
        ),
        "descripcion": limpiar_texto(
            caracteristicas.get("resumen", "")
        ),
        "categoria": product_category(producto),
        "marca": marca,
        "caracteristicas": ficha_limpia,
        "url": producto.get("url", ""),
        "fuente": "LDLC"
    }

    documentos.append(documento)


print("Documentos preparados:", len(documentos))

sin_precio = sum(
    1 for documento in documentos
    if documento["precio"] is None
)

print("Productos sin precio:", sin_precio)


# ==========================================
# 5. CONECTAR CON ELASTICSEARCH
# ==========================================

es = Elasticsearch(URL_ELASTICSEARCH)

if not es.ping():
    raise ConnectionError(
        "No se pudo conectar con Elasticsearch"
    )

print("Conexión con Elasticsearch: correcta")

if not es.indices.exists(index=NOMBRE_INDICE):
    raise RuntimeError(
        f"El índice '{NOMBRE_INDICE}' no existe. "
        "Ejecuta primero crear_indice.py"
    )


# ==========================================
# 6. PREPARAR INDEXACIÓN
# ==========================================

acciones = []

for documento in documentos:

    identificador = hashlib.sha256(
        documento["url"].encode("utf-8")
    ).hexdigest()

    acciones.append({
        "_index": NOMBRE_INDICE,
        "_id": identificador,
        "_source": documento
    })


# ==========================================
# 7. INDEXAR PRODUCTOS
# ==========================================

correctos, errores = helpers.bulk(
    es,
    acciones,
    raise_on_error=False
)

print("\nResultado de la indexación:")
print("Documentos procesados correctamente:", correctos)
print("Errores:", len(errores))

if errores:
    print("Primer error:", errores[0])


# ==========================================
# 8. VERIFICAR DOCUMENTOS
# ==========================================

es.indices.refresh(index=NOMBRE_INDICE)

resultado = es.count(index=NOMBRE_INDICE)

print(
    "Total de documentos en Elasticsearch:",
    resultado["count"]
)

print("\nProceso finalizado.")
