import scrapy
from gazettescrape.items import GazetteItem
from datetime import datetime
import urlparse
import re


class GpwSpider(scrapy.Spider):
    name = "western_cape"
    allowed_domains = [
        'westerncape.gov.za',
        'www.capegateway.gov.za'
    ]
    start_urls = {
        "https://www.westerncape.gov.za/documents/public_info/P",
    }

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(url, self.parse_alphabetic_index)

    def parse_alphabetic_index(self, response):
        year_page_xpath = '//h2[contains(@class,"field-content")]' \
                          '/a[contains(text(), "Provincial Gazettes 20")]/@href'
        for url in response.xpath(year_page_xpath).extract():
            yield scrapy.Request(urlparse.urljoin(response.url, url), self.parse_year_page)

    def parse_year_page(self, response):
        month_page_xpath = '//div[contains(@class,"paging-page-links")]/ul/li' \
                           '/a[contains(text(), "Provincial Gazette - ")]/@href'
        for url in response.xpath(month_page_xpath).extract():
            yield scrapy.Request(urlparse.urljoin(response.url, url), self.parse_month_page)

    def parse_month_page(self, response):
        gazette_xpath = '//div[contains(@class,"field-item")]/ul/li' \
                           '/a[contains(text(), "Provincial Gazette ")]'
        for anchor in response.xpath(gazette_xpath):
            gazette_item = GazetteItem()
            label_xpath = 'text()'
            gazette_item['label'] = anchor.xpath(label_xpath)[0].extract()
            file_url_xpath = '@href'
            gazette_url = anchor.xpath(file_url_xpath)[0].extract()
            gazette_item['file_urls'] = [gazette_url]
            dateregex = 'Provincial Gazette[\w\s]*- ?(\w+, )?(\d+ \w+ \d+)'
            try:
                wc_pub_date = re.search(dateregex, gazette_item['label']).groups()[-1]
                date = datetime.strptime(wc_pub_date, '%d %B %Y')
                gazette_item['published_date'] = date.isoformat()
            except AttributeError:
                dateregex = 'Provincial Gazette[\w\s]*- ?(\w+, )?(\d+ \w+)'
                try:
                    wc_pub_date = re.search(dateregex, gazette_item['label']).groups()[-1]
                    date = datetime.strptime(wc_pub_date, '%d %B')
                    title_xpath = 'h1/text()'
                    title = response.xpath(title_xpath).extract()[0]
                    title_dateregex = 'Provincial Gazette - ?(\w+ \d+)'
                    title_date = datetime.strptime(re.search(title_dateregex, title).group(1), '%B %Y')
                    if date.month == title_date.month:
                        date.year = title_date.year
                        gazette_item['published_date'] = date.isoformat()
                    else:
                        raise Exception(gazette_item['label'])
                except AttributeError:
                    raise Exception(gazette_item['label'])
            gazette_item['referrer'] = response.url
            yield gazette_item
