
const formulario = document.getElementById("formulario-busqueda");
const listaProductos = document.getElementById("lista-productos");
const totalResultados = document.getElementById("total-resultados");

formulario.addEventListener("submit", async (evento) => {
    evento.preventDefault();

    const consulta = document.getElementById("consulta").value.trim();
    const categoria = document.getElementById("categoria").value;
    const precioMin = document.getElementById("precio-min").value;
    const precioMax = document.getElementById("precio-max").value;

    const parametros = new URLSearchParams();

    if (consulta) parametros.append("q", consulta);
    if (categoria) parametros.append("categoria", categoria);
    if (precioMin) parametros.append("precio_min", precioMin);
    if (precioMax) parametros.append("precio_max", precioMax);

    totalResultados.textContent = "Buscando productos...";
    listaProductos.replaceChildren();

    try {
        const respuesta = await fetch(`/api/productos?${parametros}`);

        if (!respuesta.ok) {
            throw new Error("No se pudo realizar la búsqueda");
        }

        const datos = await respuesta.json();

        totalResultados.textContent =
            `${datos.total} productos encontrados (mostrando hasta 20).`;

        if (datos.productos.length === 0) {
            totalResultados.textContent = "No se encontraron productos.";
            return;
        }

        datos.productos.forEach((producto) => {
            const tarjeta = document.createElement("article");
            tarjeta.className = "producto";

            const nombre = document.createElement("h3");
            nombre.textContent = producto.nombre || "Producto sin nombre";

            const categoriaTexto = document.createElement("span");
            categoriaTexto.className = "categoria";
            categoriaTexto.textContent =
                `${producto.categoria || "Sin categoría"} · ${producto.fuente || ""}`;

            const descripcion = document.createElement("p");
            descripcion.className = "descripcion";
            descripcion.textContent = producto.descripcion || "Sin descripción";

            const precio = document.createElement("div");
            precio.className = "precio";
            precio.textContent = typeof producto.precio === "number"
                ? producto.precio.toLocaleString("es-ES", {
                    style: "currency",
                    currency: "EUR"
                })
                : "Precio no disponible";

            const enlace = document.createElement("a");
            enlace.textContent = "Ver en la tienda";
            enlace.href = producto.url || "#";
            enlace.target = "_blank";
            enlace.rel = "noopener noreferrer";

            tarjeta.append(
                nombre,
                categoriaTexto,
                descripcion,
                precio,
                enlace
            );

            listaProductos.appendChild(tarjeta);
        });

    } catch (error) {
        console.error(error);
        totalResultados.textContent =
            "Error al buscar productos. Comprueba que Flask y Elasticsearch estén funcionando.";
    }
});


async function cargarCategorias() {
    const selector = document.getElementById("categoria");

    try {
        const respuesta = await fetch("/api/categorias");

        if (!respuesta.ok) {
            throw new Error("No se pudieron cargar las categorías");
        }

        const datos = await respuesta.json();

        datos.categorias.forEach((categoria) => {
            const opcion = document.createElement("option");
            opcion.value = categoria;
            opcion.textContent = categoria;
            selector.appendChild(opcion);
        });

    } catch (error) {
        console.error("Error cargando categorías:", error);
    }
}

cargarCategorias();

