# ComponentSearch — Buscador de componentes informáticos

Proyecto académico de Recuperación de Información y Web.

Esta versión permite buscar componentes informáticos mediante
Elasticsearch, utilizando una interfaz web desarrollada con
Flask, HTML, CSS y JavaScript.

## Funcionalidades actuales

- Indexación de productos de LDLC.
- Búsqueda textual mediante Elasticsearch (BM25).
- Filtro por categorías.
- Filtros por precio mínimo y máximo.
- Visualización de productos y enlaces a la tienda.
- API REST desarrollada con Flask.

## Requisitos

- Windows 10/11.
- Python 3.11.
- Docker Desktop funcionando.
- Git.

## 1. Descargar el proyecto

Clonar el repositorio RIWS y seleccionar la rama:

```powershell
git clone URL_DEL_REPOSITORIO
cd RIWS
git switch feature/elasticsearch
```

Si el repositorio ya está descargado:

```powershell
git fetch origin
git switch feature/elasticsearch
git pull
```

## 2. Preparar Python

Desde la carpeta raíz `RIWS`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r buscador/requirements.txt
```

## 3. Iniciar Elasticsearch

Abrir Docker Desktop y esperar a que esté funcionando.

Crear un contenedor de Elasticsearch 9.5.3:

```powershell
docker run -d --name es01 -p 9200:9200 -e "discovery.type=single-node" -e "xpack.security.enabled=false" -e "ES_JAVA_OPTS=-Xms1g -Xmx1g" docker.elastic.co/elasticsearch/elasticsearch:9.5.3
```

Si el contenedor ya existe, pero está detenido:

```powershell
docker start es01
```

Comprobar que Elasticsearch responde:

```powershell
curl.exe http://localhost:9200
```

Nota: esta configuración desactiva la seguridad de Elasticsearch
únicamente para pruebas locales. No debe exponerse a Internet.

## 4. Crear el índice

```powershell
python buscador/crear_indice.py
```

## 5. Indexar los productos

El proyecto utiliza el archivo:

`pruebasCopilot/ldlc.json`

Ejecutar:

```powershell
python buscador/indexar_productos.py
```

Deberían indexarse 279 productos, utilizando la versión actual
del archivo JSON.

## 6. Iniciar la aplicación web

```powershell
python buscador/app.py
```

Abrir en el navegador:

http://127.0.0.1:5000/

## 7. Probar el buscador

Ejemplo:

- Búsqueda: Arctic
- Categoría: Refrigeración
- Precio mínimo: 5
- Precio máximo: 50

Con los datos actuales deberían aparecer dos productos.

## Estructura del buscador

- `app.py`: servidor Flask y API REST.
- `crear_indice.py`: creación del índice de Elasticsearch.
- `indexar_productos.py`: preparación e indexación de productos.
- `buscar_productos.py`: pruebas de búsqueda desde terminal.
- `templates/index.html`: estructura de la interfaz.
- `static/estilos.css`: estilos visuales.
- `static/buscador.js`: conexión de la interfaz con la API.
- `requirements.txt`: dependencias Python.

## Estado del proyecto

Versión inicial funcional.

Pendiente:
- Incorporar una segunda fuente de productos.
- Mejorar la relevancia y la tolerancia a errores ortográficos.
- Implementar paginación.
- Integrar el servidor LLM requerido por la asignatura.
- Revisar la normalización y clasificación de productos.
```