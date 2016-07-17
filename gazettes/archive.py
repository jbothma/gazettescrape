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
import shutil
import re
from tempfile import mkdtemp
import subprocess
import logging
import pdb
import sys
import getopt
import boto
from boto.s3.key import Key

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

WEB_SCRAPE_STORE_URI = os.environ.get('WEB_SCRAPE_STORE_URI')
LOCAL_CACHE_STORE_PATH = os.environ.get('LOCAL_CACHE_STORE_PATH')
ARCHIVE_STORE_URI = os.environ.get('ARCHIVE_STORE_URI')
GAZETTE_DB_URI = os.environ.get('GAZETTE_DB_URI')
DB_URI = os.environ.get('DB_URI')
LOG_LEVEL = os.environ.get('LOG_LEVEL')

logger.setLevel(LOG_LEVEL)


class NeedsOCRError(Exception):
    pass


def main(argv):
    pdb_on_error = False

    try:
        opts, args = getopt.getopt(argv, "hd", ["help", "pdb"])
    except getopt.GetoptError:
        usage()
        sys.exit(2)

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
            sys.exit()
        elif opt in ('-d', '--pdb'):
            pdb_on_error = True

    if pdb_on_error:
        try:
            archive(pdb_on_error)
        except Exception, e:
            logger.exception(e)
            ype, value, tb = sys.exc_info()
            pdb.post_mortem(tb)
    else:
        archive(pdb_on_error)


def archive(pdb_on_error):
    tmpdir = mkdtemp(prefix='gazettes-archive')
    engine = create_engine(DB_URI)
    Session = sessionmaker(bind=engine)
    webscraped_sesh = Session()
    scrapestore_get = get_function(WEB_SCRAPE_STORE_URI)
    archive_put = put_function(ARCHIVE_STORE_URI)
    cache_path = LOCAL_CACHE_STORE_PATH

    for webgazette in webscraped_sesh.query(WebScrapedGazette)\
                                     .filter(WebScrapedGazette.manually_ignored == False)\
                                     .all():
        logger.debug('------------------------------')
        archive_sesh = Session()

        # Get the PDF
        cached_gazette_path = os.path.join(cache_path, webgazette.store_path)
        if not os.path.exists(cached_gazette_path):
            logger.debug("Cache MISS %s", webgazette.store_path)
            scrapestore_get(webgazette.store_path, cached_gazette_path)
        else:
            logger.debug("Cache HIT %s", webgazette.store_path)

        # Archive the PDF
        try:
            logger.debug("original_uri: %s", webgazette.original_uri)
            cover_page_text = get_cover_page_text(cached_gazette_path)
            if is_gazette_index(cover_page_text):
                logger.debug("Ignoring index %r", webgazette.original_uri)
                continue

            pagecount = get_page_count(cached_gazette_path)
            publication_title = get_publication_title(webgazette.referrer,
                                                      webgazette.label)
            publication_subtitle = get_publication_subtitle(webgazette.referrer,
                                                            webgazette.label)
            special_issue = get_special_issue(webgazette.referrer)
            language_edition = get_language_edition(webgazette.referrer,
                                                    webgazette.label)
            issue_number = get_issue_number(webgazette.referrer, webgazette.label)
            volume_number = get_volume_number(webgazette.referrer, cover_page_text)
            jurisdiction_code = get_jurisdiction_code(webgazette.referrer,
                                                      webgazette.label)
            part_number = get_part_number(webgazette.referrer,
                                          webgazette.label)
            unique_id = get_unique_id(publication_title,
                                      publication_subtitle,
                                      jurisdiction_code,
                                      volume_number,
                                      issue_number,
                                      part_number,
                                      language_edition)
            archive_path = get_archive_path(unique_id,
                                            jurisdiction_code,
                                            special_issue,
                                            webgazette.published_date)
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

            existing_archived_gazette = archive_sesh \
                                       .query(ArchivedGazette)\
                                       .filter(ArchivedGazette.unique_id
                                               == archived_gazette.unique_id)\
                                       .first()
            if existing_archived_gazette:
                if existing_archived_gazette.original_uri == webgazette.original_uri:
                    logger.debug("%r exists in the archive", archived_gazette.unique_id)
                else:
                    logger.error("Skipping %r because another ArchivedGazette " \
                                 "exists with the same unique_id (%r)",
                                 webgazette,
                                 existing_archived_gazette)
            else:
                logger.debug("Arching %r", archived_gazette.unique_id)
                archive_put(cached_gazette_path, archived_gazette.archive_path)
                archive_sesh.add(archived_gazette)
                logger.debug("Done")
        except Exception, e:
            logger.exception("Error for %r", webgazette)
            if pdb_on_error:
                ype, value, tb = sys.exc_info()
                pdb.post_mortem(tb)

        archive_sesh.commit()
    webscraped_sesh.rollback()
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
        regex = '^(\d+)[_ ]\w'
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
    return "%s/%s/%s-dated-%s%s.pdf" % (
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
        ('Government Gazette', 'Regulation Gazette'): 'government-gazette',
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
        'Regulation Gazette': '-regulation-gazette',
    }.get(subtitle, '')


def ensure_dirs(path):
    dirs = os.path.dirname(path)
    if not os.path.exists(dirs):
        os.makedirs(dirs)


def get_function(store_uri):
    uri = urlparse(store_uri)
    if uri.scheme == 'file':
        store_path = uri.path
        return lambda from_relative_path, to_filename: local_get(store_path,
                                                                 from_relative_path,
                                                                 to_filename)
    elif uri.scheme == 's3':
        access_key_id = uri.username
        access_key = uri.password
        bucket_name = uri.hostname
        key_prefix = uri.path
        conn = boto.connect_s3(access_key_id, access_key)
        bucket = conn.get_bucket(bucket_name)
        return lambda from_relative_path, to_filename: s3_get(bucket,
                                                              key_prefix,
                                                              from_relative_path,
                                                              to_filename)
    else:
        raise Exception


def local_get(store_path, from_relative_path, to_filename):
    full_from_path = os.path.join(store_path, from_relative_path)
    ensure_dirs(to_filename)
    shutil.copyfile(full_from_path, to_filename)


def s3_get(bucket, from_key_prefix, from_key_suffix, to_filename):
    key = os.path.join(from_key_prefix, from_key_suffix)
    k = Key(bucket)
    k.key = key
    k.get_contents_to_filename(to_filename)


def put_function(store_uri):
    uri = urlparse(store_uri)
    if uri.scheme == 'file':
        store_path = uri.path
        return lambda from_filename, to_relative_path: local_put(from_filename,
                                                                 store_path,
                                                                 to_relative_path)
    elif uri.scheme == 's3':
        access_key_id = uri.username
        access_key = uri.password
        bucket_name = uri.hostname
        key_prefix = uri.path
        conn = boto.connect_s3(access_key_id, access_key)
        bucket = conn.get_bucket(bucket_name)
        return lambda from_filename, to_relative_path: s3_put(bucket,
                                                              from_filename,
                                                              key_prefix,
                                                              to_relative_path)
    else:
        raise Exception


def local_put(from_filename, store_path, to_relative_path):
    full_to_path = os.path.join(store_path, to_relative_path)
    ensure_dirs(full_to_path)
    shutils.copyfile(from_filename, full_to_path)


def s3_put(bucket, from_filename, to_key_prefix, to_key_suffix):
    key = os.path.join(to_key_prefix, to_key_suffix)
    k = Key(bucket)
    k.key = key
    k.set_contents_from_filename(from_filename)
    k.make_public()



if __name__ == "__main__":
    main(sys.argv[1:])
