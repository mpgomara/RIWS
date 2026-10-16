
from elasticsearch import Elasticsearch

es = Elasticsearch("http://localhost:9200")
INDICE = "componentes"

# Obtener categorías existentes en Elasticsearch
respuesta_categorias = es.search(
    index=INDICE,
    size=0,
    aggs={
        "categorias": {
            "terms": {
                "field": "categoria",
                "size": 50
            }
        }
    }
)

categorias = [
    item["key"]
    for item in respuesta_categorias["aggregations"]["categorias"]["buckets"]
]

categorias.sort()

print("\n=== BUSCADOR DE COMPONENTES ===")

consulta = input("\n¿Qué componente quieres buscar? ").strip()

print("\nCategorías disponibles:")
print("0. Todas las categorías")

for numero, categoria in enumerate(categorias, start=1):
    print(f"{numero}. {categoria}")

try:
    seleccion = int(input("\nSelecciona una categoría: "))

    if seleccion < 0 or seleccion > len(categorias):
        raise ValueError("Categoría no válida")

    precio_min = input("Precio mínimo (€), Enter para omitir: ").strip()
    precio_max = input("Precio máximo (€), Enter para omitir: ").strip()

    filtros = []

    # Filtrar por categoría
    if seleccion != 0:
        filtros.append({
            "term": {
                "categoria": categorias[seleccion - 1]
            }
        })

    # Filtrar por precio
    rango_precio = {}

    if precio_min:
        rango_precio["gte"] = float(precio_min.replace(",", "."))

    if precio_max:
        rango_precio["lte"] = float(precio_max.replace(",", "."))

    if rango_precio:
        filtros.append({
            "range": {
                "precio": rango_precio
            }
        })

    # Búsqueda textual
    if consulta:
        busqueda = {
            "multi_match": {
                "query": consulta,
                "fields": [
                    "nombre^3",
                    "descripcion",
                    "marca"
                ]
            }
        }
    else:
        busqueda = {"match_all": {}}

    # Consulta completa
    respuesta = es.search(
        index=INDICE,
        query={
            "bool": {
                "must": [busqueda],
                "filter": filtros
            }
        },
        size=20,
        track_total_hits=True
    )

    resultados = respuesta["hits"]["hits"]

    print("\nProductos encontrados:", respuesta["hits"]["total"]["value"])
    print("-" * 50)

    for resultado in resultados:
        producto = resultado["_source"]
        precio = producto.get("precio")

        print("Nombre:", producto["nombre"])
        print("Categoría:", producto.get("categoria", "Sin categoría"))
        print("Marca:", producto.get("marca", ""))
        print(
            "Precio:",
            f"{precio:.2f} €" if precio is not None else "No disponible"
        )
        print("Tienda:", producto["fuente"])
        print("URL:", producto["url"])
        print("-" * 50)

except ValueError as error:
    print("Error:", error)
