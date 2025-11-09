"""
Job Repository
CRUD operations for scheduled_jobs and job_execution_log tables.
Manages CRON job scheduling and execution tracking.
"""

import json
from typing import Optional, List, Dict
from datetime import datetime
from ..connection import get_connection, get_cursor, ensure_connection, execute_query


# ============================================================================
# SCHEDULED_JOBS TABLE - Cron Job Management
# ============================================================================

def insert_scheduled_job(
    job_name: str,
    company: str,
    date_from: str,
    date_to: str,
    model: str,
    cron_schedule: str,
    enabled: bool = True,
    report_limit: int = 5,
    report_types: List[str] = None,
    report_categories: List[str] = None
) -> int:
    """
    Insert or update scheduled job (UPSERT operation).
    
    Args:
        job_name: Unique job identifier
        company: Company ticker/name
        date_from: Start date (DD-MM-YYYY or YYYY-MM-DD)
        date_to: End date (DD-MM-YYYY or YYYY-MM-DD)
        model: AI model to use for summarization
        cron_schedule: Cron expression (e.g., "0 9 * * MON")
        enabled: Whether job is active
        report_limit: Maximum number of reports to process
        report_types: List of report types to include
        report_categories: List of categories to include
    
    Returns:
        int: Job ID or 0 on error
    """
    try:
        # Ensure report_limit column exists (compatibility with older schema)
        try:
            execute_query(
                "ALTER TABLE scheduled_jobs ADD COLUMN report_limit INT DEFAULT 5 AFTER cron_schedule"
            )
        except:
            pass  # Column already exists or error occurred
        
        # Convert date format from DD-MM-YYYY to YYYY-MM-DD
        def convert_date(date_str):
            if not date_str:
                return None
            if '-' in date_str and len(date_str) == 10:
                parts = date_str.split('-')
                if len(parts[0]) == 2:  # DD-MM-YYYY
                    return f"{parts[2]}-{parts[1]}-{parts[0]}"
            return date_str
        
        date_from = convert_date(date_from)
        date_to = convert_date(date_to)
        
        # Convert lists to JSON
        report_types_json = json.dumps(report_types) if report_types else None
        report_categories_json = json.dumps(report_categories) if report_categories else None
        
        sql = """
            INSERT INTO scheduled_jobs
            (job_name, company, date_from, date_to, model, cron_schedule,
             enabled, report_limit, report_types, report_categories)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                company = VALUES(company),
                date_from = VALUES(date_from),
                date_to = VALUES(date_to),
                model = VALUES(model),
                cron_schedule = VALUES(cron_schedule),
                enabled = VALUES(enabled),
                report_limit = VALUES(report_limit),
                report_types = VALUES(report_types),
                report_categories = VALUES(report_categories),
                updated_at = NOW()
        """
        
        result = execute_query(sql, (
            job_name, company, date_from, date_to, model, cron_schedule,
            enabled, report_limit, report_types_json, report_categories_json
        ))
        
        return result if result else 0
    except Exception as e:
        print(f"Error inserting scheduled job: {e}")
        # Try again without report_limit column (backward compatibility)
        try:
            sql_fallback = """
                INSERT INTO scheduled_jobs
                (job_name, company, date_from, date_to, model, cron_schedule, enabled, report_types, report_categories)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    company = VALUES(company),
                    date_from = VALUES(date_from),
                    date_to = VALUES(date_to),
                    model = VALUES(model),
                    cron_schedule = VALUES(cron_schedule),
                    enabled = VALUES(enabled),
                    report_types = VALUES(report_types),
                    report_categories = VALUES(report_categories),
                    updated_at = NOW()
            """
            result = execute_query(sql_fallback, (
                job_name, company, date_from, date_to, model, cron_schedule,
                enabled, report_types_json, report_categories_json
            ))
            print(f"✅ Saved job without report_limit column (backward compat)")
            return result if result else 0
        except Exception as e2:
            print(f"Error (fallback also failed): {e2}")
            raise e


def get_scheduled_job(job_name: str) -> Optional[Dict]:
    """
    Get scheduled job by name.
    
    Args:
        job_name: Job identifier
    
    Returns:
        Dict: Job record with parsed JSON fields or None if not found
    """
    ensure_connection()
    try:
        cursor = get_cursor()
        sql = "SELECT * FROM scheduled_jobs WHERE job_name = %s"
        cursor.execute(sql, (job_name,))
        result = cursor.fetchone()
        
        if result:
            # Parse JSON fields
            if result.get('report_types'):
                result['report_types'] = json.loads(result['report_types'])
            if result.get('report_categories'):
                result['report_categories'] = json.loads(result['report_categories'])
            
            # Set default for report_limit if column doesn't exist
            if 'report_limit' not in result or result['report_limit'] is None:
                result['report_limit'] = 5
        
        return result
    except Exception as e:
        print(f"Error fetching scheduled job: {e}")
        return None


