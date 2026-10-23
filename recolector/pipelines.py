# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import hashlib
from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem


class RecolectorPipeline:
    def __init__(self):
            self.vistos = set()
    
    def process_item(self, item, spider=None):
        a = ItemAdapter(item)
        for campo in ("titulo", "texto", "marca"):
            a[campo] = " ".join((a.get(campo) or "").split())
        if not a["titulo"] or not a.get("url"):
            raise DropItem("Falta titulo o URL")
        if a.get("precio") is None:
            raise DropItem("Falta precio: " + a["url"])
        # The id depends only on the URL, so re-crawling updates the same
        # Elasticsearch document instead of creating a duplicate when the price changes.
        a["id"] = hashlib.sha256(a["url"].encode()).hexdigest()
        if a["id"] in self.vistos:
            raise DropItem("Duplicado: " + a["url"])
        self.vistos.add(a["id"])
        return item
