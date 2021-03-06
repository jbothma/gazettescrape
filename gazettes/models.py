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
    This models gazette files in the structured archive. It aims to provide
    information to refer to a specific gazette issue and as far as possible
    avoid duplicate files based the gazette's metadata while supporting
    optional part splits and language-specific editions.

    The unique ID is intended to identify a single instance of a document.
    we need to be able to match those now original_uris to already-scraped
    documents and not create duplicates in our exports or search interface:
    - If the website where gazettes are scraped from changes
    - If the labels used in the links where we scrape them from change
    - If we use scanned sources
    volume and issue number aren't sufficient - sometimes extraordinaries are
    published on existing issue numbers.
    Possible Strategies for automatically handling duplicates:
    - add an auto-increment integer suffix
    - add the label suffix e.g. Separate or Liquor or Elec
    - add the date
    None of these really deal with the fact that sometimes duplicate IDs
    are calculated because of mistakes e.g. real duplicates, or labels being
    incorrect on the website.
    e.g. http://www.gpwonline.co.za/Gazettes/Gazettes/2539_8-9_LimpSeparate.pdf
    and http://www.gpwonline.co.za/Gazettes/Gazettes/2539_3-7_LimpSeparate.pdf
    where the former is really 2593 with digits switched.

    The risk with automatically making IDs using some of the above strategies
    for these cases is that changes on a website or new sources could result in
    automatically letting thousands of duplicates in, while the number
    of duplicate keys are around 20 out of 5000 so it's fine to exclude them
    pending manual metadata extraction and ID definition.
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
    # The ISO 639-1 language code if it's a special edition in a given language.
    # Most gazettes are only issued in bilingual english/afrikaans/(xhoza)
    # editions but sometimes there are dedicated editions e.g. to announce an
    # ascented act.
    language_edition = Column(String, unique=False, nullable=True)
    # The part number. If the original_uri document includes all parts, or if the
    # relevant gazette consisted of a single part, this is null. Otherwise this
    # is the part number contained in the document
    part = Column(Integer, unique=False, nullable=True)
    created_at = Column(DateTime(timezone=True),
                        nullable=False,
                        server_default=func.now())
    # Date of the latest modification of this entry
    updated_at = Column(DateTime(timezone=True),
                        nullable=False,
                        server_default=func.now(),
                        onupdate=func.current_timestamp())

    def __repr__(self):
        return "<ArchivedGazette(id=%r, publication_title='%s', " \
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
            language_edition=dict['language_edition'],
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
                "maximum": 8000,
            },
            "language_edition": {"oneOf": [
                {"type": "string"},
                {"type": "null"},
            ]},
            "part": {"oneOf": [
                {"type": "integer"},
                {"type": "null"},
            ]},
        },
    }
