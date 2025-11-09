"""
Company Repository
CRUD operations for companies table.
"""

from typing import Optional, List, Dict
from ..connection import get_connection, get_cursor, ensure_connection


def insert_company(name: str, full_name: str = None, sector: str = None) -> Optional[int]:
    """
    Insert or get company ID (idempotent operation).
    
    Args:
        name: Company short name (ticker symbol)
        full_name: Full company name (optional)
        sector: Business sector (optional)
    
    Returns:
        int: Company ID or None on error
    """
    ensure_connection()
    try:
        connection = get_connection()
        cursor = get_cursor()
        
        # Check if company exists
        company_id = get_company_id(name)
        if company_id:
            return company_id
        
        sql = """
            INSERT INTO companies (name, full_name, sector)
            VALUES (%s, %s, %s)
        """
        cursor.execute(sql, (name, full_name, sector))
        connection.commit()
        return cursor.lastrowid
    except Exception as e:
        connection = get_connection()
        if connection:
            connection.rollback()
        print(f"Error inserting company: {e}")
        return None


def get_company_id(name: str) -> Optional[int]:
    """
    Get company ID by name (case-insensitive LIKE match).
    
    Args:
        name: Company name to search for
    
    Returns:
        int: Company ID or None if not found
    """
    ensure_connection()
    try:
        cursor = get_cursor()
        sql = "SELECT id FROM companies WHERE name LIKE %s"
        cursor.execute(sql, (name,))
        result = cursor.fetchone()
        return result['id'] if result else None
    except Exception as e:
        print(f"Error getting company ID: {e}")
        return None


def get_all_companies() -> List[Dict]:
    """
    Get all companies from database.
    
    Returns:
        List[Dict]: List of company records (id, name, full_name, sector)
    """
    ensure_connection()
    try:
        cursor = get_cursor()
        sql = "SELECT * FROM companies ORDER BY name"
        cursor.execute(sql)
        return cursor.fetchall()
    except Exception as e:
        print(f"Error fetching companies: {e}")
        return []
