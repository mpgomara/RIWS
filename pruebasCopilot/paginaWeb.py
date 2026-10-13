import json
import re
from collections import Counter
from html import escape
from pathlib import Path
import unicodedata


BASE_DIR = Path(__file__).resolve().parent
INPUT_PATH = BASE_DIR / "ldlc.json"
OUTPUT_PATH = BASE_DIR / "paginaWeb.html"


def clean_text(value):
    return " ".join(str(value or "").split())


def price_in_cents(value):
    match = re.search(r"([\d\s.,]+)\s*€\s*(\d{1,2})?", clean_text(value))
    if not match:
        return ""
    euros = int(re.sub(r"\D", "", match.group(1)))
    cents = int((match.group(2) or "0").ljust(2, "0"))
    return str(euros * 100 + cents)


def normalize_text(value):
    normalized = unicodedata.normalize("NFKD", clean_text(value).casefold())
    return "".join(character for character in normalized if not unicodedata.combining(character))


def product_category(product):
    characteristics = product.get("caracteristicas") or {}
    specifications = characteristics.get("ficha_tecnica") or {}
    name = normalize_text(product.get("nombre"))
    summary = normalize_text(characteristics.get("resumen"))
    specification_keys = " ".join(normalize_text(key) for key in specifications)
    specification_values = " ".join(normalize_text(value) for value in specifications.values())
    identity = f"{name} {summary}"

    if "kit de actualizacion" in identity or "kit upgrade" in specification_keys:
        return "Kits de actualización"
    if "formato de la carcasa" in specification_keys or any(
        term in identity for term in ("caja de pc", "caja de media torre", "filtro antipolvo")
    ):
        return "Cajas y accesorios"
    if any(term in identity for term in ("geforce", "rtx ", "gtx ", "radeon rx", "quadro")):
        return "Tarjetas gráficas"
    if "tamano memoria video" in specification_keys or "marca del gpu" in specification_keys:
        return "Tarjetas gráficas"
    if "modelo de procesador" in specification_keys or "frecuencia cpu" in specification_keys:
        return "Procesadores"
    if "formato de memoria" in specification_keys or "capacidad por modulo de memoria" in specification_keys:
        return "Memoria RAM"
    if "placa base" in name or "socket" in summary and "chipset" in summary:
        return "Placas base"
    if any(term in identity for term in ("nvme", "ssd", "disco duro", "hdd", "tarjeta de memoria")):
        return "Almacenamiento"
    if "80 plus" in identity or "formato alimentacion" in specification_keys:
        return "Fuentes de alimentación"
    if any(term in identity for term in ("ventilador", "refrigeracion", "watercooling", "pasta termica", "ventirad")):
        return "Refrigeración"
    if any(term in identity for term in ("tarjeta de sonido", "tarjeta de red", "controladora")):
        return "Conectividad y expansión"
    if "montaje" in name:
        return "Montaje y servicios"
    if any(term in identity for term in ("cable", "adaptador", "conector", "usb", "hdmi", "displayport")):
        return "Cables y adaptadores"
    if any(term in identity for term in ("tornillo", "separador", "accesorio", "filtro")):
        return "Accesorios"
    return "Otros componentes"


def load_products():
    text = INPUT_PATH.read_text(encoding="utf-8")
    try:
        products = json.loads(text)
        return products, False
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        index = len(text) - len(text.lstrip())
        if index >= len(text) or text[index] != "[":
            raise
        index += 1
        products = []

        while True:
            while index < len(text) and text[index].isspace():
                index += 1
            if index >= len(text):
                return products, True
            if text[index] == "]":
                return products, False
            if text[index] == ",":
                index += 1
                while index < len(text) and text[index].isspace():
                    index += 1
                if index >= len(text):
                    return products, True

            try:
                product, index = decoder.raw_decode(text, index)
            except json.JSONDecodeError as error:
                if error.pos >= len(text) - 1:
                    return products, True
                raise
            products.append(product)

            while index < len(text) and text[index].isspace():
                index += 1
            if index >= len(text):
                return products, True
            if text[index] == ",":
                index += 1
            elif text[index] == "]":
                return products, False
            else:
                raise ValueError("El JSON contiene datos no válidos entre productos.")


