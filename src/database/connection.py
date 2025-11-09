"""
Database Connection Module
Thread-safe connection management for MySQL/MariaDB with thread-local storage.
Supports automatic reconnect on connection failures.
"""

import os
import pymysql
import threading
from typing import Optional, Tuple
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database connection settings from environment variables
HOST = os.getenv("DB_HOST", "localhost")
USER = os.getenv("DB_USER", "user")
PASSWORD = os.getenv("DB_PASSWORD", "qwerty123")
DATABASE = os.getenv("DB_NAME", "gpw data")

# Thread-local storage for connections
_thread_local = threading.local()


def get_connection():
    """
    Get thread-local database connection.
    Creates new connection if none exists for current thread.
    
    Returns:
        pymysql.Connection: Database connection for current thread
    """
    if not hasattr(_thread_local, 'connection') or _thread_local.connection is None:
        try:
            _thread_local.connection = pymysql.connect(
                host=HOST,
                user=USER,
                password=PASSWORD,
                database=DATABASE,
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=False,
                connect_timeout=10,
                read_timeout=30,
                write_timeout=30,
                charset='utf8mb4'
            )
        except Exception as e:
            print(f"Database connection error: {e}")
            _thread_local.connection = None
    return _thread_local.connection


def get_cursor():
    """
    Get cursor for current thread's connection.
    
    Returns:
        pymysql.cursors.DictCursor: Cursor object or None if connection failed
    """
    conn = get_connection()
    if conn is None:
        return None
    if not hasattr(_thread_local, 'cursor') or _thread_local.cursor is None:
        _thread_local.cursor = conn.cursor()
    return _thread_local.cursor


def connect() -> bool:
    """
    Establish database connection for current thread.
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        conn = get_connection()
        if conn:
            get_cursor()
            return True
        return False
    except Exception as e:
        print(f"Database connection error: {e}")
        return False


def ensure_connection() -> bool:
    """
    Ensure database connection is alive, reconnect if needed.
    Uses ping() to verify connection health with automatic reconnect.
    
    Returns:
        bool: True if connection is active, False if all retries failed
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            conn = get_connection()
            if conn is None:
                if connect():
                    return True
            else:
                # Test connection with ping (automatic reconnect if needed)
                conn.ping(reconnect=True)
                return True
        except Exception as e:
            # Connection failed, force reconnect
            try:
                conn = get_connection()
                if conn:
                    conn.close()
            except:
                pass
            _thread_local.connection = None
            _thread_local.cursor = None
            
            if attempt < max_retries - 1:
                # Try again
                continue
            else:
                # Final attempt
                return connect()
    
    return False


def execute_query(sql: str, params: tuple = None, fetch_one: bool = False, fetch_all: bool = False):
    """
    Execute SQL query with automatic reconnect on packet sequence error.
    Thread-safe implementation using thread-local connections.
    
    Args:
        sql: SQL query string
        params: Query parameters tuple
        fetch_one: Return single row as dict
        fetch_all: Return all rows as list of dicts
    
    Returns:
        - None if INSERT/UPDATE/DELETE
        - Single dict if fetch_one=True
        - List of dicts if fetch_all=True
        - lastrowid for INSERT operations
    
    Raises:
        Exception: Database errors after retry attempts
    """
    max_retries = 2
    
    for attempt in range(max_retries):
        try:
            if not ensure_connection():
                raise Exception("Could not establish database connection")
            
            conn = get_connection()
            cursor = get_cursor()
            
            if conn is None or cursor is None:
                raise Exception("Database connection or cursor is not initialized")
            
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            
            if fetch_one:
                return cursor.fetchone()
            elif fetch_all:
                return cursor.fetchall()
            else:
                conn.commit()
                return cursor.lastrowid
                
        except Exception as e:
            error_msg = str(e).lower()
            
            # Check for packet sequence or connection errors
            if "packet sequence" in error_msg or "connection" in error_msg or "lost" in error_msg or "protocol" in error_msg:
                try:
                    conn = get_connection()
                    if conn:
                        conn.close()
                except:
                    pass
                _thread_local.connection = None
                _thread_local.cursor = None
                
                if attempt < max_retries - 1:
                    # Try to reconnect and retry
                    if connect():
                        continue
            
            # If we get here, it's a real error
            try:
                conn = get_connection()
                if conn:
                    conn.rollback()
            except:
                pass
            raise


def close_connection():
    """Close database connection for current thread"""
    try:
        cursor = get_cursor()
        if cursor:
            cursor.close()
    except:
        pass
    
    try:
        conn = get_connection()
        if conn:
            conn.close()
    except:
        pass
    
    _thread_local.connection = None
    _thread_local.cursor = None


# Backward compatibility - expose connection and cursor as module-level references
def _update_globals():
    """Update module globals for backward compatibility (not recommended for new code)"""
    import sys
    current_module = sys.modules[__name__]
    current_module.connection = get_connection()
    current_module.cursor = get_cursor()
    return current_module.connection, current_module.cursor
