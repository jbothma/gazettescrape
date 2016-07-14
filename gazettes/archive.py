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
import re
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
import StringIO
from tempfile import mkdtemp


WEB_SCRAPE_STORE_URI = "file:///home/jdb/proj/code4sa/corpdata/scrapyfilestore"
LOCAL_CACHE_STORE_PATH = "../archivecachefilestore"
ARCHIVE_STORE = "file:///home/jdb/proj/code4sa/corpdata/archivefilestore"
GAZETTE_DB_URI = 'postgres://gazettes@localhost/web_scraped_gazette'
DB_URI = 'postgres://gazettes@localhost/gazettes'


def main():
    tmpdir = mkdtemp(prefix='gazettes-archive')
    engine = create_engine(DB_URI)
    Session = sessionmaker(bind=engine)
    session = Session()
    web_scrape_store_uri = urlparse(WEB_SCRAPE_STORE_URI)
    cache_path = LOCAL_CACHE_STORE_PATH

    for webgazette in session.query(WebScrapedGazette):
        print
        # Get the PDF
        cached_gazette_path = os.path.join(cache_path, webgazette.store_path)
        if not os.path.exists(cached_gazette_path):
            print("Cache MISS %s" % webgazette.store_path)
            cached_gazette_dir = os.path.dirname(cached_gazette_path)
            if not os.path.exists(cached_gazette_dir):
                os.makedirs(cached_gazette_dir)
            if web_scrape_store_uri.scheme == 'file':
                scraped_path = os.path.join(web_scrape_store_uri.path,
                                            webgazette.store_path)
                copyfile(scraped_path, cached_gazette_path)
        else:
            print("Cache HIT %s" % webgazette.store_path)

        # Archive the gazette
        print("%s\n%s" % (webgazette.original_uri, cached_gazette_path))
        try:
            with open(cached_gazette_path, 'rb') as fp:
                rsrcmgr = PDFResourceManager()
                outfp = StringIO.StringIO()
                parser = PDFParser(fp)
                password = ""
                document = PDFDocument(parser, password)
                if not document.is_extractable:
                    print("### not extractable")
                    tmppath = os.path.join(tmpdir, webgazette.store_path)
                    if not os.path.exists(os.path.dirname(tmppath)):
                        os.makedirs(os.path.dirname(tmppath))
                    result = os.system("qpdf --password=%s --decrypt %s %s"
                                       % (password, cached_gazette_path, tmppath))
                    if result == 0:
                        copyfile(tmppath, cached_gazette_path)
                    else:
                        raise Exception("qpd exit status %r" % result)

                device = TextConverter(rsrcmgr, outfp, codec='utf-8', laparams=LAParams())
                interpreter = PDFPageInterpreter(rsrcmgr, device)
                maxpages = 0
                caching = True
                pagenos = set()
                cover_page = PDFPage.get_pages(fp, pagenos, maxpages=maxpages, password=password,caching=caching, check_extractable=True).next()
                interpreter.process_page(cover_page)
                device.close()
                t = outfp.getvalue()

                pagecount = 1
                print(pagecount)
                cover_page_text = t
                publication_title = get_publication_title(webgazette.referrer,
                                                          webgazette.label)
                print(publication_title)
                publication_subtitle = get_publication_subtitle(webgazette.referrer,
                                                                webgazette.label)
                if publication_subtitle:
                    print(publication_subtitle)
                special_issue = get_special_issue(webgazette.referrer)
                if special_issue:
                    print(special_issue)
                issue_number = get_issue_number(webgazette.referrer, webgazette.label)
                print("issue %r" % issue_number)
                volume_number = get_volume_number(webgazette.referrer, cover_page_text)
                print("volume %r" % volume_number)
                jurisdiction_code = get_jurisdiction_code(webgazette.referrer,
                                                          webgazette.label)
                unique_id = get_unique_id(publication_title,
                                          publication_subtitle,
                                          jurisdiction_code,
                                          volume_number,
                                          issue_number,
                                          special_issue)
                print(unique_id)
                archive_path = get_archive_path(publication_title,
                                                publication_subtitle,
                                                jurisdiction_code,
                                                volume_number,
                                                issue_number,
                                                special_issue,
                                                webgazette.published_date)
                archived_gazette = ArchivedGazette.fromDict({
                    'original_uri': webgazette.original_uri,
                    'archive_path': archive_path,
                    'publication_title': publication_title,
                    'publication_subtitle': publication_subtitle,
                    'special_issue': special_issue,
                    'issue_number': issue_number,
                    'volume_number': volume_number,
                    'jurisdiction_code': jurisdiction_code,
                    'publication_date': webgazette.published_date,
                    'unique_id': unique_id,
                    'pagecount': pagecount,
                })
                # session.add(archived_gazette)

        except UnicodeEncodeError:
            print('UnicodeEncodeError')

    session.commit()
    engine.dispose()


