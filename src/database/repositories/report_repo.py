"""
Report Repository
CRUD operations for reports table (GPW financial reports).
"""

from typing import Optional, List, Dict
from datetime import datetime
from ..connection import get_connection, get_cursor, ensure_connection


def insert_report(
    company_id: int,
    date: str,
    title: str,
    report_type: str,
    report_category: str,
    rate_change: float = None,
    exchange_rate: float = None,
    link: str = None
) -> Optional[int]:
    """
    Insert GPW report into database.
    
    Args:
        company_id: Foreign key to companies table
        date: Report date (DD-MM-YYYY or YYYY-MM-DD format)
        title: Report title
        report_type: Type of report (e.g., RB, ESPI)
        report_category: Category/subject
        rate_change: Rate change percentage (optional)
        exchange_rate: Exchange rate value (optional)
        link: URL to original report (optional)
    
    Returns:
        int: Report ID or None on error
    """
    try:
        connection = get_connection()
        cursor = get_cursor()
        
        # Convert date format: if contains time (space), extract only date part
        if date and " " in date:
            date = date.split()[0]
        
        # Convert DD-MM-YYYY → YYYY-MM-DD for MySQL
        if date:
            try:
                date_obj = datetime.strptime(date, "%d-%m-%Y")
                date = date_obj.strftime("%Y-%m-%d")
            except ValueError:
                # If parsing fails, keep original format
                pass
        
        sql = """
            INSERT INTO reports 
            (company_id, date, title, report_type, report_category, 
             rate_change, exchange_rate, link)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (
            company_id, date, title, report_type, report_category,
            rate_change, exchange_rate, link
        ))
        connection.commit()
        return cursor.lastrowid
    except Exception as e:
        connection = get_connection()
        if connection:
            connection.rollback()
        print(f"Error inserting report: {e}")
        return None


def get_reports(
    company_id: int = None,
    date_from: str = None,
    date_to: str = None,
    report_type: str = None,
    limit: int = 100
) -> List[Dict]:
    """
    Get reports with optional filters.
    
    Args:
        company_id: Filter by company ID
        date_from: Start date (YYYY-MM-DD)
        date_to: End date (YYYY-MM-DD)
        report_type: Filter by report type
        limit: Maximum number of results
    
    Returns:
        List[Dict]: List of report records
    """
    try:
        cursor = get_cursor()
        sql = "SELECT * FROM reports WHERE 1=1"
        params = []
        
        if company_id:
            sql += " AND company_id = %s"
            params.append(company_id)
        
        if date_from:
            sql += " AND date >= %s"
            params.append(date_from)
        
        if date_to:
            sql += " AND date <= %s"
            params.append(date_to)
        
        if report_type:
            sql += " AND report_type = %s"
            params.append(report_type)
        
        sql += " ORDER BY date DESC LIMIT %s"
        params.append(limit)
        
        cursor.execute(sql, params)
        return cursor.fetchall()
    except Exception as e:
        print(f"Error fetching reports: {e}")
        return []
