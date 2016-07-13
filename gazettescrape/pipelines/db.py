# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sqlalchemy.sql.functions as func
from gazettes.models import GazetteMeta


class DBPipeline(object):
    def __init__(self, db_uri):
        self.db_uri = db_uri
        self.engine = None
        self.Session = None

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            db_uri=crawler.settings.get('GAZETTE_DB_URI'),
        )

    def open_spider(self, spider):
        self.engine = create_engine(self.db_uri)
        self.Session = sessionmaker(bind=self.engine)

    def close_spider(self, spider):
        self.engine.dispose()

    def process_item(self, item, spider):
        original_uri = item['file_urls'][0]
        session = self.Session()
        gazette = session.query(GazetteMeta).filter_by(original_uri=original_uri).first()
        if gazette:
            gazette.last_seen = func.now()
            gazette.referrer = item['referrer']
        else:
            gazette = GazetteMeta(
                label=item['label'],
                original_uri=item['file_urls'][0],
                referrer=item['referrer'],
                store_path=item['files'][0]['path'],
                published_date=item['published_date'],
                last_seen=func.now(),
                first_seen=func.now()
            )
            session.add(gazette)
        session.commit()
        return item
