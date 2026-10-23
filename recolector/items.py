# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class RecolectorItem(scrapy.Item):
    id = scrapy.Field()          # sha256 of the product URL (stable between crawls)
    titulo = scrapy.Field()      # product name
    precio = scrapy.Field()      # float, e.g. 819.95
    moneda = scrapy.Field()      # "EUR"
    texto = scrapy.Field()       # description (short spec line + long description)
    marca = scrapy.Field()
    categorias = scrapy.Field()  # breadcrumb, e.g. ["Computing", "Components", ...]
    url = scrapy.Field()
    fuente = scrapy.Field()
