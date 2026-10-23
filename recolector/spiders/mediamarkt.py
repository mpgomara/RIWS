"""Spider for https://www.mediamarkt.es/ driven by its XML sitemaps.

The sitemaps only LIST urls (no product data). This spider reads them to discover product
URLs, then downloads each product page and extracts name, price and description.

Usage (from the project root):
  scrapy crawl mediamarkt -s CLOSESPIDER_ITEMCOUNT=50 -O recursos.jsonl      # quick test
  scrapy crawl mediamarkt -a slug=frigorifico -a max_sitemaps=2 -O recursos.jsonl           # scope by URL words
  scrapy crawl mediamarkt -a slug="portatil gaming" -a max_sitemaps=5 -a limit=300 -O recursos.jsonl
  scrapy crawl mediamarkt -a category="Frigoríficos" -O recursos.jsonl   # scope by breadcrumb

Scope options:
  slug      words that must ALL appear in the product URL (cheap: filters before downloading).
  category  text that must appear in the breadcrumb (accurate, but the page is downloaded first).
  limit     max number of product URLs to request.
  max_sitemaps  how many of the 56 product sitemaps to read (each holds many thousands of URLs).
"""
import json
import re

import scrapy
from scrapy.exceptions import CloseSpider
from scrapy.spiders import SitemapSpider

from recolector.items import RecolectorItem


def parse_price_es(texto):
    """Spanish text price -> float. '79,99€' -> 79.99 ; '1.059,99 €' -> 1059.99 ; '49€' -> 49.0"""
    if not texto:
        return None
    t = texto.replace(" ", " ").replace(" ", " ")
    m = re.search(r"(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d{1,2}|[–-]))?\s*€", t)
    if not m:
        return None
    euros = m.group(1).replace(".", "")
    cents = m.group(2) if (m.group(2) or "").isdigit() else "0"
    return float(f"{euros}.{cents.ljust(2, '0')}")


def price_from_page_text(nodos):
    """MediaMarkt shows '559,–' visually plus a hidden '559,00€'. Use only amounts written with
    two-digit cents, count them, and take the cheapest one that appears at least twice
    (current price and old price are repeated in the page; financing/shipping amounts are not)."""
    texto = " ".join(nodos).replace("\u00a0", " ").replace("\u202f", " ")
    cifras = []
    for m in re.finditer(r"(?<![\d.,])(\d{1,3}(?:\.\d{3})+|\d+),(\d{2})\s*€", texto):
        cifras.append(float(f"{m.group(1).replace('.', '')}.{m.group(2)}"))
    if not cifras:
        return None
    from collections import Counter
    repetidos = [v for v, n in Counter(cifras).items() if n >= 2]
    return min(repetidos) if repetidos else cifras[0]


def parse_price_machine(valor):
    """Price from JSON-LD / meta tags: dot decimal ('79.99'), sometimes a number."""
    if valor in (None, ""):
        return None
    try:
        return float(str(valor).strip().replace(",", "."))
    except ValueError:
        return parse_price_es(str(valor))


