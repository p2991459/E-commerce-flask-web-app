# import required modules
import csv
import scrapy
from scrapy.spiders import CrawlSpider, Request, Rule
from scrapy.linkextractors import LinkExtractor
from urllib.parse import urlparse
from usp.tree import sitemap_tree_for_homepage
from scrapy.exceptions import CloseSpider
import time
from scrapy import signals
from email_extraction.spiders import post_scrap


class UrlExtractor(scrapy.Spider):
    # adjusting parameters
    name = 'url_ex'

    start_urls = []
    
    def __init__(self, *args, **kwargs):
        super(UrlExtractor, self).__init__(*args, **kwargs)
        self.url_list = []
        self.current_site = ''
        self.link_ext = LinkExtractor()

        try:
            self.output
        except AttributeError:
            self.output = self.name+time.strftime("_%d_%m_%H_%M")+'.csv'
            print(f'No output name given, using {self.output}')

        try:
            self.start_urls = [
                self.website
            ]
        except AttributeError:
            raise CloseSpider('No "website" param found please use command: -a website="URL..."')

    def start_requests(self):
        for url in self.start_urls:
            prsr = urlparse(url)
            base_url = prsr.scheme + '://' + prsr.hostname

            # Code to check if sitemap exist
            tree = sitemap_tree_for_homepage(base_url)
            sm_urls = [page.url for page in tree.all_pages()]
            if len(sm_urls) > 0:
                print('sitemap found for:', base_url)
                writer = csv.writer(
                    open(self.output, 'a'),
                    lineterminator='\n'
                    )
                # Can be added functionality for each website urls in a new sheet...
                writer.writerows([[url] for url in sm_urls])
                continue


            self.link_ext = LinkExtractor(
              allow=base_url,
              unique=True
              )
            yield Request(url,self.parse, meta={'base_url': base_url})

    def parse(self, response, *args, **kwargs):
        base_url = response.meta['base_url']
        links = self.link_ext.extract_links(response)
        links = {link.url for link in links if not link.fragment}
        unique_links = links - set(self.url_list)
        self.url_list.extend(unique_links)
        
        for link in unique_links:
            yield Request(link, self.parse, meta={'base_url': base_url})
        yield {'extracted_urls': unique_links, 'base_url': base_url }

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(UrlExtractor, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        return spider

    def spider_closed(self, spider):
        post_scrap(self.output, self.name)
