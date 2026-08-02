import logging
from pathlib import Path

from psycopg import connect

from .config import get_settings


logger = logging.getLogger(__name__)

TABLES = {
    "shows": (
        "show_id,name,number_of_seasons,number_of_episodes,adult,in_production,"
        "original_name,popularity,eposide_run_time,type_id,status_id"
    ),
    "show_votes": "vote_count,vote_average,show_id",
    "air_dates": "is_first,show_id,date",
    "genre_types": "genre_type_id,genre_name",
    "genres": "show_id,genre_type_id",
    "created_by_types": "created_by_type_id,created_by_name",
    "created_by": "show_id,created_by_type_id",
    "production_company_types": (
        "production_company_type_id,production_company_name"
    ),
    "production_companies": "show_id,production_company_type_id",
    "production_country_types": (
        "production_country_type_id,production_country_name"
    ),
    "production_countries": "show_id,production_country_type_id",
}

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS shows (
    show_id BIGINT PRIMARY KEY,
    name TEXT,
    number_of_seasons INTEGER,
    number_of_episodes INTEGER,
    adult BOOLEAN,
    in_production BOOLEAN,
    original_name TEXT,
    popularity DOUBLE PRECISION,
    eposide_run_time INTEGER,
    type_id INTEGER,
    status_id INTEGER
);
CREATE TABLE IF NOT EXISTS show_votes (
    vote_count INTEGER,
    vote_average DOUBLE PRECISION,
    show_id BIGINT PRIMARY KEY
);
CREATE TABLE IF NOT EXISTS air_dates (
    is_first BOOLEAN,
    show_id BIGINT,
    date DATE
);
CREATE TABLE IF NOT EXISTS genre_types (
    genre_type_id INTEGER PRIMARY KEY,
    genre_name TEXT
);
CREATE TABLE IF NOT EXISTS genres (
    show_id BIGINT,
    genre_type_id INTEGER
);
CREATE TABLE IF NOT EXISTS created_by_types (
    created_by_type_id BIGINT PRIMARY KEY,
    created_by_name TEXT
);
CREATE TABLE IF NOT EXISTS created_by (
    show_id BIGINT,
    created_by_type_id BIGINT
);
CREATE TABLE IF NOT EXISTS production_company_types (
    production_company_type_id BIGINT PRIMARY KEY,
    production_company_name TEXT
);
CREATE TABLE IF NOT EXISTS production_companies (
    show_id BIGINT,
    production_company_type_id BIGINT
);
CREATE TABLE IF NOT EXISTS production_country_types (
    production_country_type_id INTEGER PRIMARY KEY,
    production_country_name TEXT
);
CREATE TABLE IF NOT EXISTS production_countries (
    show_id BIGINT,
    production_country_type_id INTEGER
);
"""

INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_votes_average ON show_votes (vote_average DESC);
CREATE INDEX IF NOT EXISTS idx_shows_popularity ON shows (popularity DESC);
CREATE INDEX IF NOT EXISTS idx_air_dates_show ON air_dates (show_id);
CREATE INDEX IF NOT EXISTS idx_air_dates_date ON air_dates (date);
CREATE INDEX IF NOT EXISTS idx_genres_show ON genres (show_id);
CREATE INDEX IF NOT EXISTS idx_genres_type ON genres (genre_type_id);
CREATE INDEX IF NOT EXISTS idx_countries_show ON production_countries (show_id);
CREATE INDEX IF NOT EXISTS idx_countries_type ON production_countries (production_country_type_id);
"""


def _copy_csv(cursor, table: str, columns: str, csv_path: Path) -> None:
    copy_sql = (
        f"COPY {table} ({columns}) FROM STDIN "
        f"WITH (FORMAT CSV, HEADER TRUE, FORCE_NULL ({columns}))"
    )
    with csv_path.open("r", encoding="utf-8-sig", newline="") as source:
        with cursor.copy(copy_sql) as copy:
            while chunk := source.read(1024 * 1024):
                copy.write(chunk)


def seed_database() -> None:
    settings = get_settings()
    data_dir = Path(settings.data_dir)
    if not data_dir.exists():
        raise FileNotFoundError(f"Dataset directory does not exist: {data_dir}")

    with connect(settings.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(SCHEMA_SQL)
            cursor.execute("SELECT COUNT(*) FROM shows")
            if cursor.fetchone()[0] > 0:
                logger.info("TV shows dataset already loaded")
                return

            logger.info("Loading TV shows dataset from %s", data_dir)
            for table, columns in TABLES.items():
                csv_path = data_dir / f"{table}.csv"
                if not csv_path.exists():
                    raise FileNotFoundError(f"Missing dataset file: {csv_path}")
                _copy_csv(cursor, table, columns, csv_path)
                logger.info("Loaded %s", table)

            cursor.execute(INDEX_SQL)
            connection.commit()
            logger.info("Dataset loading complete")
