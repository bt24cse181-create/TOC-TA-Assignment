"""Database Connectivity & Schema Verification Script for WorkflowGuard.

Performs:
1. Configuration loading and verification
2. MySQL raw connectivity check (SELECT 1)
3. Database accessibility verification (workflowguard_db)
4. Inspection of initialized tables
5. Querying the seeded ONLINE_PAYMENT reference workflow
6. Safe connection disposal and actionable error diagnostics
"""

import sys
from pathlib import Path

# Ensure backend root is on sys.path so 'app.*' imports work from any working directory
BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select, text  # noqa: E402
from sqlalchemy.exc import DBAPIError, OperationalError  # noqa: E402

from app.core.config import ENV_FILE_PATH, settings  # noqa: E402
from app.core.database import SessionLocal, engine, sanitize_db_error  # noqa: E402
from app.models.workflow import Workflow, WorkflowState, WorkflowTransition  # noqa: E402


def check_database() -> int:
    """Run full diagnostic check against MySQL and print structured report."""
    print("=" * 70)
    print(" WorkflowGuard Database Connectivity Verification (Phase 1)")
    print("=" * 70)

    # 1. Configuration check
    print(f"\n[1] Configuration:")
    print(f"    - Environment File : {ENV_FILE_PATH} ({'FOUND' if ENV_FILE_PATH.exists() else 'NOT FOUND - using defaults/env'})")
    print(f"    - MySQL Host       : {settings.DB_HOST}")
    print(f"    - MySQL Port       : {settings.DB_PORT}")
    print(f"    - MySQL User       : {settings.DB_USER}")
    print(f"    - MySQL Database   : {settings.DB_NAME}")
    print(f"    - Sanitized URL    : {settings.database_url_masked}")

    # 2. Connection and SELECT 1 check
    print(f"\n[2] Testing MySQL raw connection (SELECT 1)...")
    try:
        with engine.connect() as conn:
            val = conn.execute(text("SELECT 1")).scalar()
            if val == 1:
                print("    -> SUCCESS: Executed 'SELECT 1'. Connection is operational.")
            else:
                print(f"    -> WARNING: Unexpected return value: {val}")

            # 3. Check current database
            current_db = conn.execute(text("SELECT DATABASE()")).scalar()
            print(f"\n[3] Target Database Check:")
            print(f"    - Active Database  : '{current_db}'")
            if current_db != settings.DB_NAME:
                print(f"    -> WARNING: Active database '{current_db}' does not match expected '{settings.DB_NAME}'")

            # 4. Table inspection
            table_rows = conn.execute(text("SHOW TABLES")).fetchall()
            existing_tables = [row[0] for row in table_rows]
            print(f"\n[4] Existing Tables in '{settings.DB_NAME}':")
            if not existing_tables:
                print("    -> No tables found. The database schema has not been imported yet.")
                print("    -> Run: Get-Content database/schema.sql | mysql -u root -p")
                return 0

            print(f"    -> Found {len(existing_tables)} tables: {', '.join(existing_tables)}")
            expected_tables = {
                "workflows",
                "workflow_states",
                "workflow_transitions",
                "process_cases",
                "event_logs",
                "anomaly_results",
            }
            missing = expected_tables - set(existing_tables)
            if missing:
                print(f"    -> WARNING: Missing expected tables: {missing}")
            else:
                print("    -> All 6 expected tables exist!")

    except (OperationalError, DBAPIError) as exc:
        sanitized_msg = sanitize_db_error(exc)
        print("\n" + "!" * 70)
        print(" [!] DATABASE CONNECTION FAILED")
        print("!" * 70)
        print(f"Details: {sanitized_msg}\n")
        print("Troubleshooting steps:")
        print(" 1. Check if the MySQL Windows Service is running:")
        print("    PowerShell: Get-Service MySQL80  (or: net start MySQL80)")
        print(" 2. Verify credentials in your .env file:")
        print(f"    File: {ENV_FILE_PATH}")
        print(f"    Make sure DB_USER and DB_PASSWORD match your local MySQL configuration.")
        print(" 3. If the database 'workflowguard_db' does not exist yet:")
        print("    Execute: mysql -u root -p < database/schema.sql")
        print("=" * 70)
        return 1
    except Exception as exc:
        sanitized_msg = sanitize_db_error(exc)
        print(f"\n[!] Unexpected error: {sanitized_msg}")
        return 1

    # 5. ORM Query for Seeded ONLINE_PAYMENT Workflow
    print(f"\n[5] Verifying Seeded Workflow via SQLAlchemy ORM...")
    try:
        with SessionLocal() as session:
            stmt = select(Workflow).where(Workflow.code == "ONLINE_PAYMENT")
            workflow = session.execute(stmt).scalar_one_or_none()

            if workflow:
                print(f"    -> Found workflow: '{workflow.name}' (Code: {workflow.code}, ID: {workflow.id})")
                print(f"       - Version   : {workflow.version}")
                print(f"       - Is Active : {workflow.is_active}")
                print(f"       - States    : {len(workflow.states)} states registered:")
                for state in workflow.states:
                    init_flag = " [INITIAL]" if state.is_initial else ""
                    term_flag = " [TERMINAL]" if state.is_terminal else ""
                    print(f"         * {state.state_key} ({state.state_type}){init_flag}{term_flag}")

                print(f"       - Transitions: {len(workflow.transitions)} transitions registered:")
                for t in workflow.transitions:
                    retry_info = f" (max retries: {t.max_retries})" if t.max_retries > 0 else ""
                    print(f"         * {t.from_state.state_key} --[{t.event_name}]--> {t.to_state.state_key}{retry_info}")
            else:
                print("    -> Notice: 'ONLINE_PAYMENT' workflow not found in 'workflows' table.")
                print("       Seed data can be inserted by applying database/schema.sql.")

    except Exception as exc:
        print(f"    -> Failed querying ORM models: {sanitize_db_error(exc)}")
        return 1
    finally:
        # 6. Ensure engine disposal on exit
        engine.dispose()

    print("\n" + "=" * 70)
    print(" Verification complete. Database connectivity & models are fully operational!")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    exit_code = check_database()
    sys.exit(exit_code)
