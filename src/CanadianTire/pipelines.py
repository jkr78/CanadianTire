# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html


# Support unicode in python 3
try:
    unicode
except NameError:
    unicode = str


import six
from scrapy.utils.python import to_bytes
from scrapy.exporters import BaseItemExporter

try:
    import MySQLdb

    def quote_string(s):
        return '"' + MySQLdb.escape_string(unicode(s)) + '"'

except ImportError:
    import json

    def quote_string(s):
        return json.dumps(unicode(s), ensure_ascii=False)

from CanadianTire.items import CanadianTireProduct


# In future rewrite this exporter to support fetching field
# mappings directly from Item like in ORM
class MySQLExporterForCanadianTire(BaseItemExporter):
    def __init__(self, file, **kwargs):
        self._configure(kwargs, dont_fail=True)
        if not self.encoding:
            self.encoding = 'utf-8'
        self.file = file
        self.table_name = 'CanadianTireProduct'
        self.primary_keys = ['pCode']

    def export_item(self, item):
        if not isinstance(item, CanadianTireProduct):
            self.file.write(to_bytes(
                repr(item),
                self.encoding,
                errors='xmlcharrefreplace'))
            return

        field_mapping = {
            'url': ('url', unicode),
            'image_url': ('image_url', unicode),
            'pCode': ('pCode', unicode),
            'sku_id': ('sku_id', unicode),
            'part_number': ('part_number', unicode),
            'size': ('size', float),
            'product_name': ('product_name', unicode),
            'price': ('price', float),
            'sale_price': ('sale_price', float),
            'rating': ('rating', float),
            'product_number': ('product_number', unicode),
        }

        insert_fields = []
        insert_values = []
        have_primary_key = False
        for k in field_mapping:
            field_name, formatter = field_mapping[k]
            if field_name in self.primary_keys:
                have_primary_key = True

            insert_fields.append(field_name)
            value = formatter(item[k]) if item[k] is not None else None
            if value is None:
                value = 'NULL'
            elif isinstance(value, six.text_type):
                value = quote_string(value)
            else:
                value = str(value)

            insert_values.append(value)

        sql = u'INSERT INTO {0}({1}) VALUES ({2})'.format(
            self.table_name,
            u','.join(insert_fields),
            u','.join(insert_values))

        if have_primary_key:
            update_fields = (
                u'{0}={1}'.format(k, v)
                for k, v in zip(insert_fields, insert_values)
                if k not in self.primary_keys)

            sql2 = u' ON DUPLICATE KEY UPDATE {0}'.format(
                u','.join(update_fields))

            sql += sql2

        sql += u';\n'
        self.file.write(to_bytes(sql, self.encoding))


class CanadianTirePipeline(object):
    def process_item(self, item, spider):
        return item