def get_all_scheduled_jobs(enabled_only: bool = False) -> List[Dict]:
    """
    Get all scheduled jobs.
    
    Args:
        enabled_only: If True, return only enabled jobs
    
    Returns:
        List[Dict]: List of job records with parsed JSON fields
    """
    try:
        sql = "SELECT * FROM scheduled_jobs"
        if enabled_only:
            sql += " WHERE enabled = TRUE"
        sql += " ORDER BY job_name"
        
        results = execute_query(sql, fetch_all=True)
        
        # Parse JSON fields
        if results:
            for result in results:
                if result.get('report_types'):
                    result['report_types'] = json.loads(result['report_types'])
                if result.get('report_categories'):
                    result['report_categories'] = json.loads(result['report_categories'])
                # Set default for report_limit if missing
                if 'report_limit' not in result or result['report_limit'] is None:
                    result['report_limit'] = 5
        
        return results if results else []
    except Exception as e:
        print(f"Error fetching scheduled jobs: {e}")
        return []


def update_job_run_stats(job_name: str, next_run: datetime = None):
    """
    Update job statistics after execution.
    
    Args:
        job_name: Job identifier
        next_run: Next scheduled run time
    """
    try:
        connection = get_connection()
        cursor = get_cursor()
        sql = """
            UPDATE scheduled_jobs
            SET 
                last_run = NOW(),
                next_run = %s,
                run_count = run_count + 1,
                updated_at = NOW()
            WHERE job_name = %s
        """
        cursor.execute(sql, (next_run, job_name))
        connection.commit()
    except Exception as e:
        connection = get_connection()
        if connection:
            connection.rollback()
        print(f"Error updating job stats: {e}")


def delete_scheduled_job(job_name: str):
    """
    Delete scheduled job.
    
    Args:
        job_name: Job identifier to delete
    """
    try:
        connection = get_connection()
        cursor = get_cursor()
        sql = "DELETE FROM scheduled_jobs WHERE job_name = %s"
        cursor.execute(sql, (job_name,))
        connection.commit()
    except Exception as e:
        connection = get_connection()
        if connection:
            connection.rollback()
        print(f"Error deleting scheduled job: {e}")


# ============================================================================
# JOB_EXECUTION_LOG TABLE - Execution Audit Trail
# ============================================================================

def insert_job_execution(
    job_name: str,
    status: str = 'running'
) -> Optional[int]:
    """
    Insert job execution log (start of execution).
    
    Args:
        job_name: Job identifier
        status: Initial status (default: 'running')
    
    Returns:
        int: Execution ID or None on error
    """
    try:
        connection = get_connection()
        cursor = get_cursor()
        sql = """
            INSERT INTO job_execution_log
            (job_name, status, started_at)
            VALUES (%s, %s, NOW())
        """
        cursor.execute(sql, (job_name, status))
        connection.commit()
        return cursor.lastrowid
    except Exception as e:
        connection = get_connection()
        if connection:
            connection.rollback()
        print(f"Error inserting job execution: {e}")
        return None


def update_job_execution(
    execution_id: int,
    status: str,
    reports_found: int = None,
    documents_processed: int = None,
    summary_report_id: int = None,
    error_message: str = None,
    log_file_path: str = None
):
    """
    Update job execution log (end of execution).
    
    Args:
        execution_id: Execution ID to update
        status: Final status ('completed', 'failed', etc.)
        reports_found: Number of reports found
        documents_processed: Number of documents processed
        summary_report_id: Foreign key to summary_reports table
        error_message: Error details if failed
        log_file_path: Path to detailed log file
    """
    try:
        connection = get_connection()
        cursor = get_cursor()
        sql = """
            UPDATE job_execution_log
            SET 
                status = %s,
                finished_at = NOW(),
                duration_seconds = TIMESTAMPDIFF(SECOND, started_at, NOW()),
                reports_found = %s,
                documents_processed = %s,
                summary_report_id = %s,
                error_message = %s,
                log_file_path = %s
            WHERE id = %s
        """
        cursor.execute(sql, (
            status, reports_found, documents_processed,
            summary_report_id, error_message, log_file_path,
            execution_id
        ))
        connection.commit()
    except Exception as e:
        connection = get_connection()
        if connection:
            connection.rollback()
        print(f"Error updating job execution: {e}")


def get_job_execution_logs(job_name: str = None, limit: int = 50) -> List[Dict]:
    """
    Get job execution logs.
    
    Args:
        job_name: Filter by job name (optional)
        limit: Maximum number of results
    
    Returns:
        List[Dict]: List of execution log records
    """
    try:
        sql = "SELECT * FROM job_execution_log WHERE 1=1"
        params = []
        
        if job_name:
            sql += " AND job_name = %s"
            params.append(job_name)
        
        sql += " ORDER BY started_at DESC LIMIT %s"
        params.append(limit)
        
        results = execute_query(sql, tuple(params), fetch_all=True)
        return results if results else []
    except Exception as e:
        print(f"Error fetching execution logs: {e}")
        return []


# ============================================================================
# DATABASE VIEWS - Quick Access Helpers
# ============================================================================

def get_active_jobs_view() -> List[Dict]:
    """
    Get active jobs from v_active_jobs view.
    
    Returns:
        List[Dict]: List of active job records with parsed JSON fields
    """
    try:
        sql = "SELECT * FROM v_active_jobs"
        results = execute_query(sql, fetch_all=True)
        
        # Parse JSON fields
        if results:
            for result in results:
                if result.get('report_types'):
                    result['report_types'] = json.loads(result['report_types'])
                if result.get('report_categories'):
                    result['report_categories'] = json.loads(result['report_categories'])
        
        return results if results else []
    except Exception as e:
        print(f"Error fetching active jobs view: {e}")
        return []
