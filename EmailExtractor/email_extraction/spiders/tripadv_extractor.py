# import required modules
import scrapy
from scrapy.spiders import CrawlSpider, Request, Rule
from scrapy.linkextractors import LinkExtractor
from googlesearch import search
import re
from scrapy_selenium import SeleniumRequest
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urlparse
from scrapy.exceptions import CloseSpider
import logging
import time
from scrapy import signals
from email_extraction.spiders import post_scrap

logging.getLogger('scrapy').propagate = False
logging.getLogger('usp.helpers').propagate = False
logging.getLogger().propagate = False
logging.disable(logging.WARNING)


# create class to extract email ids
class TripadvExtractor(CrawlSpider):
    # adjusting parameters
    name = 'tripadv_ex'

    def parse_item(self, response):
        self.log('crawling'.format(response.url))

    def __init__(self, *args, **kwargs):
        super(TripadvExtractor, self).__init__(*args, **kwargs)
        self.result = []
        self.emails = []
        self.url_list = []
        self.unique_mails = set()
        self.link_ext = LinkExtractor()

        try:
            self.output
        except AttributeError:
            self.output = self.name+time.strftime("_%d_%m_%H_%M")+'.csv'
            print(f'No output name given, using {self.output}')

        try:
            print(f'Spider for: {self.tripUrl}')
            print(f'Looking-for-word:{self.lookingFor}')
        except:
            print('Please use required options: tripUrl, lookingFor')
            raise CloseSpider('Invalid Query Param')
        self.urls = [
            self.tripUrl
        ]
        self.counter = 0

    # sending requests
    def start_requests(self):
        requests = list(super(TripadvExtractor, self).start_requests())
        req = []
        for url in self.urls:
            prsr = urlparse(url)
            base_url = prsr.scheme + '://' + prsr.hostname
            req.append(Request(url, self.parse, meta={'base_url': base_url}))
        # requests += [scrapy.Request(x, self.parse, meta={'base_url': x}) for x in self.urls]
        requests += req
        return requests

    # extracting emails
    def parse_email(self, response):
        self.emails.clear()
        EMAIL_REGEX = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
        emails = re.findall(EMAIL_REGEX, str(response.text))

        if len(emails):
            return {'emails': emails, 'page': response.url}

    def parse(self, response, *args, **kwargs):

        if re.search(self.lookingFor, response.text, re.IGNORECASE):
            base_url = response.meta['base_url']
            self.link_ext = LinkExtractor(
                allow=base_url,
                unique=True
            )

            emails = self.parse_email(response)
            if emails:
                self.result.append(emails)
            links = self.link_ext.extract_links(response)
            links = {link.url for link in links if not link.fragment}
            unique_links = links - set(self.url_list)
            self.url_list.extend(unique_links)
            for link in unique_links:
                yield Request(link, self.parse, meta={'base_url': base_url})
            if len(self.result):
                yield {'result': self.result}
            self.result.clear()
        else:
            print('Chicago not found in %s' % response.url)

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(TripadvExtractor, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        return spider

    def spider_closed(self, spider):
        post_scrap(self.output, self.name)
