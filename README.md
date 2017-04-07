# CanadianTire scraper
canadiantire.ca - scraper written using Scrapy framework 

## Introduction

Scrapy must be installed and functional before running crawler
For Scrapy installation instructions, please consult:
[Scrapy Installation](https://doc.scrapy.org/en/latest/intro/install.html)

## Running

To install requirements (Scrapy) using pip:
	pip install -r requirements.txt

To install requirements (Scrapy) on Windows machine using pip:
	pip install -r requirements-win32.txt

To run:
	scrapy crawl CanadianTire --output=output.sql --output-format=mysql

It will output data to 'output.sql' file and output debug information
on screen

To output logs to log.txt file execute following command:
	scrapy crawl CanadianTire --output=output.sql --output-format=mysql --logfile=log.txt

## Requirements

Code is made for an interview.

Below is the requirements and how I understood it:
  1. Scrap product list from page: [Quick Search](http://www.canadiantire.ca/en/household-pets/cleaning-supplies-vacuums/vacuums-floor-care/mops-buckets.html)
  2. For every product following values must be scraped:
    * url to main product page: where are two candidates 'pdp-url' and 'short-pdp-url', I have selected 'pdp-url'
    * image url: where are thumbnail image and it is possible to parse the product page to fetch more images, videos and etc. I have selected thumbnail one (may be NULL)
    * pCode: as I understand it is 'prod-id'
    * skuid: some sku's has more than one value. It would be possible to split into two different products. To make it easier I took first value in case it has more than one.
    * part_number: where is two places where part numbers are mentioned. In product list under 'sku-part-number' and in price information service. I took it from price information service.
    * size: 'Quantity' from price information service
    * product name
    * price
    * sale price: 'Promo.Price' or NULL
    * rating: from statistics (bazaarvoice.com)
    * product number: 'sku-number', expecting format 'XXX-XXXX-X'. Padding first number with '0' up to 3 chars.
  3. Parse and get the url for the product listing service
  4. Original page requests price information in 2 tries. 20 prices per request. It seems to support more than this, but spider is done to limit request to 20 as original.
  5. Added a lot of error handlers (more than it is needed in production):
    * checking that fields exist and reporting error (in case page/schema changes and code change is needed)
    * checking that all products are updated with other services, no product is missing
    * if an error occurred (spider failed for unknown reason)
    * error can be sent by mail if config is specified
  6. Exporter to MySQL dump like file.

## Spider logic

Spider has following logic:

  1. The site allows robots
  2. Spider loads [Quick Search](http://www.canadiantire.ca/en/household-pets/cleaning-supplies-vacuums/vacuums-floor-care/mops-buckets.html), finds 'search-result-grid', loads configuration and makes a request to product listing service
  3. Product list service contains JSON (looks like elasticsearch) with information about products and pagination. Spider parses products and requests statistic (bazaarvoice.com) service per every product.
  4. If where is 'next' page specified in paginator, spider fetches it
  5. Since statistics and price info services expect a list of products (bulk) it is better to cache products in spider member variable than add meta information per request.
  6. Parse statistics, update product. Collect a list of products updated and fetch price information.
  7. Parse price info, update product and return the item

## Other information

  1. Some products do not have an image. 
  2. To enable email sending edit the configuration and specify: CANADIAN_TIRE_ERROR_MAIL_TO
  3. Feed exporter must be specified to allow SQL output as bellow:
    FEED_EXPORTERS = {
      'mysql': 'CrowdApexInterview.pipelines.MySQLExporterForCanadianTire',
    }