def render_product(product, index):
    name = clean_text(product.get("nombre")) or "Producto sin nombre"
    price = clean_text(product.get("precio")) or "Precio no disponible"
    sortable_price = price_in_cents(price)
    category = product_category(product)
    characteristics = product.get("caracteristicas") or {}
    summary = clean_text(characteristics.get("resumen"))
    specifications = characteristics.get("ficha_tecnica") or {}
    if not isinstance(specifications, dict):
        specifications = {}

    search_text = clean_text(
        " ".join([name, price, summary] + [f"{key} {value}" for key, value in specifications.items()])
    )
    rows = "".join(
        f'<div class="spec-row"><dt>{escape(clean_text(key))}</dt>'
        f'<dd>{escape(clean_text(value))}</dd></div>'
        for key, value in specifications.items()
    )
    preview = "".join(
        f'<div class="spec-row"><dt>{escape(clean_text(key))}</dt>'
        f'<dd>{escape(clean_text(value))}</dd></div>'
        for key, value in list(specifications.items())[:5]
    )
    if not preview:
        preview = '<p class="muted">Ficha técnica no disponible.</p>'

    details = ""
    if rows:
        details = (
            f'<details><summary>Ficha técnica completa ({len(specifications)} datos)</summary>'
            f'<dl class="spec-list full-specs">{rows}</dl></details>'
        )

    product_url = product.get("url", "")
    link = ""
    if isinstance(product_url, str) and product_url.startswith(
        "https://www.ldlc.com/es-es/ficha/"
    ):
        link = (
            f'<a class="product-link" href="{escape(product_url, quote=True)}" '
            'target="_blank" rel="noopener noreferrer">Ver en LDLC</a>'
        )

    return f"""
        <article class="product-card" data-search="{escape(search_text.casefold(), quote=True)}" data-category="{escape(category, quote=True)}" data-price="{sortable_price}">
      <div class="card-topline"><span>PRODUCTO {index:02d}</span>
        <strong class="price">{escape(price)}</strong></div>
      <h2>{escape(name)}</h2>
            <p class="category-label">{escape(category)}</p>
      <p class="summary">{escape(summary or "Sin descripción disponible.")}</p>
      <dl class="spec-list">{preview}</dl>
      {details}
      {link}
    </article>
    """


