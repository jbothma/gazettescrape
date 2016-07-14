"""
A tool to take gazettes from various sources, store them in a nice
structured path, and maintain a database of the gazettes in their
structured paths.
"""

from gazettes.models import WebScrapedGazette, ArchivedGazette
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from urlparse import urlparse
import os
from shutil import copyfile
import pyPdf


WEB_SCRAPE_STORE_URI = "file:///home/jdb/proj/code4sa/corpdata/scrapyfilestore"
LOCAL_CACHE_STORE_PATH = "../archivecachefilestore"
ARCHIVE_STORE = "file:///home/jdb/proj/code4sa/corpdata/archivefilestore"
GAZETTE_DB_URI = 'postgres://gazettes@localhost/web_scraped_gazette'
DB_URI = 'postgres://gazettes@localhost/gazettes'


def main():
    engine = create_engine(DB_URI)
    Session = sessionmaker(bind=engine)
    session = Session()
    web_scrape_store_uri = urlparse(WEB_SCRAPE_STORE_URI)
    cache_path = LOCAL_CACHE_STORE_PATH

    for webgazette in session.query(WebScrapedGazette):
        # Get the PDF
        cached_gazette_path = os.path.join(cache_path, webgazette.store_path)
        if not os.path.exists(cached_gazette_path):
            cached_gazette_dir = os.path.dirname(cached_gazette_path)
            if not os.path.exists(cached_gazette_dir):
                os.makedirs(cached_gazette_dir)
            if web_scrape_store_uri.scheme == 'file':
                scraped_path = os.path.join(web_scrape_store_uri.path,
                                            webgazette.store_path)
                copyfile(scraped_path, cached_gazette_path)

        # Archive the gazette
        print("\n%s\n%s" % (webgazette.original_uri, cached_gazette_path))
        try:
            with file(cached_gazette_path, 'rb') as f:
                pdf = pyPdf.PdfFileReader(f)
                if pdf.isEncrypted:
                    print("ENCRYPTED")
                    pdf.decrypt('')
                ArchivedGazette
                pagecount = pdf.getNumPages()
                cover_page_text = pdf.getPage(0).extractText()
                publication_title = get_publication_title(webgazette.referrer)
                publication_subtitle = get_publication_subtitle(webgazette.referrer,
                                                                webgazette.label)
                special_issue = get_special_issue(webgazette.referrer)
                issue_number = get_issue_number(webgazette.referrer, webgazette.label)
                volume_number = get_volume_number(webgazette.referrer, cover_page_text)
                jurisdiction_code = get_jurisdiction_code(webgazette.referrer)
                unique_id = get_unique_id(publication_title,
                                          publication_subtitle,
                                          jurisdiction_code,
                                          volume_number,
                                          issue_number,
                                          special_issue)
                archive_path = get_archive_path(publication_title,
                                                publication_subtitle,
                                                jurisdiction_code,
                                                volume_number,
                                                issue_number,
                                                special_issue,
                                                webgazette.published_date)
                archived_gazette = ArchivedGazette(
                    original_uri=webgazette.original_uri,
                    archive_path=archive_path,
                    publication_title=publication_title,
                    publication_subtitle=publication_subtitle,
                    special_issue=special_issue,
                    issue_number=issue_number,
                    volume_number=volume_number,
                    jurisdiction_code=jurisdiction_code,
                    publication_date=webgazette.published_date,
                    unique_id=unique_id,
                    pagecount=pagecount,
                )
                session.add(archived_gazette)

        except UnicodeEncodeError:
            print('UnicodeEncodeError')

    session.commit()
    engine.dispose()


