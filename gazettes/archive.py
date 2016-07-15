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
from shutil import move
import re
from tempfile import mkdtemp
import subprocess

WEB_SCRAPE_STORE_URI = "file:///home/jdb/proj/code4sa/corpdata/scrapyfilestore"
LOCAL_CACHE_STORE_PATH = "../archivecachefilestore"
ARCHIVE_STORE = "file:///home/jdb/proj/code4sa/corpdata/archivefilestore"
GAZETTE_DB_URI = 'postgres://gazettes@localhost/web_scraped_gazette'
DB_URI = 'postgres://gazettes@localhost/gazettes'


class NeedsOCRError(Exception):
    pass


def main():
    tmpdir = mkdtemp(prefix='gazettes-archive')
    engine = create_engine(DB_URI)
    Session = sessionmaker(bind=engine)
    webscraped_sesh = Session()
    web_scrape_store_uri = urlparse(WEB_SCRAPE_STORE_URI)
    cache_path = LOCAL_CACHE_STORE_PATH

    for webgazette in webscraped_sesh.query(WebScrapedGazette)\
                                     .filter(WebScrapedGazette.manually_ignored == False)\
                                     .all():
        archive_sesh = Session()
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
                move(scraped_path, cached_gazette_path)
        else:
            print("Cache HIT %s" % webgazette.store_path)

        # Archive the PDF
        try:
            print("%s\n%s" % (webgazette.original_uri, cached_gazette_path))

            cover_page_text = get_cover_page_text(cached_gazette_path)
            if is_gazette_index(cover_page_text):
                continue

            pagecount = get_page_count(cached_gazette_path)
            print(pagecount)

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
            language_edition = get_language_edition(webgazette.referrer,
                                                    webgazette.label)
            if language_edition:
                print(language_edition)
            issue_number = get_issue_number(webgazette.referrer, webgazette.label)
            print("issue %r" % issue_number)
            volume_number = get_volume_number(webgazette.referrer, cover_page_text)
            print("volume %r" % volume_number)
            jurisdiction_code = get_jurisdiction_code(webgazette.referrer,
                                                      webgazette.label)
            part_number = get_part_number(webgazette.referrer,
                                          webgazette.label)
            if part_number is not None:
                print("part %r" % part_number)
            unique_id = get_unique_id(publication_title,
                                      publication_subtitle,
                                      jurisdiction_code,
                                      volume_number,
                                      issue_number,
                                      part_number,
                                      language_edition)
            print(unique_id)
            archive_path = get_archive_path(unique_id,
                                            jurisdiction_code,
                                            special_issue,
                                            webgazette.published_date)
            print(archive_path)
            archived_gazette = ArchivedGazette.fromDict({
                'original_uri': webgazette.original_uri,
                'archive_path': archive_path,
                'publication_title': publication_title,
                'publication_subtitle': publication_subtitle,
                'special_issue': special_issue,
                'language_edition': language_edition,
                'issue_number': issue_number,
                'volume_number': volume_number,
                'jurisdiction_code': jurisdiction_code,
                'publication_date': webgazette.published_date,
                'unique_id': unique_id,
                'pagecount': pagecount,
            })
            print(archived_gazette)
            archive_sesh.add(archived_gazette)
        except NeedsOCRError, e:
            print(e)

        archive_sesh.commit()
    engine.dispose()


def get_cover_page_text(cached_gazette_path):
    result = os.system("pdftotext -f 1 -l 1 %s" % cached_gazette_path)
    if result == 0:
        pre, ext = os.path.splitext(cached_gazette_path)
        with open(pre + '.txt', 'r') as f:
            return f.read()
    else:
        raise Exception("pdf_to_text exit status %r" % result)


def get_page_count(cached_gazette_path):
    info = subprocess.check_output(['pdfinfo', cached_gazette_path])
    regex = 'Pages:\s+(\d+)\s'
    try:
        return int(re.search(regex, info).group(1))
    except AttributeError:
        raise Exception("Can't find page count in %r" % info)


def is_gazette_index(cover_page_text):
    return 'INDEX OF THE' in cover_page_text


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
            regex = 'Legal? ?([A-C])'
            return "Legal Gazette %s" % re.search(regex, label).group(1)
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
            return 'Road Carrier Permits'
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


