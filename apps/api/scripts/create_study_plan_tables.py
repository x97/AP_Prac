"""Create the additive study-plan tables.

Production normally runs the API with ``AUTO_CREATE_TABLES=true``, so a
restart creates these tables. This script is the explicit fallback for
environments where automatic table creation is disabled.
"""

from app.core.db import Base, engine, init_db


def main() -> None:
    init_db()
    table_names = [
        "classroom_homeworks",
        "classroom_homework_questions",
        "study_plans",
        "study_plan_items",
        "study_plan_assignments",
        "study_plan_tasks",
        "qa_threads",
        "qa_replies",
    ]
    tables = [Base.metadata.tables[name] for name in table_names]
    Base.metadata.create_all(bind=engine, tables=tables)
    print(f"created/verified {len(tables)} study-plan/Q&A tables")


if __name__ == "__main__":
    main()