def render_page(products, incomplete):
    cards = "".join(
        render_product(product, index)
        for index, product in enumerate(products, start=1)
    )
    if not cards:
        cards = '<p class="empty-state">No hay productos en el archivo JSON.</p>'
    category_counts = Counter(product_category(product) for product in products)
    category_options = [f'<option value="">Todas las categorías ({len(products)})</option>']
    for category, count in sorted(category_counts.items()):
        safe_category = escape(category, quote=True)
        category_options.append(
            f'<option value="{safe_category}">{escape(category)} ({count})</option>'
        )

    notice = ""
    if incomplete:
        notice = (
            '<p class="warning" role="status">El JSON quedó incompleto; '
            'se muestran solo los registros completos recuperados.</p>'
        )

    template = r"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Componentes | Catálogo LDLC</title>
  <style>
    :root { color-scheme: light; --ink:#172321; --muted:#5e6a67; --paper:#f3f6f2; --line:#d9e1dc; --green:#176b55; --orange:#d95735; --serif:Georgia,"Times New Roman",serif; --sans:"Trebuchet MS",Verdana,sans-serif; }
    * { box-sizing:border-box; }
    body { margin:0; background:var(--paper); color:var(--ink); font-family:var(--sans); line-height:1.5; }
    .masthead { border-bottom:1px solid var(--line); background:linear-gradient(115deg,#e4f1e8,#f7f5ec 58%,#f9e6dc); }
    .masthead-inner, main { width:min(1180px,calc(100% - 40px)); margin:0 auto; }
    .masthead-inner { padding:38px 0 30px; }
    .eyebrow { margin:0 0 8px; color:var(--green); font-size:.78rem; font-weight:700; text-transform:uppercase; }
    h1 { max-width:760px; margin:0; font:700 3rem/1.08 var(--serif); }
    .intro { max-width:650px; margin:14px 0 0; color:var(--muted); }
    main { padding:24px 0 56px; }
    .toolbar { display:flex; align-items:center; justify-content:space-between; gap:16px; margin-bottom:18px; }
    .filter-controls { display:flex; flex-wrap:wrap; align-items:end; gap:12px; }
    .filter-field { display:grid; gap:4px; color:var(--muted); font-size:.82rem; font-weight:700; }
    .count { margin:0; color:var(--muted); }
    .search { width:min(360px,100%); min-height:44px; padding:10px 13px; border:1px solid #aebcb5; border-radius:4px; background:#fff; color:var(--ink); font:inherit; }
    .category-filter { width:min(280px,100%); min-height:44px; padding:9px 32px 9px 11px; border:1px solid #aebcb5; border-radius:4px; background:#fff; color:var(--ink); font:inherit; }
    .sort-filter { width:min(240px,100%); min-height:44px; padding:9px 32px 9px 11px; border:1px solid #aebcb5; border-radius:4px; background:#fff; color:var(--ink); font:inherit; }
    .search:focus { outline:3px solid #a9d3bf; outline-offset:2px; }
    .category-filter:focus { outline:3px solid #a9d3bf; outline-offset:2px; }
    .sort-filter:focus { outline:3px solid #a9d3bf; outline-offset:2px; }
    .sr-only { position:absolute; width:1px; height:1px; overflow:hidden; clip:rect(0,0,0,0); white-space:nowrap; }
    .warning { margin:0 0 16px; padding:12px 14px; border-left:3px solid var(--orange); background:#fff2eb; }
    .product-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; }
    .pagination { display:flex; align-items:center; justify-content:center; gap:8px; margin-top:24px; }
    .page-numbers { display:flex; flex-wrap:wrap; justify-content:center; gap:6px; }
    .page-button { min-width:40px; min-height:40px; padding:7px 10px; border:1px solid var(--line); border-radius:4px; background:#fff; color:var(--ink); font:inherit; cursor:pointer; }
    .page-button:hover:not(:disabled), .page-button[aria-current="page"] { border-color:var(--green); background:var(--green); color:#fff; }
    .page-button:disabled { cursor:default; opacity:.45; }
    .page-status { min-width:92px; color:var(--muted); font-size:.88rem; text-align:center; }
    .product-card { min-width:0; padding:19px; border:1px solid var(--line); border-top:3px solid var(--green); background:#fff; }
    .card-topline { display:flex; align-items:baseline; justify-content:space-between; gap:12px; color:var(--muted); font-size:.75rem; font-weight:700; }
    .price { flex:0 0 auto; color:var(--orange); font-size:1.12rem; }
    .category-label { width:fit-content; margin:0 0 8px; padding:2px 8px; background:#e3f1e9; color:var(--green); font-size:.76rem; font-weight:700; }
    h2 { margin:11px 0 7px; font:700 1.35rem/1.2 var(--serif); overflow-wrap:anywhere; }
    .summary { margin:0 0 14px; color:var(--muted); }
    .spec-list { margin:0; }
    .spec-row { display:grid; grid-template-columns:minmax(115px,.8fr) minmax(0,1.2fr); gap:10px; padding:7px 0; border-top:1px solid #edf0ed; font-size:.88rem; }
    .spec-row dt, .muted { color:var(--muted); }
    .spec-row dd { margin:0; font-weight:600; overflow-wrap:anywhere; }
    details { margin-top:12px; border-top:1px solid var(--line); }
    summary { padding:11px 0 4px; color:var(--green); cursor:pointer; font-weight:700; }
    .full-specs { max-height:360px; overflow:auto; padding-right:4px; }
    .product-link { display:inline-block; margin-top:14px; color:var(--green); font-weight:700; text-underline-offset:3px; }
    .empty-state { grid-column:1 / -1; padding:24px; background:#fff; }
    footer { padding:18px 20px; border-top:1px solid var(--line); color:var(--muted); font-size:.82rem; text-align:center; }
    @media (max-width:720px) {
      .masthead-inner, main { width:min(100% - 28px,560px); }
      .masthead-inner { padding:30px 0 24px; }
      h1 { font-size:2rem; }
      .toolbar { align-items:stretch; flex-direction:column; }
    .filter-controls { align-items:stretch; flex-direction:column; }
        .search, .category-filter, .sort-filter { width:100%; }
      .product-grid { grid-template-columns:minmax(0,1fr); }
      .product-card { padding:16px; }
    }
  </style>
</head>
<body>
  <header class="masthead"><div class="masthead-inner">
    <p class="eyebrow">Catálogo LDLC · Informática</p>
    <h1>Componentes para tu próximo equipo</h1>
    <p class="intro">Productos recopilados en la categoría de componentes, con precio y ficha técnica.</p>
  </div></header>
  <main>
    <div class="toolbar">
      <p class="count" id="result-count" aria-live="polite">{{COUNT}} productos</p>
            <div class="filter-controls">
                <label class="filter-field">Buscar
                    <input class="search" id="search" type="search" placeholder="Nombre o característica">
                </label>
                <label class="filter-field">Categoría
                    <select class="category-filter" id="category-filter">{{CATEGORY_OPTIONS}}</select>
                </label>
                <label class="filter-field">Ordenar por precio
                    <select class="sort-filter" id="sort-filter">
                        <option value="">Relevancia</option>
                        <option value="price-asc">Precio: más bajo primero</option>
                        <option value="price-desc">Precio: más alto primero</option>
                    </select>
                </label>
            </div>
    </div>
    {{NOTICE}}
    <section class="product-grid" aria-label="Lista de productos">{{CARDS}}</section>
        <nav class="pagination" id="pagination" aria-label="Paginación de productos">
            <button class="page-button" id="previous-page" type="button">Anterior</button>
            <div class="page-numbers" id="page-numbers"></div>
            <span class="page-status" id="page-status" aria-live="polite"></span>
            <button class="page-button" id="next-page" type="button">Siguiente</button>
        </nav>
  </main>
  <footer>Datos cargados desde ldlc.json</footer>
  <script>
    const search = document.querySelector("#search");
    const categoryFilter = document.querySelector("#category-filter");
    const sortFilter = document.querySelector("#sort-filter");
    const cards = [...document.querySelectorAll(".product-card")];
    const count = document.querySelector("#result-count");
        const pagination = document.querySelector("#pagination");
        const pageNumbers = document.querySelector("#page-numbers");
        const pageStatus = document.querySelector("#page-status");
        const previousPage = document.querySelector("#previous-page");
        const nextPage = document.querySelector("#next-page");
        const pageSize = 24;
        let currentPage = 1;
    const normalize = (value) => value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();

        function renderResults() {
      const query = normalize(search.value.trim());
            const selectedCategory = categoryFilter.value;
            const matchingCards = cards.filter((card) => {
                const matchesSearch = normalize(card.dataset.search).includes(query);
                const matchesCategory = !selectedCategory || card.dataset.category === selectedCategory;
                return matchesSearch && matchesCategory;
            });
            const sortOrder = sortFilter.value;
            if (sortOrder) {
                matchingCards.sort((left, right) => {
                    const leftPrice = Number.parseInt(left.dataset.price, 10);
                    const rightPrice = Number.parseInt(right.dataset.price, 10);
                    const leftHasPrice = Number.isFinite(leftPrice);
                    const rightHasPrice = Number.isFinite(rightPrice);
                    if (!leftHasPrice || !rightHasPrice) {
                        return leftHasPrice === rightHasPrice ? 0 : leftHasPrice ? -1 : 1;
                    }
                    return sortOrder === "price-asc"
                        ? leftPrice - rightPrice
                        : rightPrice - leftPrice;
                });
            }
            const totalPages = Math.ceil(matchingCards.length / pageSize);
            currentPage = Math.min(currentPage, Math.max(totalPages, 1));
            const firstVisible = (currentPage - 1) * pageSize;

            for (const card of cards) card.hidden = true;
            for (const card of matchingCards.slice(firstVisible, firstVisible + pageSize)) {
                card.hidden = false;
      }

            count.textContent = `${matchingCards.length} ${matchingCards.length === 1 ? "producto" : "productos"}`;
            pageStatus.textContent = totalPages ? `Página ${currentPage} de ${totalPages}` : "Sin resultados";
            previousPage.disabled = currentPage <= 1;
            nextPage.disabled = currentPage >= totalPages;
            pagination.hidden = totalPages <= 1;
            pageNumbers.replaceChildren();

            const firstPage = Math.max(1, Math.min(currentPage - 2, totalPages - 4));
            const lastPage = Math.min(totalPages, firstPage + 4);
            for (let page = firstPage; page <= lastPage; page += 1) {
                const button = document.createElement("button");
                button.className = "page-button";
                button.type = "button";
                button.textContent = page;
                button.setAttribute("aria-label", `Página ${page}`);
                if (page === currentPage) button.setAttribute("aria-current", "page");
                button.addEventListener("click", () => {
                    currentPage = page;
                    renderResults();
                });
                pageNumbers.append(button);
            }
        }

        previousPage.addEventListener("click", () => {
            currentPage -= 1;
            renderResults();
        });
        nextPage.addEventListener("click", () => {
            currentPage += 1;
            renderResults();
        });
        search.addEventListener("input", () => {
            currentPage = 1;
            renderResults();
        });
        categoryFilter.addEventListener("change", () => {
            currentPage = 1;
            renderResults();
        });
        sortFilter.addEventListener("change", () => {
            currentPage = 1;
            renderResults();
        });
        renderResults();
  </script>
</body>
</html>
"""
    return (
        template.replace("{{COUNT}}", str(len(products)))
        .replace("{{NOTICE}}", notice)
        .replace("{{CARDS}}", cards)
        .replace("{{CATEGORY_OPTIONS}}", "".join(category_options))
    )


def main():
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"No se encontró el archivo de datos: {INPUT_PATH}")

    products, incomplete = load_products()
    if not isinstance(products, list):
        raise ValueError("El JSON debe contener una lista de productos.")

    products = [product for product in products if isinstance(product, dict)]
    OUTPUT_PATH.write_text(render_page(products, incomplete), encoding="utf-8")
    status = "; JSON incompleto" if incomplete else ""
    print(f"Página creada: {OUTPUT_PATH} ({len(products)} productos{status})")


if __name__ == "__main__":
    main()
