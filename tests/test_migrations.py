from pathlib import Path

import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from app.db.base import Base

REPO_ROOT = Path(__file__).resolve().parent.parent

LEGACY_SCHEMA = """
CREATE TABLE phone_numbers (
    id INTEGER NOT NULL PRIMARY KEY,
    number VARCHAR,
    description VARCHAR,
    is_active BOOLEAN,
    created_at DATETIME DEFAULT (CURRENT_TIMESTAMP),
    updated_at DATETIME,
    entity_type VARCHAR,
    business_name VARCHAR,
    business_category VARCHAR,
    business_industry VARCHAR,
    business_location VARCHAR,
    is_spam BOOLEAN,
    spam_reports INTEGER,
    disabled BOOLEAN,
    monitoring_frequency INTEGER,
    complaints JSON
);
CREATE INDEX ix_phone_numbers_id ON phone_numbers (id);
CREATE UNIQUE INDEX ix_phone_numbers_number ON phone_numbers (number);
"""


def alembic_config(url: str) -> Config:
    config = Config(str(REPO_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", url)
    return config


def test_upgrade_adds_owner_and_per_owner_uniqueness(tmp_path):
    url = f"sqlite:///{tmp_path}/legacy.db"
    engine = sa.create_engine(url)
    with engine.begin() as connection:
        for statement in LEGACY_SCHEMA.strip().split(";"):
            if statement.strip():
                connection.exec_driver_sql(statement)
        connection.exec_driver_sql("INSERT INTO phone_numbers (id, number) VALUES (1, '+15125550110')")

    command.upgrade(alembic_config(url), "head")

    inspector = sa.inspect(engine)
    assert "users" in inspector.get_table_names()
    assert "owner_id" in {column["name"] for column in inspector.get_columns("phone_numbers")}

    with engine.begin() as connection:
        assert connection.exec_driver_sql("SELECT owner_id FROM phone_numbers WHERE id = 1").scalar() is None
        connection.exec_driver_sql("INSERT INTO users (id, api_key_hash) VALUES (1, 'a'), (2, 'b')")
        connection.exec_driver_sql("INSERT INTO phone_numbers (owner_id, number) VALUES (1, '+15125550111')")
        connection.exec_driver_sql("INSERT INTO phone_numbers (owner_id, number) VALUES (2, '+15125550111')")

    with engine.begin() as connection:
        try:
            connection.exec_driver_sql("INSERT INTO phone_numbers (owner_id, number) VALUES (1, '+15125550111')")
        except sa.exc.IntegrityError:
            pass
        else:
            raise AssertionError("duplicate number for one owner was accepted")


def test_upgrade_is_a_no_op_on_a_schema_from_create_all(tmp_path):
    url = f"sqlite:///{tmp_path}/fresh.db"
    engine = sa.create_engine(url)
    Base.metadata.create_all(bind=engine)
    command.upgrade(alembic_config(url), "head")

    assert "owner_id" in {column["name"] for column in sa.inspect(engine).get_columns("phone_numbers")}
