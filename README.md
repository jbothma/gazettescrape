# gazettescrape

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