class MediamarktSpider(SitemapSpider):
    name = "mediamarkt"
    allowed_domains = ["mediamarkt.es"]
    # Index (117 child sitemaps) -> only the product-detail ones are followed.
    sitemap_urls = ["https://www.mediamarkt.es/sitemaps/sitemap-index.xml"]
    sitemap_follow = [r"productdetailspages"]  # 56 product sitemaps; NOT productimages/search/facet
    sitemap_rules = [("", "parse_product")]

    # Let 403/429 reach the callback so we can notice a block and stop instead of hammering.
    custom_settings = {"HTTPERROR_ALLOWED_CODES": [403, 429]}

    def __init__(self, slug=None, category=None, limit=None, max_sitemaps=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.slug_words = (slug or "").lower().split()
        self.category = (category or "").lower().strip()
        self.limit = int(limit) if limit else None
        self.max_sitemaps = int(max_sitemaps) if max_sitemaps else None
        self.sitemaps_seen = 0
        self.requested = 0
        self.blocked = 0

    # ---------- discovery ----------
    def sitemap_filter(self, entries):
        for e in entries:
            loc = e["loc"]
            if loc.endswith(".xml"):  # child sitemaps
                if self.max_sitemaps and "productdetailspages" in loc:
                    if self.sitemaps_seen >= self.max_sitemaps:
                        continue
                    self.sitemaps_seen += 1
                yield e
                continue
            if self.slug_words and not all(w in loc.lower() for w in self.slug_words):
                continue
            if self.limit and self.requested >= self.limit:
                return
            self.requested += 1
            yield e

    # ---------- product pages ----------
    def parse_product(self, response):
        if response.status in (403, 429):
            self.blocked += 1
            self.logger.warning("Blocked (%s) at %s", response.status, response.url)
            if self.blocked >= 5:
                raise CloseSpider("blocked_by_site")
            return

        ld = self._json_ld(response, "Product")
        offers = ld.get("offers") or {}
        if isinstance(offers, list):
            offers = offers[0] if offers else {}

        titulo = (ld.get("name")
                  or " ".join(response.css("h1 ::text").getall())
                  or response.css("meta[property='og:title']::attr(content)").get(""))

        precio = parse_price_machine(offers.get("price") or offers.get("lowPrice"))
        if precio is None:
            precio = parse_price_machine(response.css(
                "meta[property='product:price:amount']::attr(content), "
                "meta[itemprop='price']::attr(content)").get())
        if precio is None:  # TODO verify against the real page (see README note)
            nodos = response.xpath(
                "//body//text()[not(ancestor::script) and not(ancestor::style) and not(ancestor::noscript)]"
            ).getall()
            precio = price_from_page_text(nodos)

        texto = (ld.get("description")
                 or response.css("meta[name='description']::attr(content)").get()
                 or response.css("meta[property='og:description']::attr(content)").get(""))

        marca = ld.get("brand")
        if isinstance(marca, dict):
            marca = marca.get("name")
        if not marca:
            marca = response.css(
                "meta[property='product:brand']::attr(content), meta[property='og:brand']::attr(content), "
                "meta[itemprop='brand']::attr(content), [itemprop='brand'] ::text").get("")

        categorias = self._breadcrumb(response)
        if self.category and not any(self.category in c.lower() for c in categorias):
            return

        yield RecolectorItem(
            titulo=titulo,
            precio=precio,
            moneda=offers.get("priceCurrency") or "EUR",
            texto=texto,
            marca=marca or "",
            categorias=categorias,
            url=response.url,
            fuente="mediamarkt.es",
        )

    # ---------- helpers ----------
    @staticmethod
    def _json_ld_all(response):
        for raw in response.css("script[type='application/ld+json']::text").getall():
            try:
                data = json.loads(raw)
            except ValueError:
                continue
            stack = data if isinstance(data, list) else [data]
            while stack:
                d = stack.pop()
                if isinstance(d, dict):
                    yield d
                    if "@graph" in d:
                        stack.extend(d["@graph"])

    def _json_ld(self, response, tipo):
        for d in self._json_ld_all(response):
            t = d.get("@type")
            if t == tipo or (isinstance(t, list) and tipo in t):
                return d
        return {}

    def _breadcrumb(self, response):
        bc = self._json_ld(response, "BreadcrumbList")
        nombres = []
        for el in sorted(bc.get("itemListElement", []) or [], key=lambda x: x.get("position", 0)):
            item = el.get("item")
            nombre = el.get("name") or (item.get("name") if isinstance(item, dict) else None)
            if nombre:
                nombres.append(nombre.strip())
        if nombres:
            if len(nombres) > 1:
                nombres = nombres[:-1]  # last = the product itself
            return [n for n in nombres if n.lower() not in ("home", "inicio")]
        crumbs = [" ".join(c.split()) for c in response.css(
            "nav[aria-label*=readcrumb] a ::text, [class*=readcrumb] a ::text").getall()]
        return [c for c in crumbs if c and c.lower() not in ("home", "inicio") and not c.lower().startswith("volver a")]
