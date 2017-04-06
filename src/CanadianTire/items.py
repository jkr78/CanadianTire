# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class CanadianTireProduct(scrapy.Item):
    url = scrapy.Field()
    image_url = scrapy.Field()
    pCode = scrapy.Field()
    sku_id = scrapy.Field()
    part_number = scrapy.Field()
    size = scrapy.Field()
    product_name = scrapy.Field()
    price = scrapy.Field()
    sale_price = scrapy.Field()  # if not on sale then None
    rating = scrapy.Field()
    product_number = scrapy.Field()  # as displayed on website

    def __init__(self, *args, **kwargs):
        super(CanadianTireProduct, self).__init__(*args, **kwargs)
        # some defaults
        self.setdefault('sale_price', None)
        self.setdefault('rating', 0)
