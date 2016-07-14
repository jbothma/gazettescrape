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
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfpage import PDFTextExtractionNotAllowed
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.pdfdevice import PDFDevice

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
        archived_g = ArchivedGazette(
            original_uri=webgazette.original_uri,
            publication_date=webgazette.published_date,
        )
        print(webgazette.referrer)
        print(archived_g)

    engine.dispose()


if __name__ == "__main__":
    main()
