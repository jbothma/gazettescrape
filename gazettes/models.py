from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Date, DateTime
import sqlalchemy.sql.functions as func

Base = declarative_base()


class WebScrapedGazette(Base):
    """
    Data about a gazette that was scraped from the web
    """
    __tablename__ = 'web_scraped_gazette'

    id = Column(Integer, primary_key=True)
    original_uri = Column(String,
                          unique=True,
                          nullable=False)
    store_path = Column(String,
                        unique=True,
                        nullable=False)
    label = Column(String,
                   nullable=False)
    published_date = Column(Date,
                            nullable=False)
    first_seen = Column(DateTime(timezone=True),
                        nullable=False)
    last_seen = Column(DateTime(timezone=True),
                       nullable=False)
    created_at = Column(DateTime(timezone=True),
                        nullable=False,
                        server_default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        nullable=False,
                        server_default=func.now(),
                        onupdate=func.current_timestamp())
    referrer = Column(String,
                      nullable=False,
                      index=True)

    def __repr__(self):
        return "<WebScrapedGazette(id=%r, label='%s', published_date='%s'," \
            " original_uri='%s', store_path='%s')>" \
            % (self.id, self.label, self.published_date, self.original_uri, self.store_path)


class ArchivedGazette(Base):
    """
    Data about a gazette in the archive
    """
    __tablename__ = 'archived_gazette'

    id = Column(Integer, primary_key=True)
    original_uri = Column(String,
                          unique=True,
                          nullable=False)
    publication_url = Column(String,
                             unique=False,
                             nullable=True)
    issue_url = Column(String,
                       unique=False,
                       nullable=True)
    publication_title = Column(String,
                               unique=True,
                               nullable=False)
    jurisdiction = Column(String,
                          nullable=False)
    publication_date = Column(Date,
                              nullable=False)
    created_at = Column(DateTime(timezone=True),
                        nullable=False,
                        server_default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        nullable=False,
                        server_default=func.now(),
                        onupdate=func.current_timestamp())

    def __repr__(self):
        return "<WebScrapedGazette(id=%r, label='%s', published_date='%s'," \
            " original_uri='%s', store_path='%s')>" \
            % (self.id, self.label, self.published_date, self.original_uri, self.store_path)
