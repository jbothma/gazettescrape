# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class GazetteItem(scrapy.Item):
    label = scrapy.Field()
    published_date = scrapy.Field()
    file_urls = scrapy.Field()
    files = scrapy.Field()
    referrer = scrapy.Field()
