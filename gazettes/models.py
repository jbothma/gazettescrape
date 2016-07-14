from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Date, DateTime, Boolean
import sqlalchemy.sql.functions as func
from jsonschema import validate

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
    manually_ignored = Column(Boolean, default=False, nullable=False)

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
    # The location where the gazette was imported from
    # e.g. http://www.gpwonline.co.za/Gazettes/Gazettes/2923_1-7_TenderBulletin.pdf
    original_uri = Column(String, unique=True, nullable=False)
    # The path where the gazette is in the structured archive
    # e.g. /ZA-GP/2014/government-gazette-vol-123-no-45678-dated-2014-01-31.pdf
    archive_path = Column(String, unique=True, nullable=False)
    # e.g. "Government Gazette", "Provincial Gazette", "Tender Bulletin"
    publication_title = Column(String, unique=False, nullable=False)
    # e.g. null, "Legal Notices A", "Regulation Gazette"
    publication_subtitle = Column(String, unique=False, nullable=True)
    # When a gazette is issued under a standard title but dedicated to specific
    # contents e.g. null, "Liquor Licenses", "Road Carrier Permits"
    # or for Separates: "Icasa", "Treasury"
    # Not intended to make a gazette name/ID/reference unique, but rather to
    # qualify a file name to make it more useful to humans.
    special_issue = Column(String, unique=False, nullable=True)
    # AKA Gazette number. e.g. 40101
    issue_number = Column(Integer, unique=False, nullable=False)
    volume_number = Column(Integer, unique=False, nullable=True)
    # ISO 3166-1 alpha-2 country code or ISO 3166-2 principle subdivision code
    # e.g. ZA for South Africa, ZA-LP for Limpopo
    jurisdiction_code = Column(String, nullable=False)
    publication_date = Column(Date, nullable=False)
    # Unique ID for the gazette constructred from e.g. its title, issue number,
    # volume number etc. as appropriate for the particular publication.
    unique_id = Column(String, unique=True, nullable=False)
    # Date on which this entry was created
    pagecount = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True),
                        nullable=False,
                        server_default=func.now())
    # Date of the latest modification of this entry
    updated_at = Column(DateTime(timezone=True),
                        nullable=False,
                        server_default=func.now(),
                        onupdate=func.current_timestamp())

    def __repr__(self):
        return "<WebScrapedGazette(id=%r, publication_title='%s', " \
            "jurisdiction_code='%s', volume_number=%s, issue_number=%s, " \
            "publication_date='%s')>" \
            % (self.id, self.publication_title, self.jurisdiction_code,
               self.volume_number, self.issue_number, self.publication_date)

    @staticmethod
    def fromDict(dict):
        valdict = dict.copy()
        valdict['publication_date'] = valdict['publication_date'].isoformat()
        validate(valdict, ArchivedGazette.schema)
        return ArchivedGazette(
            original_uri=dict['original_uri'],
            archive_path=dict['archive_path'],
            publication_title=dict['publication_title'],
            publication_subtitle=dict['publication_subtitle'],
            special_issue=dict['special_issue'],
            issue_number=dict['issue_number'],
            volume_number=dict['volume_number'],
            jurisdiction_code=dict['jurisdiction_code'],
            publication_date=dict['publication_date'],
            unique_id=dict['unique_id'],
            pagecount=dict['pagecount'],
        )

    schema = {
        "type": "object",
        "properties": {
            "original_uri": {"type": "string"},
            "archive_path": {"type": "string"},
            "publication_title": {"type": "string"},
            "publication_subtitle": {"oneOf": [
                {"type": "string"},
                {"type": "null"},
            ]},
            "special_issue": {"oneOf": [
                {"type": "string"},
                {"type": "null"},
            ]},
            "issue_number": {
                "type": "integer",
                "minimum": 1,
                "maximum": 80000,
            },
            "volume_number": {"oneOf": [
                {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 2000,
                },
                {"type": "null"}
            ]},
            "jurisdiction_code": {"type": "string"},
            "publication_date": {"type": "string"},
            "unique_id": {"type": "string"},
            "pagecount": {
                "type": "integer",
                "minimum": 1,
                "maximum": 3200,
            },
        },
    }
