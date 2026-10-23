from scrapy.exceptions import CloseSpider

class AccessDenialMiddleware:

    def process_response(self, request, response, spider):
        if response.status in (403, 429):
            spider.crawler.engine.close_spider(
                spider,
                reason=f"access_denied_{response.status}",
            )
            raise CloseSpider(
                f"Stopping after HTTP {response.status}"
            )

        return response