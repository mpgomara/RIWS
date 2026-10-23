"""Spider for https://www.ldlc.com/en/

Usage (from the project root):
  scrapy crawl ldlc -O recursos.jsonl
  scrapy crawl ldlc -a category=https://www.ldlc.com/en/computing/laptop/c4265/ -a max_pages=3 -O recursos.jsonl
  scrapy crawl ldlc -a category=URL1,URL2 -a query="rtx 5070" -O recursos.jsonl

NOTE: robots.txt disallows /en/search/, so the site's own search cannot be crawled while
ROBOTSTXT_OBEY = True. Scope is controlled with category URLs (+ an optional local keyword
filter) instead.
"""
import json
import re

import scrapy

from recolector.items import RecolectorItem

PRODUCT_RE = re.compile(r"/product/PB\d+\.html")


def parse_price(texto):
    """'819€95' -> 819.95 ; '1 059€95' -> 1059.95 ; '819.95' -> 819.95"""
    if not texto:
        return None
    t = texto.replace("\u00a0", " ").replace("\u202f", " ")
    m = re.search(r"(\d[\d ]*)€(\d{1,2})(?!\d)", t)      # 819€95
    if not m:
        m = re.search(r"(\d[\d ]*)[.,](\d{1,2})(?!\d)", t)  # 129,90 / 819.95
    if m:
        return float(f"{m.group(1).replace(' ', '')}.{m.group(2).ljust(2, '0')}")
    m = re.search(r"(\d[\d ]*)", t)                          # 49 €
    return float(m.group(1).replace(" ", "")) if m else None


class LdlcSpider(scrapy.Spider):
    name = "ldlc"
    allowed_domains = ["ldlc.com"]
    default_category = "https://www.ldlc.com/en/computing/components/graphics-card/c4684/"

    def __init__(self, category=None, query=None, max_pages=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_urls = [u.strip() for u in (category or self.default_category).split(",") if u.strip()]
        self.query = (query or "").lower().split()
        self.max_pages = int(max_pages) if max_pages else None

    # ---------- listing pages ----------
    def parse(self, response):
        page = response.meta.get("page", 1)
        n_prod = 0

        items = response.css("li.pdt-item")  # TODO verify selector
        entries = []
        for li in items:
            href = li.css(".title-3 a::attr(href), h3 a::attr(href)").get()
            nombre = " ".join(li.css(".title-3 a ::text, h3 a ::text").getall())
            desc = " ".join(li.css(".pdt-desc ::text, .desc ::text").getall())
            if href:
                entries.append((href, nombre, desc))
        if not entries:  # fallback: any link that looks like a product page
            seen = set()
            for href in response.css("a::attr(href)").getall():
                if PRODUCT_RE.search(href) and href not in seen:
                    seen.add(href)
                    entries.append((href, "", ""))

        for href, nombre, desc in entries:
            if self.query and nombre:
                hay = (nombre + " " + desc).lower()
                if not all(w in hay for w in self.query):
                    continue
            n_prod += 1
            yield response.follow(
                href, callback=self.parse_product,
                meta={"desc_corta": " ".join(desc.split()), "listado": response.url},
            )

        # pagination: .../cNNNN/page2/
        if n_prod == 0 and not entries:
            return
        if self.max_pages and page >= self.max_pages:
            return
        for href in response.css("a::attr(href)").getall():
            m = re.search(r"/page(\d+)/?$", href)
            if m and int(m.group(1)) == page + 1:
                yield response.follow(href, callback=self.parse, meta={"page": page + 1})
                break

    # ---------- product pages ----------
    def parse_product(self, response):
        ld = self._json_ld_product(response)
        offers = ld.get("offers") or {}
        if isinstance(offers, list):
            offers = offers[0] if offers else {}

        titulo = (ld.get("name")
                  or " ".join(response.css("h1 ::text").getall())
                  or response.css("meta[property='og:title']::attr(content)").get(""))

        precio = None
        if offers.get("price") not in (None, ""):
            precio = parse_price(str(offers["price"]))
        if precio is None:
            precio = parse_price(response.css("meta[property='product:price:amount']::attr(content)").get())
        if precio is None:  # TODO verify selector
            for sel in ("aside .price ::text", ".price .price ::text", ".price ::text"):
                precio = parse_price("".join(response.css(sel).getall()))
                if precio is not None:
                    break

        larga = " ".join(response.css("#product-description ::text, .product-description ::text, #description ::text").getall())
        if not larga.strip():
            larga = ld.get("description") or response.css("meta[name='description']::attr(content)").get("")
        texto = " ".join(x for x in (response.meta.get("desc_corta", ""), larga) if x and x.strip())

        marca = ld.get("brand")
        if isinstance(marca, dict):
            marca = marca.get("name")

        crumbs = [" ".join(c.split()) for c in response.css(
            "nav[aria-label*=readcrumb] a ::text, .breadcrumb a ::text, ol.breadcrumb li ::text").getall()]
        categorias = [c for c in crumbs if c and c.lower() not in ("home", "ldlc")]

        yield RecolectorItem(
            titulo=titulo,
            precio=precio,
            moneda=offers.get("priceCurrency") or "EUR",
            texto=texto,
            marca=marca or "",
            categorias=categorias,
            url=response.url,
            fuente="ldlc.com",
        )

    @staticmethod
    def _json_ld_product(response):
        for raw in response.css("script[type='application/ld+json']::text").getall():
            try:
                data = json.loads(raw)
            except ValueError:
                continue
            for d in (data if isinstance(data, list) else [data]):
                if isinstance(d, dict) and d.get("@type") == "Product":
                    return d
        return {}
