from __future__ import annotations

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import get_settings

settings = get_settings()

# PostgreSQL advisory lock shared by every uvicorn worker during create_all.
_INIT_DB_LOCK_KEY = 737373

if settings.resolved_database_url.startswith("sqlite"):
    engine = create_engine(
        settings.resolved_database_url,
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
        future=True,
    )

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_connection, _connection_record):  # noqa: ANN001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()
else:
    engine = create_engine(settings.resolved_database_url, pool_pre_ping=True, future=True)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    future=True,
)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    # Import models so metadata is populated before create_all.
    from app.users import models  # noqa: F401

    if not settings.auto_create_tables:
        return

    if engine.dialect.name == "postgresql":
        # ``uvicorn --workers 2`` runs this in both workers. Serialize table
        # creation, otherwise one worker fails with a duplicate pg_type error.
        with engine.begin() as conn:
            conn.execute(
                text("SELECT pg_advisory_lock(:key)"), {"key": _INIT_DB_LOCK_KEY}
            )
            try:
                Base.metadata.create_all(bind=conn)
            finally:
                conn.execute(
                    text("SELECT pg_advisory_unlock(:key)"),
                    {"key": _INIT_DB_LOCK_KEY},
                )
        return

    settings.app_db_path.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
