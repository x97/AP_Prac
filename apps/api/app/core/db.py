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


# Additive columns that ``create_all`` cannot add to an existing ``users``
# table. Each entry maps column name to SQL type. SQLite accepts plain
# TIMESTAMP / BOOLEAN and stores ISO strings / 0-1, which SQLAlchemy maps back.
_USER_PROFILE_COLUMNS: dict[str, dict[str, str]] = {
    "sqlite": {
        "grade": "VARCHAR(32)",
        "region": "VARCHAR(64)",
        "target_score": "INTEGER",
        "studied_psychology": "BOOLEAN",
        "study_mode": "VARCHAR(32)",
        "exam_time": "VARCHAR(16)",
        "teacher_note": "TEXT",
        "profile_completed_at": "TIMESTAMP",
    },
    "postgresql": {
        "grade": "VARCHAR(32)",
        "region": "VARCHAR(64)",
        "target_score": "INTEGER",
        "studied_psychology": "BOOLEAN",
        "study_mode": "VARCHAR(32)",
        "exam_time": "VARCHAR(16)",
        "teacher_note": "TEXT",
        "profile_completed_at": "TIMESTAMP WITH TIME ZONE",
    },
}


def _ensure_user_profile_columns(bind) -> None:  # noqa: ANN001
    from sqlalchemy import inspect

    if "users" not in inspect(bind).get_table_names():
        return
    existing = {column["name"] for column in inspect(bind).get_columns("users")}
    dialect = "postgresql" if bind.dialect.name == "postgresql" else "sqlite"
    for name, ddl in _USER_PROFILE_COLUMNS[dialect].items():
        if name in existing:
            continue
        bind.execute(text(f"ALTER TABLE users ADD COLUMN {name} {ddl}"))


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
                _ensure_user_profile_columns(conn)
            finally:
                conn.execute(
                    text("SELECT pg_advisory_unlock(:key)"),
                    {"key": _INIT_DB_LOCK_KEY},
                )
        return

    settings.app_db_path.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        _ensure_user_profile_columns(conn)
