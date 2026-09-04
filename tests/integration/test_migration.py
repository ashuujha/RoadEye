"""A genuinely empty database, independent of the database used by API tests."""

import os
import subprocess
import sys
from uuid import uuid4

import psycopg
from psycopg import sql
from roadeye.config import settings
from sqlalchemy.engine import make_url


def test_clean_migration_and_postgis():
    base = make_url(settings.database_url)
    name = "roadeye_migration_" + uuid4().hex
    admin_url = base.set(drivername="postgresql", database="postgres").render_as_string(
        hide_password=False
    )
    with psycopg.connect(admin_url, autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE DATABASE {} ENCODING 'UTF8' TEMPLATE template0").format(sql.Identifier(name)))
        try:
            target = base.set(database=name).render_as_string(hide_password=False)
            result = subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                env={**os.environ, "ROADEYE_DATABASE_URL": target},
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, result.stderr
            native = base.set(database=name, drivername="postgresql").render_as_string(
                hide_password=False
            )
            with psycopg.connect(native) as check:
                assert (
                    check.execute("SELECT version_num FROM alembic_version").fetchone()[0]
                    == "20260905_immutable"
                )
                assert (
                    check.execute("SELECT ST_Distance(ST_Point(0,0), ST_Point(3,4))").fetchone()[0]
                    == 5
                )
                assert (
                    check.execute(
                        "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'"
                    ).fetchone()[0]
                    >= 20
                )
        finally:
            connection.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))
