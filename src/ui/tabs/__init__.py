"""
Gradio UI tabs package.
Each tab module creates its own interface section.
"""

from .scraping_tab import create_scraping_tab, run_scrape_ui, refresh_companies_dropdown
from .automation_tab import create_automation_tab
from .schedules_tab import create_schedules_tab
from .reports_tab import create_reports_tab
from .info_tab import create_info_tab

__all__ = [
    'create_scraping_tab',
    'create_automation_tab',
    'create_schedules_tab',
    'create_reports_tab',
    'create_info_tab',
    'run_scrape_ui',
    'refresh_companies_dropdown',
]
