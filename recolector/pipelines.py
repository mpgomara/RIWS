# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import hashlib
from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem


class RecolectorPipeline:
    def process_item(self, item, spider=None):
        a = ItemAdapter(item)
        a["texto"] = " ".join(a.get("texto", "").split())
        if not a["texto"] or not a.get("url"):
            raise DropItem("Falta texto o URL")
        clave = a["url"] + "|" + a["texto"]
        a["id"] = hashlib.sha256(clave.encode()).hexdigest()
        return item
