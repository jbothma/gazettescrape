"""
A tool to take gazettes from various sources, store them in a nice
structured path, and maintain a database of the gazettes in their
structured paths.
"""

WEB_SCRAPE_STORE_PATH = "../scrapyfilestore"
LOCAL_CACHE_STORE_PATH = "../archivecachefilestore"
ARCHIVE_STORE_PATH = "../archivefilestore"

        self.engine = create_engine(self.db_uri)
        self.Session = sessionmaker(bind=self.engine)

        session = self.Session()
        webgazette = session.query(WebScrapedGazette).filter_by(original_uri=original_uri).first()

                self.engine.dispose()


                if __name__ == "__main__":
    main()
