"""
Database Connection Module v2.0 - BACKWARD COMPATIBILITY WRAPPER
Supports: companies, reports, search_history, scheduled_jobs, 
          summary_reports, job_execution_log, downloaded_files
Thread-safe with thread-local connections.

NOTE: This file now imports from src/database/ for clean architecture.
All new code should import directly from src.database instead of this file.
"""

# Import all functions from new structure
from src.database.connection import (
    get_connection,
    get_cursor,
    connect,
    ensure_connection,
    execute_query,
    close_connection,
    HOST,
    USER,
    PASSWORD,
    DATABASE,
    _thread_local
)

from src.database.repositories.company_repo import (
    insert_company,
    get_company_id,
    get_all_companies
)

from src.database.repositories.report_repo import (
    insert_report,
    get_reports
)

from src.database.repositories.file_repo import (
    calculate_md5,
    file_exists_by_md5,
    insert_downloaded_file,
    update_file_summary,
    get_downloaded_files,
    get_downloaded_file_by_name
)

from src.database.repositories.job_repo import (
    insert_scheduled_job,
    get_scheduled_job,
    get_all_scheduled_jobs,
    update_job_run_stats,
    delete_scheduled_job,
    insert_job_execution,
    update_job_execution,
    get_job_execution_logs,
    get_active_jobs_view
)

from src.database.repositories.history_repo import (
    insert_search_history,
    get_search_history,
    insert_summary_report,
    get_summary_reports,
    get_summary_report_by_id,
    get_company_stats_view
)

# Backward compatibility - expose connection and cursor as module-level properties
def _update_globals():
    """Update module globals for backward compatibility"""
    import sys
    current_module = sys.modules[__name__]
    current_module.connection = get_connection()
    current_module.cursor = get_cursor()
    return current_module.connection, current_module.cursor


if __name__ == "__main__":
    print("Database Connection Module v2.0 - Compatibility Wrapper")
    print(f"Connected to: {DATABASE}")
    print(f"Available tables: companies, reports, search_history,")
    print(f"                  scheduled_jobs, summary_reports,")
    print(f"                  job_execution_log, downloaded_files")
    print()
    print("NOTE: New code should import from src.database")
    print()
    
    # Test connection
    companies = get_all_companies()
    print(f"Found {len(companies)} companies in database")
    for company in companies[:5]:
        print(f"  - {company['name']}")
    
    if len(companies) > 5:
        print(f"  ... and {len(companies) - 5} more")
