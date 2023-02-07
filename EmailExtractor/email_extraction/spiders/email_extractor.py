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
 
import logging
logging.getLogger('scrapy').propagate = False
logging.getLogger('usp.helpers').propagate = False
logging.getLogger().propagate = False
logging.disable(logging.WARNING)

# create class to extract email ids
class EmailExtractor(CrawlSpider):
     
    # adjusting parameters
    name = 'email_ex'

    def parse_item(self, response):
        self.log('crawling'.format(response.url))
 
    def __init__(self, *args, **kwargs):
        super(EmailExtractor, self).__init__(*args, **kwargs)
        self.result = []
        self.emails = []
        self.url_list = []
        self.unique_mails = set()
        self.link_ext = LinkExtractor()
        self.query = "florist chicago"  # for google srch
        self.urls = [
            # 'https://www.fasanflorist.com/',
            # 'https://www.ashaddflorist.com/contact/',
            # 'https://www.arenaflowers.co.in/',
            # 'https://www.southsideblooms.com/',
            'https://www.tripadvisor.com/Hotels-g35805-a_ufe.true-Chicago_Illinois-Hotels.html',
        ]
        self.counter = 0
 
    # sending requests
    def start_requests(self):
        
        requests = list(super(EmailExtractor, self).start_requests())
        req = []
        for url in self.urls:
            prsr = urlparse(url)
            base_url = prsr.scheme + '://' + prsr.hostname
            req.append(scrapy.Request(url, self.parse, meta={'base_url': base_url}))
        requests += req
        return requests
 
    # extracting emails
    def parse_email(self, response):
        self.emails.clear()
        EMAIL_REGEX = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
        emails = re.findall(EMAIL_REGEX, str(response.text))

        # new_mails = self.unique_mails - set(emails)
        # self.unique_mails.update(new_mails)

        # for email in emails:
        #     # if email not in self.unique_mails:
        #     self.emails.append(email.group())
        if len(emails):
            return {'emails': emails, 'page': response.url}
 
        

    def parse(self, response, *args, **kwargs):
        base_url = response.meta['base_url']

        self.link_ext = LinkExtractor(
            allow=base_url,
            unique=True
            )

        # print(response.url)
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
        



