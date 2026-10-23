
from flask import Flask, jsonify, request, render_template
from elasticsearch import Elasticsearch

app = Flask(__name__)

es = Elasticsearch("http://localhost:9200")
INDICE = "componentes"

@app.route("/")
def inicio():
    return render_template("index.html")


@app.route("/api/categorias", methods=["GET"])
def obtener_categorias():
    try:
        respuesta = es.search(
            index=INDICE,
            size=0,
            aggs={
                "categorias": {
                    "terms": {
                        "field": "categoria",
                        "size": 100
                    }
                }
            }
        )

        categorias = [
            item["key"]
            for item in respuesta["aggregations"]["categorias"]["buckets"]
        ]

        return jsonify({
            "categorias": sorted(categorias)
        })

    except Exception:
        app.logger.exception("Error obteniendo categorías")
        return jsonify({
            "error": "No se pudieron obtener las categorías"
        }), 503


@app.route("/api/productos", methods=["GET"])
def buscar_productos():
    consulta = request.args.get("q", "").strip()
    categoria = request.args.get("categoria", "").strip()

    try:
        precio_min = request.args.get("precio_min", type=float)
        precio_max = request.args.get("precio_max", type=float)

        if (
            precio_min is not None
            and precio_max is not None
            and precio_min > precio_max
        ):
            return jsonify({"error": "El precio mínimo supera al máximo"}), 400

        filtros = []

        if categoria:
            filtros.append({
                "term": {"categoria": categoria}
            })

        rango = {}

        if precio_min is not None:
            rango["gte"] = precio_min

        if precio_max is not None:
            rango["lte"] = precio_max

        if rango:
            filtros.append({
                "range": {"precio": rango}
            })

        if consulta:
            busqueda = {
                "multi_match": {
                    "query": consulta,
                    "fields": ["nombre^3", "descripcion", "marca"]
                }
            }
        else:
            busqueda = {"match_all": {}}

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

        productos = [
            resultado["_source"]
            for resultado in respuesta["hits"]["hits"]
        ]

        return jsonify({
            "total": respuesta["hits"]["total"]["value"],
            "productos": productos
        })

    except Exception:
        app.logger.exception("Error consultando Elasticsearch")
        return jsonify({
            "error": "No se pudo consultar Elasticsearch"
        }), 503



if __name__ == "__main__":
    app.run(debug=True, port=5000)
