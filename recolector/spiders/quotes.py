import scrapy


class QuotesSpider(scrapy.Spider):
    name = "quotes"
    allowed_domains = ["quotes.toscrape.com"]
    start_urls = ["https://quotes.toscrape.com"]

    def parse(self, response):
        for q in response.css("div.quote"):
            autor = q.css("small.author::text").get("")
            yield {
                "titulo": "Cita de " + autor,
                "texto": q.css("span.text::text").get(""),
                "autor": autor,
                "categorias": q.css("a.tag::text").getall(),
                "url": response.url,
                "fuente": "quotes.toscrape.com"
            }
        siguiente = response.css("li.next a::attr(href)").get()
        if siguiente:
            yield response.follow(siguiente, callback=self.parse)
