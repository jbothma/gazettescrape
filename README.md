# gazettescrape - South African Government Gazette scraper

## Minimal Configuration

Depends on the following DB URI being accessible or overridden to another

```
GAZETTE_DB_URI = 'postgres://gazettes@localhost/gazettes'
```

## Running

## Government Printing Works (GPW) spider

Arguments:
```
gazette_type='http://www.gpwonline.co.za/Gazettes/Pages/Published-Liquor-Licenses.aspx'
start_url='http://www.gpwonline.co.za/Gazettes/Pages/Published-Liquor-Licenses.aspx'
```

If start_url is not provided, it uses gazette_type as start_url

e.g. locally

```
scrapy crawl -a gazette_type='http://www.gpwonline.co.za/Gazettes/Pages/Published-Liquor-Licenses.aspx' gpw
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

## Gazette types

- National
  - National Gazette Liquour License Special Edition
  - Regulation Gazette
  - Extraordinary Gazette
- Provincial
  - Provincial Gazette Liquour License Special Edition
  - Provincial Separate Gazette
  - Provincial Extraordinary Gazettes
    - e.g. demarcation changes
- Legal Gazette
- Separate Gazette