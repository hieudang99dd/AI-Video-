from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def ensure_sqlite_schema(target_engine=engine) -> None:
    """Create missing tables and add any newly introduced columns to existing SQLite tables."""
    Base.metadata.create_all(target_engine)
    if not str(target_engine.url).startswith("sqlite"):
        return
    inspector = inspect(target_engine)
    existing_tables = set(inspector.get_table_names())
    with target_engine.begin() as conn:
        for table_name, table in Base.metadata.tables.items():
            if table_name not in existing_tables:
                continue
            existing_cols = {c["name"] for c in inspector.get_columns(table_name)}
            for col in table.columns:
                if col.name not in existing_cols:
                    col_type = col.type.compile(dialect=target_engine.dialect)
                    default_sql = "NULL"
                    if not col.nullable:
                        if "INT" in col_type.upper():
                            default_sql = "0"
                        elif "FLOAT" in col_type.upper() or "REAL" in col_type.upper():
                            default_sql = "0.0"
                        elif "BOOL" in col_type.upper():
                            default_sql = "0"
                        elif "JSON" in col_type.upper():
                            default_sql = "'{}'"
                        else:
                            default_sql = "''"
                    conn.execute(
                        text(
                            f"ALTER TABLE {table_name} ADD COLUMN {col.name} {col_type} DEFAULT {default_sql}"
                        )
                    )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

