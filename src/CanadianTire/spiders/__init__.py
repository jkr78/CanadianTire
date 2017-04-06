# -*- coding: utf-8 -*-

# Support xrange in python 3
try:
    xrange
except NameError:
    xrange = range


try:
    import simplejson as json
except ImportError:
    import json

try:
    from urllib import quote
except ImportError:
    from urllib.parse import quote  # 3.0+

try:
    from urlparse import urljoin
except ImportError:
    from urllib.parse import urljoin  # 3.0+

try:
    from urllib import pathname2url
except ImportError:
    from urllib.request import pathname2url

from copy import copy
import calendar
import datetime
import logging

from six import string_types
from scrapy import (
    Spider,
    Request,
    signals,
)
from scrapy.mail import MailSender

from CanadianTire.items import CanadianTireProduct


class CanadianTireSpider(Spider):
    name = "CanadianTire"
    # allowed_domains = ["www.canadiantire.ca"]
    start_urls = ['http://www.canadiantire.ca'
                  '/en/household-pets'
                  '/cleaning-supplies-vacuums/vacuums-floor-care'
                  '/mops-buckets.html']

    PRICE_AVAIL_BASE_URL = 'http://www.canadiantire.ca/ESB/PriceAvailability'
    MAX_PROD_COUNT_IN_PRICE_AVAIL = 20

    STATS_BASE_URL = 'http://api.bazaarvoice.com/data/statistics.json'

    QUERY_STORE = '0144'

    SEARCH_REQARGS = {
        'site': 'ct',
        'store': QUERY_STORE,
        'x1': 'c.cat-level-1',
        'q1': 'Living',
        'x2': 'c.cat-level-2',
        'q2': 'Cleaning Supplies \x26 Vacuums',
        'x3': 'c.cat-level-3',
        'q3': 'Vacuums \x26 Floor Care',
        'x4': 'c.cat-level-4',
        'q4': 'Mops \x26 Buckets',
        'format': 'json',
        'count': '36',
        'q': '*',
    }

    PRICE_AVAIL_REQARGS = {
        'Store': QUERY_STORE,
        'Banner': 'CTR',
        'Kiosk': 'FALSE',
        'Language': 'E',
    }

    STATS_REQARGS = {
        'apiversion': '5.4',
        'passkey': 'l45q9ns76mpthbmmr0rdmebue',
        'stats': 'reviews',
    }

    product_index = {}

    def check_field(self, field):
        errs = []

        if 'pdp-url' not in field:
            errs.append('pdp-url not in field')
        if 'prod-id' not in field:
            errs.append('prod-id not in field')
        if 'sku-id' not in field:
            errs.append('sku-id not in field')
        if 'prod-name' not in field:
            errs.append('prod-name not in field')
        if 'sku-number' not in field:
            errs.append('sku-number not in field')

        return errs

    def check_price_info(self, pi):
        errs = []

        if 'Product' not in pi:
            errs.append('Product not in price info')
        if 'PartNumber' not in pi:
            errs.append('PartNumber not in price info')
        if 'Price' not in pi:
            errs.append('Price not in price info')

        return errs

    def check_stats(self, stats):
        errs = []

        if 'ProductStatistics' not in stats:
            errs.append('ProductStatistics not in stats')
        else:
            if 'ProductId' not in stats['ProductStatistics']:
                errs.append('ProductStatistics.ProductId not in stats')

        return errs

    def report_error(self, msg, errs=None):
        logger = logging.getLogger()

        if not errs:
            r = '{0}'.format(msg)
        elif isinstance(errs, string_types):
            r = '{0}: {1}'.format(msg, errs)
        elif isinstance(errs, dict):
            r = '{0}: {1}'.format(msg, errs)
        elif len(errs) == 1:
            r = '{0}: {1}'.format(msg, errs[0])
        else:
            r = '{0}:\n{1}'.format(
                msg,
                '\n'.join(['{0}'.format(s) for s in errs]))

        logger.error(r)

        email_to = self.settings.getlist('CANADIAN_TIRE_ERROR_MAIL_TO')
        if email_to:
            mailer = MailSender.from_settings(self.settings)
            email_subject = self.settings.get(
                'CANADIAN_TIRE_ERROR_MAIL_SUBJECT',
                'CanadianTire Error')
            mailer.send(to=email_to, subject=email_subject, body=r)

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(CanadianTireSpider, cls).from_crawler(
            crawler, *args, **kwargs)

        crawler.signals.connect(spider.on_error, signal=signals.spider_error)
        return spider

    def parse(self, response):
        el = response.xpath(
            '//div[contains(@class, "search-results-grid")'
            ' and contains(@class, "grid--grid-view")]/@data-config')

        sdc = json.loads(el.extract_first())

        q = '&'.join(
            ('{0}={1}'.format(k, quote(self.SEARCH_REQARGS[k]))
             for k in self.SEARCH_REQARGS))
        url = urljoin(
            'http://',
            pathname2url(sdc['productSnpUri']) + '?' + q)

        request = Request(
            url,
            callback=self.parse_search)
        return request

    def price_avail_urls(self, prods):
        """
        For some reason CanadianTire requests only 20 prices.
        It seems server could support more than this but I will
        make it act as original, no more than 20 prices per request.
        It can be they check on length of url, not on no of prices,
        in that case code needs to be redone here.
        """

        def build_url(prods):
            reqargs = copy(self.PRICE_AVAIL_REQARGS)
            reqargs['_'] = str(calendar.timegm(
                datetime.datetime.utcnow().utctimetuple()))
            reqargs['Product'] = ','.join(prods)
            q = '&'.join('{0}={1}'.format(k, quote(reqargs[k]))
                         for k in reqargs)
            url = urljoin(self.PRICE_AVAIL_BASE_URL, '?' + q)
            return url

        urls = []
        while prods:
            urls.append(build_url(
                prods[:self.MAX_PROD_COUNT_IN_PRICE_AVAIL]))
            prods = prods[self.MAX_PROD_COUNT_IN_PRICE_AVAIL:]

        return urls

    def stats_url(self, prods):
        reqargs = copy(self.STATS_REQARGS)
        reqargs['_'] = str(calendar.timegm(
            datetime.datetime.utcnow().utctimetuple()))
        reqargs['filter'] = 'productid:'
        reqargs['filter'] += ','.join(prods)
        q = '&'.join('{0}={1}'.format(k, quote(reqargs[k]))
                     for k in reqargs)
        url = urljoin(self.STATS_BASE_URL, '?' + q)
        return url

    def parse_search(self, response):
        def product_number_formatter(pn):
            # formats product number as on website
            pn1, pn2, pn3 = str(pn).split('-')
            return '{0}-{1}-{2}'.format(
                pn1.zfill(3), pn2.zfill(4), pn3.zfill(1))

        try:
            o = json.loads(response.body_as_unicode())
        except ValueError as e:
            self.report_error(
                'parse_search: Cannot parse response as JSON',
                errs=[str(e), response.body_as_unicode()])
            return

        results = o.get('results', None)
        if not results:
            # This should not happen
            self.report_error(
                'parse_search: No "results" in JSON response',
                errs=str(o))
            return

        prods = []
        for result in results:
            field = result.get("field", None)
            if not field:
                self.report_error(
                    'parse_search: No "field" in "results" in JSON response',
                    errs=str(o))
                return

            errs = self.check_field(field)
            if errs:
                self.report_error(
                    'parse_search: Bad field',
                    errs)
                continue

            product = CanadianTireProduct(
                url=field['pdp-url'],
                image_url=field.get('thumb-img-url', ''),
                pCode=field['prod-id'],
                sku_id=field['sku-id'].split('|')[0],
                product_name=field['prod-name'],
                product_number=product_number_formatter(
                    field['sku-number'].split('|')[0]),
            )

            # we will need to update products, but we cannot
            # use meta[] since one request will contain many
            # products. it is easier to cache the products
            # and use index
            if field['prod-id'] in product:
                self.report_error(
                    'parse_search: product {0} already exist in index',
                    errs=product)
            self.product_index[field['prod-id']] = product
            prods.append(field['prod-id'])

        if 'pagination' in o:
            next_url = o['pagination'].get('next')
            if next_url:
                yield Request(
                    response.urljoin(next_url),
                    self.parse_search)

        yield Request(
            self.stats_url(prods),
            callback=self.parse_stats)

    def parse_stats(self, response):
        try:
            o = json.loads(response.body_as_unicode())
        except ValueError as e:
            self.report_error(
                'parse_stats: Cannot parse response as JSON',
                errs=[str(e), response.body_as_unicode()])
            return

        results = o.get('Results', None)
        if not results:
            # This should not happen
            self.report_error(
                'parse_stats: No "results" in JSON response',
                errs=str(o))
            return

        prods = []
        for result in results:
            errs = self.check_stats(result)
            if errs:
                self.report_error(
                    'parse_stats: Bad stats info',
                    errs)
                continue

            stats = result['ProductStatistics']
            if stats['ProductId'] not in self.product_index:
                self.report_error(
                    'parse_price_avail: Missing product for stats',
                    errs=[str(stats)])
                continue

            product = self.product_index[stats['ProductId']]

            if 'ReviewStatistics' in stats:
                rating = stats['ReviewStatistics'].get(
                    'AverageOverallRating', None)

                if rating is None:
                    rating = 0
                product['rating'] = rating

            prods.append(stats['ProductId'])

        urls = self.price_avail_urls(prods)
        for url in urls:
            yield Request(
                url,
                callback=self.parse_price_avail)

    def parse_price_avail(self, response):
        try:
            o = json.loads(response.body_as_unicode())
        except ValueError as e:
            self.report_error(
                'parse_price_avail: Cannot parse response as JSON',
                errs=[str(e), response.body_as_unicode()])
            return

        for pi in o:
            errs = self.check_price_info(pi)
            if errs:
                self.report_error(
                    'parse_price_avail: Bad price info',
                    errs)
                continue

            if pi['Product'] not in self.product_index:
                self.report_error(
                    'parse_price_avail: Missing product for price',
                    errs=str(pi))
                continue

            product = self.product_index[pi['Product']]

            product['part_number'] = pi['PartNumber']
            product['size'] = pi.get('Quantity', 0)
            product['price'] = pi['Price']
            if 'Promo' in pi:
                product['sale_price'] = pi['Promo'].get('Price', None)

            del self.product_index[pi['Product']]
            yield product

    def closed(self, reason):
        if len(self.product_index):
            self.report_error(
                'closed: {0} products lost'.format(
                    len(self.product_index)),
                errs=self.product_index)

    @staticmethod
    def on_error(failure, response, spider):
        report_error = getattr(spider, 'report_error', None)
        if report_error:
            report_error(
                'error: Failure occured during scraping',
                errs=[failure, response])
