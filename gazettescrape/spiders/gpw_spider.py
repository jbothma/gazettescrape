import scrapy
from gazettescrape.items import GazetteItem
from datetime import datetime

class GpwSpider(scrapy.Spider):
    name = "gpw"
    allowed_domains = ["gpwonline.co.za"]
    start_urls = [
        "http://www.gpwonline.co.za/Gazettes/Pages/Published-Liquor-Licenses.aspx?p=1"
    ]

    def parse(self, response):
        gazette_row_css = '.GazetteTitle'
        for row in response.css(gazette_row_css):
            gazette_item = GazetteItem()
            label_xpath = 'div/a/text()'
            gazette_item['label'] = row.xpath(label_xpath)[0].extract()
            file_urls_xpath = 'div/a/@href'
            gazette_item['file_urls'] = row.xpath(file_urls_xpath).extract()
            date_xpath = 'div/text()'
            gpw_pub_date = row.xpath(date_xpath)[0].extract()
            date = datetime.strptime(gpw_pub_date, '%d/%m/%Y')
            gazette_item['published_date'] = date.isoformat()
            yield gazette_item