def get_publication_title(referrer, label):
    url = urlparse(referrer)
    if url.hostname == 'www.gpwonline.co.za':
        if url.path in {
                '/Gazettes/Pages/Provincial-Gazettes-Eastern-Cape.aspx',
                '/Gazettes/Pages/Provincial-Gazettes-Gauteng.aspx',
                '/Gazettes/Pages/Provincial-Gazettes-KwaZulu-Natal.aspx',
                '/Gazettes/Pages/Provincial-Gazettes-Limpopo.aspx',
                '/Gazettes/Pages/Provincial-Gazettes-Mpumalanga.aspx',
                '/Gazettes/Pages/Provincial-Gazettes-North-West.aspx',
                '/Gazettes/Pages/Provincial-Gazettes-Northern-Cape.aspx',
        }:
            return 'Provincial Gazette'
        elif url.path in {
                '/Gazettes/Pages/Published-Legal-Gazettes.aspx',
                '/Gazettes/Pages/Published-National-Government-Gazettes.aspx',
                '/Gazettes/Pages/Published-National-Regulation-Gazettes.aspx',
                '/Gazettes/Pages/Published-Separate-Gazettes.aspx',
                '/Gazettes/Pages/Road-Access-Permits.aspx',
        }:
            return 'Government Gazette'
        elif url.path == '/Gazettes/Pages/Published-Liquor-Licenses.aspx':
            if ('NCape' in label or
                'NKaap' in label or
                'Northern Cape' in label or
                'gaut' in label.lower()):
                return 'Provincial Gazette'
            elif 'National' in label:
                return 'Government Gazette'
            else:
                raise Exception("unknon jurisdiction for '%s'" % label)
        elif url.path == '/Gazettes/Pages/Published-Tender-Bulletin.aspx':
            return 'Tender Bulletin'
        else:
            raise Exception("unknown path '%s'" % url.path)
    elif url.hostname in {
            'www.westerncape.gov.za'
    }:
        return 'Provincial Gazette'
    else:
        raise Exception


def get_publication_subtitle(referrer, label):
    url = urlparse(referrer)
    if url.hostname == 'www.gpwonline.co.za':
        if url.path == '/Gazettes/Pages/Published-National-Regulation-Gazettes.aspx':
            return 'Regulation Gazette'
        elif url.path == '/Gazettes/Pages/Published-Legal-Gazettes.aspx':
            return 'Legal Gazette XX'
        elif url.path in {
                '/Gazettes/Pages/Provincial-Gazettes-Eastern-Cape.aspx',
                '/Gazettes/Pages/Provincial-Gazettes-Gauteng.aspx',
                '/Gazettes/Pages/Provincial-Gazettes-KwaZulu-Natal.aspx',
                '/Gazettes/Pages/Provincial-Gazettes-Limpopo.aspx',
                '/Gazettes/Pages/Provincial-Gazettes-Mpumalanga.aspx',
                '/Gazettes/Pages/Provincial-Gazettes-North-West.aspx',
                '/Gazettes/Pages/Provincial-Gazettes-Northern-Cape.aspx',
                '/Gazettes/Pages/Published-Legal-Gazettes.aspx',
                '/Gazettes/Pages/Published-Liquor-Licenses.aspx',
                '/Gazettes/Pages/Published-National-Government-Gazettes.aspx',
                '/Gazettes/Pages/Published-Separate-Gazettes.aspx',
                '/Gazettes/Pages/Road-Access-Permits.aspx',
                '/Gazettes/Pages/Published-Tender-Bulletin.aspx',
        }:
            return None
        else:
            raise Exception("unknown path '%s'" % url.path)
    elif url.hostname in {
            'www.westerncape.gov.za'
    }:
        return None
    else:
        raise Exception


