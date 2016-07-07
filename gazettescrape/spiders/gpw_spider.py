import scrapy
from gazettescrape.items import GazetteItem
from datetime import datetime
import urlparse


class GpwSpider(scrapy.Spider):
    name = "gpw"
    allowed_domains = ["gpwonline.co.za"]
    start_urls = {
        'http://www.gpwonline.co.za/Gazettes/Pages/Provincial-Gazettes-Eastern-Cape.aspx',
        'http://www.gpwonline.co.za/Gazettes/Pages/Provincial-Gazettes-Gauteng.aspx',
        'http://www.gpwonline.co.za/Gazettes/Pages/Provincial-Gazettes-KwaZulu-Natal.aspx',
        'http://www.gpwonline.co.za/Gazettes/Pages/Provincial-Gazettes-Limpopo.aspx',
        'http://www.gpwonline.co.za/Gazettes/Pages/Provincial-Gazettes-Mpumalanga.aspx',
        'http://www.gpwonline.co.za/Gazettes/Pages/Provincial-Gazettes-North-West.aspx',
        'http://www.gpwonline.co.za/Gazettes/Pages/Provincial-Gazettes-Northern-Cape.aspx',
        'http://www.gpwonline.co.za/Gazettes/Pages/Published-Legal-Gazettes.aspx',
        'http://www.gpwonline.co.za/Gazettes/Pages/Published-Liquor-Licenses.aspx',
        'http://www.gpwonline.co.za/Gazettes/Pages/Published-National-Government-Gazettes.aspx',
        'http://www.gpwonline.co.za/Gazettes/Pages/Published-National-Regulation-Gazettes.aspx',
        'http://www.gpwonline.co.za/Gazettes/Pages/Published-Separate-Gazettes.aspx',
        'http://www.gpwonline.co.za/Gazettes/Pages/Published-Separate-Gazettes.aspx',
        'http://www.gpwonline.co.za/Gazettes/Pages/Published-Tender-Bulletin.aspx',
        'http://www.gpwonline.co.za/Gazettes/Pages/Road-Access-Permits.aspx',
    }

    def __init__(self, start_url=None):
        if start_url is not None:
            self.start_urls = [start_url]

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
            gazette_item['referrer'] = response.url
            yield gazette_item

        next_page_xpath = '//div[@class="Paging"]/div/strong/following-sibling::a/@href'
        next_pages = response.xpath(next_page_xpath)
        if next_pages:
            yield scrapy.Request(urlparse.urljoin(response.url, next_pages[0].extract()))
