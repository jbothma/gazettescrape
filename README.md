# gazettescrape - South African Government Gazette scraper

## Non-python dependencies

- qpdf

## Minimal Configuration

Depends on the following DB URI being accessible or overridden to another

```
GAZETTE_DB_URI = 'postgres://gazettes@localhost/gazettes'
```

## Scraping

### Government Printing Works (GPW) spider

Optional Arguments:
```
start_url=http://www.gpwonline.co.za/Gazettes/Pages/Published-Liquor-Licenses.aspx
```

Override default start URL set with a single specific URL

e.g. locally

```
scrapy crawl -a gazette_type='http://www.gpwonline.co.za/Gazettes/Pages/Published-Liquor-Licenses.aspx' gpw
```
or
```
scrapy crawl gpw
```

### Western Cape Province

```
scrapy crawl western_cape
```

## DB Migrations

### Locally

```
PYTHONPATH=. alembic revision --autogenerate -m "I changed field something something"
PYTHONPATH=. alembic upgrade +1
```

### Production/other environments

Copy alembic.ini and refer to that.

```
PYTHONPATH=. alembic -c alembic_prod.ini upgrade +1
```

## Deployment

### To scrapinghub

First deploy dependencies as eggs, e.g.

```
shub deploy-egg --from-pypi psycopg2 79283
```

Then deploy the scrapy project itself

```
shub deploy 79283
```

## Extended configuration

To store files in S3, set/override the following settings:

```
FILES_STORE = "s3://code4sa-gazettes/scrape/"

AWS_ACCESS_KEY_ID = "..."
AWS_SECRET_ACCESS_KEY = "..."
```

To store the item feed in S3, set/override the following settings:

```
FEED_URI = s3://code4sa-gazettes/scrape-feed/spider-%(name)s/start-%(time)s.json
FEED_FORMAT = jsonlines
```

## Archival

Archival figures out the unique ID of the gazettes and archives them under
human-readable paths in the configured storage location.

### Locally/dev

```
source env-example
PYTHONPATH=. python gazettes/archive.py
```

### Production

```
dokku apps:create gazettescrape
dokku docker-options:add gazettescrape run,deploy "-v /home/dokku/gazettescrape/scrapedcache:/scrapedcache"
dokku config:set WEB_SCRAPE_STORE_URI="s3://aws-access-key-id:aws-access-key@code4sa-gazettes/scrape/" \
                 ARCHIVE_STORE_URI="s3://aws-access-key-id:aws-access-key@code4sa-gazettes/archive/" \
                 DB_URI="postgres://gazettes:password@hostname/gazettes" \
                 LOG_LEVEL="INFO"
# ... push repository to host ...
dokku run python gazettes/archive.py
```

## Gazette types

- National
  - National Gazette Liquour License Special Edition
  - Regulation Gazette
  - Extraordinary Gazette
- Provincial
  - Provincial Gazette Liquour License Gazette
  - Provincial Separate Gazette
  - Provincial Extraordinary Gazettes
    - e.g. demarcation changes
- Legal Gazette
- Separate Gazette

### Types as listed in GPW price guide

- National Gazette
- Regulation Gazette
- Petrol Price Gazette
- Road Carrier Permits
- Unclaimed Monies (justice, labour or lawyers)
- Parliament (acts, white paper, green paper)
- Legal Gazettes A, B anc C
- Tender Bulletin
- National Liquor License Gazette
- Provincial Gazette
- Provincial Liquor License Gazette
  - GPW publishes these:
    - Gauteng
    - Northern Cape
    - Mpumalanga

## Gazette Properties

- Issue number
- Title
- Publication Date
- Jurisdiction Level ("national" or "provincial")
- Jurisdiction (e.g. "RSA" or "KZN")
- Issue type? (e.g. "ordinary" "extraordinary")

## Publications

- http://www.gpwonline.co.za/Gazettes/Pages/Published-Separate-Gazettes.aspx
  - Page linked from
    - Name - (gazette number) (pub day-month) (govt dept or something)
      - e.g. "40132 11-07 National Treasury", "40133 11-07 Icasa"
    - Full Publication date
    - File name - same as link label with _ instead of spaces
  - Gazette contents
    - Cover page
      - Title: "Government Gazette"
      - Subtitle: none
      - Volume Number
      - Publication Date
      - Gazette Number
    - Table of Contents
      - Section Headings
        - e.g. "Board Notices" when filename is "BoardFSB"
        - e.g. "General Notices" when filename is "TradeIndus" or "Icasa"
        - e.g. "Government Notices" when filename is "NatTreas"
      - Notice Number
      - Notice Title
      - Gazette Number
      - Page number in gazette
    - Page header: "Government Gazette"
