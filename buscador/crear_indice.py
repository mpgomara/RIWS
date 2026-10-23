
from elasticsearch import Elasticsearch

# Conexión con Elasticsearch en Docker
es = Elasticsearch("http://localhost:9200")

NOMBRE_INDICE = "componentes"

# Definimos cómo Elasticsearch interpretará los campos
configuracion = {
    "mappings": {
        "properties": {
            "nombre": {"type": "text"},
            "descripcion": {"type": "text"},
            "marca": {
                "type": "text",
                "fields": {
                    "keyword": {"type": "keyword"}
                }
            },
            "precio": {"type": "float"},
            "url": {"type": "keyword"},
            "fuente": {"type": "keyword"},
            "caracteristicas": {
                "type": "object",
                "enabled": False
            }
        }
    }
}

if not es.indices.exists(index=NOMBRE_INDICE):
    es.indices.create(
        index=NOMBRE_INDICE,
        body=configuracion
    )
    print("Índice creado correctamente:", NOMBRE_INDICE)
else:
    print("El índice ya existe:", NOMBRE_INDICE)

# Agregar el campo categoria al índice existente
es.indices.put_mapping(
    index=NOMBRE_INDICE,
    properties={
        "categoria": {"type": "keyword"}
    }
)

print("Campo categoria configurado correctamente")    
