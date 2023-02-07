from scrapy.spiders import CrawlSpider, Request, Rule
from googlesearch import search
import re
from scrapy_selenium import SeleniumRequest
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from scrapy.exceptions import CloseSpider
import time
from scrapy import signals
from email_extraction.spiders import post_scrap


# create class to extract email ids
class GoogleExtractor(CrawlSpider):
    # adjusting parameters
    name = 'google_ex'

    # rules = (
    #     # Extract and follow all links!
    #     Rule(LinkExtractor(), callback='parse_item', follow=True),
    # )

    def parse_item(self, response):
        self.log('crawling'.format(response.url))

    def __init__(self, *args, **kwargs):
        super(GoogleExtractor, self).__init__(*args, **kwargs)
        self.email_list = []

        try:
            self.output
        except AttributeError:
            self.output = self.name+time.strftime("_%d_%m_%H_%M")+'.csv'
            print(f'No output name given, using {self.output}')

        try:
            self.query
        except:
            print('Please use required option(s): query')
            raise CloseSpider('Invalid Query Param')
         
        # command: scrapy crawl google_ex -a query='query...'

        # Ex-Query: 'site:tripadvisor.com chicago and "gmail.com" OR "hotmail" OR "ymail.com" OR "yahoo.com" OR ' \
        #             '"mail.com" '

    # sending requests
    def start_requests(self):
        print('Google Extractor started...')
        for results in search(self.query, ):
            yield SeleniumRequest(
                url=results,
                callback=self.parse,
                wait_until=ec.presence_of_element_located(
                    (By.TAG_NAME, "html")),
                dont_filter=True
            )

    # extracting emails
    def parse(self, response, *args, **kwargs):
        EMAIL_REGEX = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-.]+\.[a-zA-Z0-9-]+'
        emails = re.finditer(EMAIL_REGEX, str(response.text))
        for email in emails:
            self.email_list.append(email.group())

        for email in set(self.email_list):
            yield {
                "result": [{
                    "emails": (email,),
                    "page": response.url
                }]
            }

        self.email_list.clear()

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(GoogleExtractor, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        return spider

    def spider_closed(self, spider):
        post_scrap(self.output, self.name)