- http://www.gpwonline.co.za/Gazettes/Pages/Published-National-Regulation-Gazettes.aspx
  - Page linked from
    - Name
      - e.g. "... NationalRegulation" or "... Labour" or "... NatRegulation"
  - Gazette contents
    - Cover page
      - Title: "Government Gazette"
      - Subtitle: "Regulation Gazette"
      - Volume Number e.g. "Vol. 609"
      - Gazette Number e.g. "No. 39817"
      - Regulation Gazette Number e.g. "No. 10577"
    - Page header: "Government Gazette"
    - Table of Contents
      - Section Headings
        - e.g. "Government Notices"
          - Subsection Headings
            - e.g. "Environmental Affairs, Deptartment of" when name is "NationalRegulation"
            - e.g. "Labour, Department of" when name is "NationalRegulation" or "Labour"
- http://www.gpwonline.co.za/Gazettes/Pages/Published-National-Government-Gazettes.aspx
 - Page linked from
   - Name
     - e.g. "... NationalGovernment" or "... NationalGazette"
   Gazette contents
     - cover page
       - Title: "Government Gazette"
       - Subtitle: none
     - Weekly Index
       - description: "For purposes of reference, all Proclamations, Government Notices, General Notices and Board Notices published are included in the following table of contents which thus forms a weekly index. Let yourself be guided by the gazette numbers in the righthand column"
       - Section Headings
         - e.g. "Proclamation"
         - e.g. "Government Notice"
         - e.g. "General Notice"
         - e.g. "Board Notice"
     - Table of Contents

## Gazette number Series

- Each province's gazettes
  - ordinary
  - extraordinary
  - liquour
- National
  - general
  - separate
  - regulation
  - national liquor
  - legal notices A, B and C
  - Road carrier permits
- Tender Bulletin

National Gazettes and Tender Bulletins seem to fall under the same volume.

Western Cape Provincial Gazettes don't seem to have volumes - just one big series.

Free state doesn't have volumes and the series wraps on 1 April. Or at least it might have volumes and parts within an issue.

## Other notes

- Sometimes the cover page says "Part 1 of 2". It seems like the second part is included in the same PDF.
- An example of an official reference to a gazette
  - _Government Notice 2432, Government Gazette, Vol. 400, No. 19377 of 19 Octover 1998_
  - Republic of South Africa. 2006. _Government Tender Bulletin Vol. 488 No. 2424._ Pretoria: Government Printing Works

## Structured Gazette Archive

Gazettes are to be stored according to the following stucture:

```
/south-africa/1998/government-gazette-vol-400-no-19377-dated-1998-10-19.pdf
/western-cape/2007/western-cape-provincial-gazette-no-6454-dated-2007-07-27.pdf
/south-africa/2016/tender-bulletin-vol-611-no-2916-dated-2016-05-13.pdf
/free-state/2015/free-state-provincial-gazette-no-79-dated-2015-08-25.pdf
/eastern-cape/2016/eastern-cape-provincial-gazette-vol-23-no-3703-dated-2016-07-12.pdf
```

That is (jurisdiction)/(publication year)/(unique-id).pdf

Unique IDs for gazettes take the following form:

```
government-gazette-vol-400-no-19377-dated-1998-10-19
western-cape-provincial-gazette-no-6454-dated-2007-07-27
tender-bulletin-vol-611-no-2916-dated-2016-05-13
free-state-provincial-gazette-no-79-dated-2015-08-25
eastern-cape-provincial-gazette-vol-23-no-3703-dated-2016-07-12
```

That is:
- Government Gazettes (published by GWP)
  - government-gazette
  - -(volume and issue number)
  - -dated-(publication date in YYYY-MM-DD form)
- Provincial Gazettes (published by GPW)
  - (province short name)
  - -provincial-gazette
  - -(volume and issue number)
  - -dated-(publication date in YYYY-MM-DD form)
- Western Cape (published by Western Cape Provincial Govt)
  - western-cape-provincial-gazette
  - -(issue number)
  - -dated-(publication date in YYYY-MM-DD form)
- Free State (published by office of the premier of FS)
  - TBC