def get_publication_title(referrer):
    url = urlparse(referrer)
    if url.hostname == 'www.gpwonline.co.za':
        if url.path in {
                '/Pages/Provincial-Gazettes-Eastern-Cape.aspx',
                '/Pages/Provincial-Gazettes-Gauteng.aspx',
                '/Pages/Provincial-Gazettes-KwaZulu-Natal.aspx',
                '/Pages/Provincial-Gazettes-Limpopo.aspx',
                '/Pages/Provincial-Gazettes-Mpumalanga.aspx',
                '/Pages/Provincial-Gazettes-North-West.aspx',
                '/Pages/Provincial-Gazettes-Northern-Cape.aspx',
        }:
            return 'Provincial Gazette'
        elif url.path in {
                '/Pages/Published-Legal-Gazettes.aspx',
                '/Pages/Published-Liquor-Licenses.aspx',
                '/Pages/Published-National-Government-Gazettes.aspx',
                '/Pages/Published-National-Regulation-Gazettes.aspx',
                '/Pages/Published-Separate-Gazettes.aspx',
                '/Pages/Road-Access-Permits.aspx',
        }:
            return 'Government Gazette'
        elif url.path == '/Pages/Published-Tender-Bulletin.aspx':
            return 'Tender Bulletin'
        else:
            raise Exception
    elif url.hostname in {
            'www.westerncape.gov.za'
    }:
        return 'Provincial Gazette'
    else:
        raise Exception


def get_publication_subtitle(referrer, label):
    url = urlparse(referrer)
    if url.hostname == 'www.gpwonline.co.za':
        if url.path == '/Pages/Published-National-Regulation-Gazettes.aspx':
            return 'Regulation Gazette'
        elif url.path == '/Pages/Published-Legal-Gazettes.aspx':
            return 'Legal Gazette XX'
        elif url.path in {
                '/Pages/Provincial-Gazettes-Eastern-Cape.aspx',
                '/Pages/Provincial-Gazettes-Gauteng.aspx',
                '/Pages/Provincial-Gazettes-KwaZulu-Natal.aspx',
                '/Pages/Provincial-Gazettes-Limpopo.aspx',
                '/Pages/Provincial-Gazettes-Mpumalanga.aspx',
                '/Pages/Provincial-Gazettes-North-West.aspx',
                '/Pages/Provincial-Gazettes-Northern-Cape.aspx',
                '/Pages/Published-Legal-Gazettes.aspx',
                '/Pages/Published-Liquor-Licenses.aspx',
                '/Pages/Published-National-Government-Gazettes.aspx',
                '/Pages/Published-Separate-Gazettes.aspx',
                '/Pages/Road-Access-Permits.aspx',
                '/Pages/Published-Tender-Bulletin.aspx',
        }:
            return None
        else:
            raise Exception
    elif url.hostname in {
            'www.westerncape.gov.za'
    }:
        return None
    else:
        raise Exception


def get_special_issue(referrer):
    url = urlparse(referrer)
    if url.hostname == 'www.gpwonline.co.za':
        if url.path == '/Pages/Published-Liquor-Licenses.aspx':
            return 'Liquor Licenses'
        elif url.path == '/Pages/Road-Access-Permits.aspx':
            return 'Legal Gazette XX'
        elif url.path in {
                '/Pages/Provincial-Gazettes-Eastern-Cape.aspx',
                '/Pages/Provincial-Gazettes-Gauteng.aspx',
                '/Pages/Provincial-Gazettes-KwaZulu-Natal.aspx',
                '/Pages/Provincial-Gazettes-Limpopo.aspx',
                '/Pages/Provincial-Gazettes-Mpumalanga.aspx',
                '/Pages/Provincial-Gazettes-North-West.aspx',
                '/Pages/Provincial-Gazettes-Northern-Cape.aspx',
                '/Pages/Published-Legal-Gazettes.aspx',
                '/Pages/Published-National-Government-Gazettes.aspx',
                '/Pages/Published-Separate-Gazettes.aspx',
                '/Pages/Published-Legal-Gazettes.aspx',
                '/Pages/Published-Tender-Bulletin.aspx',
                '/Pages/Published-National-Regulation-Gazettes.aspx',
        }:
            return None
        else:
            raise Exception
    elif url.hostname in {
            'www.westerncape.gov.za'
    }:
        return None
    else:
        raise Exception


def get_issue_number(referrer, label):


if __name__ == "__main__":
    main()
