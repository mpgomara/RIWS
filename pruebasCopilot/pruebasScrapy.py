from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import scrapy
from scrapy.crawler import CrawlerProcess


class LDLCSpider(scrapy.Spider):
    name = "ldlc_components"
    allowed_domains = ["ldlc.com"]
    components_path = "/es-es/informatica/piezas-de-informatica/"
    start_urls = [
        "https://www.ldlc.com/es-es/informatica/piezas-de-informatica/cint4197/"
    ]

    def parse(self, response):
        for href in response.css("a[href]::attr(href)").getall():
            url = response.urljoin(href)
            parsed_url = urlsplit(url)

            if parsed_url.path.startswith("/es-es/ficha/"):
                yield response.follow(url, callback=self.parse_product)
            elif (
                parsed_url.path.startswith(self.components_path)
                and "+" not in parsed_url.path
            ):
                category_url = urlunsplit(
                    (parsed_url.scheme, parsed_url.netloc, parsed_url.path, "", "")
                )
                yield response.follow(category_url, callback=self.parse)

    def parse_product(self, response):
        name = " ".join(response.css("h1::text").getall()).strip()
        price = response.css(".product-infoPrice .price")
        if not price:
            price = response.css(".price")

        characteristics = {}
        for row in response.css(".specsTech tr"):
            cells = [
                " ".join(cell.css("::text").getall()).strip()
                for cell in row.css("th, td")
            ]
            cells = [cell for cell in cells if cell]
            if len(cells) >= 3:
                key = f"{cells[-3]}: {cells[-2]}"
                value = cells[-1]
            elif len(cells) == 2:
                key, value = cells
            else:
                continue
            characteristics[key] = value

        yield {
            "nombre": name,
            "caracteristicas": {
                "resumen": " ".join(response.css("h2::text").getall()[:1]).strip(),
                "ficha_tecnica": characteristics,
            },
            "precio": " ".join(price.css("::text").getall()).strip() or None,
            "url": response.url,
        }


if __name__ == "__main__":
    process = CrawlerProcess(
        settings={
            "FEEDS": {
                str(Path(__file__).resolve().parent / "ldlc.json"): {
                    "format": "json",
                    "encoding": "utf8",
                    "overwrite": True,
                }
            },
            "ROBOTSTXT_OBEY": True,
            "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
            "DOWNLOAD_DELAY": 1,
            "USER_AGENT": "RIWS-Scrapy-Practice/1.0",
            "LOG_LEVEL": "INFO",
        }
    )
    process.crawl(LDLCSpider)
    process.start()
