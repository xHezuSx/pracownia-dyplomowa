"""
Database package.
Provides thread-safe database connection management and repository pattern access.
"""

# Connection management
from .connection import (
    get_connection,
    get_cursor,
    connect,
    ensure_connection,
    execute_query,
    close_connection
)

# Import all repository functions
from .repositories import *

__all__ = [
    # Connection
    'get_connection',
    'get_cursor',
    'connect',
    'ensure_connection',
    'execute_query',
    'close_connection',
    
    # Company
    'insert_company',
    'get_company_id',
    'get_all_companies',
    
    # Report
    'insert_report',
    'get_reports',
    
    # File
    'calculate_md5',
    'file_exists_by_md5',
    'insert_downloaded_file',
    'update_file_summary',
    'get_downloaded_files',
    'get_downloaded_file_by_name',
    
    # Job
    'insert_scheduled_job',
    'get_scheduled_job',
    'get_all_scheduled_jobs',
    'update_job_run_stats',
    'delete_scheduled_job',
    'insert_job_execution',
    'update_job_execution',
    'get_job_execution_logs',
    'get_active_jobs_view',
    
    # History
    'insert_search_history',
    'get_search_history',
    'insert_summary_report',
    'get_summary_reports',
    'get_summary_report_by_id',
    'get_company_stats_view',
]
