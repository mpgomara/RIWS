import json

with open("recursos.jsonl", encoding="utf-8") as f:
    docs = [json.loads(linea) for linea in f]
print("Documentos:", len(docs))
print("IDs distintos:", len({d["id"] for d in docs}))
print("Fuentes:", {d["fuente"] for d in docs})
print(docs[:1])