def get_special_issue(referrer):
    url = urlparse(referrer)
    if url.hostname == 'www.gpwonline.co.za':
        if url.path == '/Gazettes/Pages/Published-Liquor-Licenses.aspx':
            return 'Liquor Licenses'
        elif url.path == '/Gazettes/Pages/Road-Access-Permits.aspx':
            return 'Legal Gazette XX'
        elif url.path in {
                '/Gazettes/Pages/Provincial-Gazettes-Eastern-Cape.aspx',
                '/Gazettes/Pages/Provincial-Gazettes-Gauteng.aspx',
                '/Gazettes/Pages/Provincial-Gazettes-KwaZulu-Natal.aspx',
                '/Gazettes/Pages/Provincial-Gazettes-Limpopo.aspx',
                '/Gazettes/Pages/Provincial-Gazettes-Mpumalanga.aspx',
                '/Gazettes/Pages/Provincial-Gazettes-North-West.aspx',
                '/Gazettes/Pages/Provincial-Gazettes-Northern-Cape.aspx',
                '/Gazettes/Pages/Published-Legal-Gazettes.aspx',
                '/Gazettes/Pages/Published-National-Government-Gazettes.aspx',
                '/Gazettes/Pages/Published-Separate-Gazettes.aspx',
                '/Gazettes/Pages/Published-Legal-Gazettes.aspx',
                '/Gazettes/Pages/Published-Tender-Bulletin.aspx',
                '/Gazettes/Pages/Published-National-Regulation-Gazettes.aspx',
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
    url = urlparse(referrer)
    if url.hostname == 'www.gpwonline.co.za':
        regex = '^(\d+)[_ ]\d'
    elif url.hostname == 'www.westerncape.gov.za':
        regex = '^[a-zA-Z ]+(\d+)\D?-'
    else:
        raise Exception
    try:
        return int(re.search(regex, label).group(1))
    except AttributeError:
        raise Exception("Can't find issue number in '%s'" % label)


def get_volume_number(referrer, cover_page_text):
    url = urlparse(referrer)
    if url.hostname == 'www.gpwonline.co.za':
        regex = 'Vol. ?(\d+)'
        try:
            return int(re.search(regex, cover_page_text).group(1))
        except AttributeError:
            raise Exception("Can't find volume number in %r" % cover_page_text)
    elif url.hostname == 'www.westerncape.gov.za':
        return None
    else:
        raise Exception


def get_jurisdiction_code(referrer, label):
    url = urlparse(referrer)
    if url.hostname == 'www.gpwonline.co.za':
        if url.path == '/Gazettes/Pages/Provincial-Gazettes-Eastern-Cape.aspx':
            return 'ZA-WC'
        elif url.path == '/Gazettes/Pages/Provincial-Gazettes-Gauteng.aspx':
            return 'ZA-GT'
        elif url.path == '/Gazettes/Pages/Provincial-Gazettes-KwaZulu-Natal.aspx':
            return 'ZA-NL'
        elif url.path == '/Gazettes/Pages/Provincial-Gazettes-Limpopo.aspx':
            return 'ZA-LP'
        elif url.path == '/Gazettes/Pages/Provincial-Gazettes-Mpumalanga.aspx':
            return 'ZA-MP'
        elif url.path == '/Gazettes/Pages/Provincial-Gazettes-North-West.aspx':
            return 'ZA-NW'
        elif url.path == '/Gazettes/Pages/Provincial-Gazettes-Northern-Cape.aspx':
            return 'ZA-NC'
        elif url.path in {
                '/Gazettes/Pages/Published-Legal-Gazettes.aspx',
                '/Gazettes/Pages/Published-National-Government-Gazettes.aspx',
                '/Gazettes/Pages/Published-National-Regulation-Gazettes.aspx',
                '/Gazettes/Pages/Published-Separate-Gazettes.aspx',
                '/Gazettes/Pages/Road-Access-Permits.aspx',
                '/Gazettes/Pages/Published-Tender-Bulletin.aspx',
        }:
            return 'ZA'
        elif url.path == '/Gazettes/Pages/Published-Liquor-Licenses.aspx':
            if ('NCape' in label or
                'NKaap' in label or
                'Northern Cape' in label):
                return 'ZA-NC'
            elif 'gaut' in label.lower():
                return 'ZA-GT'
            elif 'National' in label:
                return 'ZA'
            else:
                raise Exception("unknon jurisdiction for '%s'" % label)
        else:
            raise Exception("unknown path '%s'" % url.path)
    elif url.hostname in {
            'www.westerncape.gov.za'
    }:
        return 'ZA-WC'
    else:
        raise Exception


def get_unique_id(publication_title,
                  publication_subtitle,
                  jurisdiction_code,
                  volume_number,
                  issue_number,
                  special_issue):
    if volume_number is None:
        return "%s-%s-no-%s" % (
            title_slug(publication_title),
            jurisdiction_code,
            issue_number
        )
    else:
        return "%s-%s-vol-%s-no-%s" % (
        title_slug(publication_title),
            jurisdiction_code,
            volume_number,
            issue_number
        )


def title_slug(title):
    return {
        'Government Gazette': 'government-gazette',
        'Provincial Gazette': 'provincial-gazette',
        'Tender Bulletin': 'tender-bulletin',
    }[title]


def get_archive_path(publication_title,
                     publication_subtitle,
                     jurisdiction_code,
                     volume_number,
                     issue_number,
                     special_issue,
                     publication_date):
    return '/'


if __name__ == "__main__":
    main()
