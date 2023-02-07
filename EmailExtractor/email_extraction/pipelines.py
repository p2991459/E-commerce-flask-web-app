# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
import csv


def write_to_csv(item, filename, crawler):
    writer = csv.writer(open(filename, 'a'), lineterminator='\n')

    for result in item.get('result', []):
        for mail_id in result.get('emails', []):
            writer.writerow([mail_id, crawler])


def write_link_to_csv(urls, filename):
    writer = csv.writer(open(filename, 'a'), lineterminator='\n')
    # Can be added functionality for each website urls in a new sheet...
    writer.writerows([[url] for url in urls])


class EmailExtractionPipeline:
    def __init__(self):
        self.count = 0

    def process_item(self, item, spider):
        if 'extracted_urls' in item:
            write_link_to_csv(item['extracted_urls'], spider.output)
        else:
            write_to_csv(item, spider.output, spider.name)
        return item