def get_part_number(referrer, label):
    url = urlparse(referrer)
    if url.hostname == 'www.gpwonline.co.za':
        regex = '(Part|P) ?(\d+)$'
    elif url.hostname == 'www.westerncape.gov.za':
        return None
    else:
        raise Exception
    match = re.search(regex, label)
    if match:
        return int(match.group(2))
    else:
        return None


def get_language_edition(referrer, label):
    """
    'Provincial Gazette Extraordinary 6445a - 18 June 2007'
    'Provincial Gazette Extraordinary 6445e - 18 June 2007'
    """
    url = urlparse(referrer)
    if url.hostname == 'www.gpwonline.co.za':
        return None
    elif url.hostname == 'www.westerncape.gov.za':
        regex = '^[a-zA-Z ]+\d+([ae]) -'
    else:
        raise Exception
    match = re.search(regex, label)
    if match:
        return {
            'a': 'AF',
            'e': 'EN',
        }[match.group(1)]
    else:
        return None


def get_issue_number(referrer, label):
    url = urlparse(referrer)
    if url.hostname == 'www.gpwonline.co.za':
        regex = '^(\d+)[_ ]\d'
    elif url.hostname == 'www.westerncape.gov.za':
        regex = '^[a-zA-Z ]+(\d+)[ae]? ?(Extraordinary )?-'
    else:
        raise Exception
    try:
        return int(re.search(regex, label).group(1))
    except AttributeError:
        raise Exception("Can't find issue number in '%s'" % label)


def get_volume_number(referrer, cover_page_text):
    url = urlparse(referrer)
    if url.hostname == 'www.gpwonline.co.za':
        regex = 'Vol.\x00? ?(\d+)'
        try:
            return int(re.search(regex, cover_page_text).group(1))
        except AttributeError:
            raise NeedsOCRError("Can't find volume number in %r" % cover_page_text)
    elif url.hostname == 'www.westerncape.gov.za':
        return None
    else:
        raise Exception


def get_jurisdiction_code(referrer, label):
    url = urlparse(referrer)
    if url.hostname == 'www.gpwonline.co.za':
        if url.path == '/Gazettes/Pages/Provincial-Gazettes-Eastern-Cape.aspx':
            return 'ZA-EC'
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
                  part_number,
                  language_edition):
    if language_edition:
        language_edition_suffix = "-%s" % language_edition
    else:
        language_edition_suffix = ''
    if part_number is None:
        part_number_suffix = ''
    else:
        part_number_suffix = "-part-%s" % part_number
    if volume_number is None:
        return "%s-%s-no-%s%s%s%s" % (
            get_base_name(publication_title,
                          publication_subtitle),
            jurisdiction_code,
            issue_number,
            subissue_slug(publication_subtitle),
            part_number_suffix,
            language_edition_suffix
        )
    else:
        return "%s-%s-vol-%s-no-%s%s%s%s" % (
            get_base_name(publication_title,
                          publication_subtitle),
            jurisdiction_code,
            volume_number,
            issue_number,
            subissue_slug(publication_subtitle),
            part_number_suffix,
            language_edition_suffix
        )


def get_archive_path(unique_id,
                     jurisdiction_code,
                     special_issue,
                     publication_date):
    if special_issue:
        special_suffix = "-%s" % special_slug(special_issue)
    else:
        special_suffix = ''
    return "/%s/%s/%s-dated-%s%s.pdf" % (
        jurisdiction_code,
        publication_date.year,
        unique_id,
        publication_date.isoformat(),
        special_suffix,
    )


def get_base_name(title, subtitle):
    """Base name for archive path"""
    return {
        ('Government Gazette', None): 'government-gazette',
        ('Government Gazette', 'Regulation Gazette'): 'regulation-gazette',
        ('Government Gazette', 'Legal Gazette A'): 'government-gazette',
        ('Government Gazette', 'Legal Gazette B'): 'government-gazette',
        ('Government Gazette', 'Legal Gazette C'): 'government-gazette',
        ('Tender Bulletin', None): 'tender-bulletin',
        ('Provincial Gazette', None): 'provincial-gazette',
    }[(title, subtitle)]


def special_slug(special_issue):
    return {
        'Liquor Licenses': 'liquor-licenses',
        'Road Carrier Permits': 'road-carrier-permits'
    }[special_issue]


def subissue_slug(subtitle):
    return {
        'Legal Gazette A': '-legal-notices-A',
        'Legal Gazette B': '-legal-notices-B',
        'Legal Gazette C': '-legal-notices-C',
    }.get(subtitle, '')


if __name__ == "__main__":
    main()
