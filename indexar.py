"""Create the Elasticsearch index and bulk-load recursos.jsonl.

  pip install "elasticsearch>=8,<9"
  python indexar.py recursos.jsonl            # default http://localhost:9200, index "ldlc"
  python indexar.py recursos.jsonl --recreate # drop and rebuild the index
"""
import argparse
import json

from elasticsearch import Elasticsearch, helpers

MAPPING = {
    "settings": {"number_of_shards": 1, "number_of_replicas": 0},
    "mappings": {
        "properties": {
            "titulo": {"type": "text", "analyzer": "english",
                       "fields": {"raw": {"type": "keyword", "ignore_above": 256}}},
            "texto": {"type": "text", "analyzer": "english"},
            "precio": {"type": "scaled_float", "scaling_factor": 100},
            "moneda": {"type": "keyword"},
            "marca": {"type": "keyword"},
            "categorias": {"type": "keyword"},
            "url": {"type": "keyword"},
            "fuente": {"type": "keyword"},
        }
    },
}


def acciones(path, index):
    with open(path, encoding="utf-8") as f:
        for linea in f:
            doc = json.loads(linea)
            yield {"_index": index, "_id": doc.pop("id"), "_source": doc}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jsonl")
    ap.add_argument("--host", default="http://localhost:9200")
    ap.add_argument("--index", default="ldlc")
    ap.add_argument("--recreate", action="store_true")
    a = ap.parse_args()

    es = Elasticsearch(a.host)
    if a.recreate and es.indices.exists(index=a.index):
        es.indices.delete(index=a.index)
    if not es.indices.exists(index=a.index):
        es.indices.create(index=a.index, **MAPPING)

    ok, errores = helpers.bulk(es, acciones(a.jsonl, a.index), stats_only=False, raise_on_error=False)
    es.indices.refresh(index=a.index)
    print("Indexed:", ok, "| errors:", len(errores), "| total in index:", es.count(index=a.index)["count"])


if __name__ == "__main__":
    main()
