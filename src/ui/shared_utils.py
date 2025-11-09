"""
Shared utilities for Gradio UI
Common functions used across multiple tabs.
"""

from datetime import datetime
from typing import Tuple, List
import pandas as pd
from ollama_manager import (
    get_available_models,
    get_installed_models,
    is_model_installed,
    pull_model,
    get_model_display_name,
)
from config_manager import ConfigManager, ScrapingConfig
from cron_manager import CronManager


def get_model_choices() -> List[str]:
    """
    Generate list of models with installation status markers.
    
    Returns:
        List of model names with ✓ (installed) or ○ (not installed) prefix
    """
    available = get_available_models()
    installed = get_installed_models()
    choices = []
    for model in available:
        is_installed_flag = model in installed
        choices.append(get_model_display_name(model, is_installed_flag))
    return choices


def format_date_from_input(date_input) -> str:
    """
    Convert various date input formats to DD-MM-YYYY string.
    Handles: timestamp (float/int), ISO string, datetime object, existing DD-MM-YYYY.
    
    Args:
        date_input: Date from Gradio (can be float timestamp, string, datetime, or None)
    
    Returns:
        str: Date in DD-MM-YYYY format or empty string
    """
    if not date_input:
        return ""
    
    # Float/int timestamp from Gradio DateTime
    if isinstance(date_input, (int, float)):
        try:
            parsed = datetime.fromtimestamp(date_input)
            return parsed.strftime("%d-%m-%Y")
        except:
            return ""
    
    # String ISO format
    if isinstance(date_input, str):
        try:
            parsed = datetime.fromisoformat(date_input.replace('Z', '+00:00'))
            return parsed.strftime("%d-%m-%Y")
        except:
            # Maybe already DD-MM-YYYY format
            if '-' in date_input and len(date_input) == 10:
                return date_input
            return ""
    
    # Datetime object
    if hasattr(date_input, 'strftime'):
        return date_input.strftime("%d-%m-%Y")
    
    return ""


def schedule_to_cron(
    frequency: str,
    time_hour: int,
    time_minute: int,
    day_of_week: str = None,
    day_of_month: int = None
) -> str:
    """
    Convert simple schedule description to cron expression.
    
    Args:
        frequency: 'Codziennie', 'Co tydzień', 'Co miesiąc', 'custom'
        time_hour: Hour (0-23)
        time_minute: Minute (0-59)
        day_of_week: 'Poniedziałek', 'Wtorek', ... (for weekly)
        day_of_month: 1-31 (for monthly)
    
    Returns:
        str: Cron expression (format: minute hour day month weekday)
    """
    dow_mapping = {
        'Poniedziałek': '1',
        'Wtorek': '2',
        'Środa': '3',
        'Czwartek': '4',
        'Piątek': '5',
        'Sobota': '6',
        'Niedziela': '0'
    }
    
    if frequency == 'Codziennie':
        return f"{time_minute} {time_hour} * * *"
    elif frequency == 'Co tydzień':
        dow = dow_mapping.get(day_of_week, '1')
        return f"{time_minute} {time_hour} * * {dow}"
    elif frequency == 'Co miesiąc':
        dom = day_of_month if day_of_month else 1
        return f"{time_minute} {time_hour} {dom} * *"
    else:
        return f"{time_minute} {time_hour} * * *"


def cron_to_human_readable(cron_expr: str) -> str:
    """
    Convert cron expression to human-readable Polish description.
    
    Args:
        cron_expr: Cron expression (e.g., "0 9 * * 1")
    
    Returns:
        str: Human-readable description
    """
    parts = cron_expr.split()
    if len(parts) != 5:
        return cron_expr
    
    minute, hour, day, month, weekday = parts
    
    time_str = f"{hour}:{minute.zfill(2)}"
    
    if day == '*' and month == '*' and weekday == '*':
        return f"Codziennie o {time_str}"
    elif day == '*' and month == '*' and weekday != '*':
        dow_names = ['Niedziela', 'Poniedziałek', 'Wtorek', 'Środa', 'Czwartek', 'Piątek', 'Sobota']
        dow_name = dow_names[int(weekday)] if weekday.isdigit() and int(weekday) < 7 else f"dzień {weekday}"
        return f"Co tydzień w {dow_name} o {time_str}"
    elif day != '*' and month == '*' and weekday == '*':
        return f"Co miesiąc {day}. dnia o {time_str}"
    else:
        return cron_expr


def get_all_configs_as_text() -> str:
    """
    Get all saved configurations as formatted Markdown text.
    
    Returns:
        str: Markdown-formatted list of configurations
    """
    manager = ConfigManager()
    configs = manager.list_configs()
    
    if not configs:
        return "Brak zapisanych konfiguracji."
    
    text = "## 📋 Zapisane konfiguracje\n\n"
    for config in configs:
        status = "✓ Aktywna" if config.enabled else "✗ Wyłączona"
        text += f"### {config.job_name}\n"
        text += f"- **Status:** {status}\n"
        text += f"- **Firma:** {config.company}\n"
        text += f"- **Okres:** {config.date_from} - {config.date_to}\n"
        text += f"- **Model:** {config.model}\n"
        text += f"- **Harmonogram:** `{config.cron_schedule}`\n"
        text += f"- **Opis:** {config.description}\n\n"
        text += "---\n\n"
    
    return text


def get_installed_jobs_as_text() -> str:
    """
    Get list of installed cron jobs as text.
    
    Returns:
        str: Markdown-formatted list of cron jobs
    """
    cron_mgr = CronManager()
    jobs = cron_mgr.get_installed_jobs()
    
    if not jobs:
        return "ℹ️ Brak zainstalowanych zadań w crontab."
    
    text = f"## 📅 Zainstalowane zadania ({len(jobs)})\n\n"
    text += "```\n"
    for job in jobs:
        text += f"{job}\n"
    text += "```\n"
    
    return text


def validate_cron_expression_ui(cron_expr: str) -> str:
    """
    Validate cron expression and return user-friendly message.
    
    Args:
        cron_expr: Cron expression to validate
    
    Returns:
        str: Validation result message
    """
    cron_mgr = CronManager()
    valid, message = cron_mgr.validate_cron_expression(cron_expr)
    
    return message


def get_job_names() -> List[str]:
    """
    Get list of all configured job names.
    
    Returns:
        List of job names from ConfigManager
    """
    config_mgr = ConfigManager()
    configs = config_mgr.list_configs()
    return [c.job_name for c in configs] if configs else []
