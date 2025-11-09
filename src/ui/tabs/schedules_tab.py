"""
Schedules Tab - Active job schedules status
"""

import gradio as gr
from config_manager import ConfigManager
from database_connection import get_active_jobs_view
from cron_manager import CronManager


def get_active_jobs_status():
    """Fetch active jobs status from database."""
    config_mgr = ConfigManager()
    cron_mgr = CronManager()
    
    # Use database view for active jobs
    active_jobs = get_active_jobs_view()
    installed_jobs_lines = cron_mgr.get_installed_jobs()
    
    # Extract job names from crontab lines (format: ... run_scheduled.py NAME >> ...)
    installed_job_names = set()
    for line in installed_jobs_lines:
        if "run_scheduled.py" in line:
            parts = line.split("run_scheduled.py")
            if len(parts) > 1:
                name = parts[1].split()[0].strip()
                installed_job_names.add(name)
    
    rows = []
    for job in active_jobs:  # job is database row from v_active_jobs view
        job_name = job['job_name']
        status = "✅ Aktywny" if job['enabled'] and job_name in installed_job_names else "⏸️ Nieaktywny"
        
        # Get last run from database
        last_run = job['last_run'].strftime('%Y-%m-%d %H:%M:%S') if job.get('last_run') else "Nigdy"
        run_count = job.get('run_count', 0)
        
        rows.append([
            job_name,
            job['company'],
            job['model'],
            job['cron_schedule'],
            status,
            last_run,
            run_count
        ])
    
    return rows


def create_schedules_tab():
    """Create the Schedules tab UI."""
    with gr.Tab("📊 Aktywne Harmonogramy"):
        gr.Markdown("### Status aktywnych zadań automatyzacji")
        
        refresh_active_btn = gr.Button("🔄 Odśwież status", variant="secondary")
        active_jobs_display = gr.Dataframe(
            headers=["Nazwa", "Firma", "Model", "Harmonogram", "Status", "Ostatnie uruchomienie", "Liczba uruchomień"],
            interactive=False
        )
        
        refresh_active_btn.click(
            fn=get_active_jobs_status,
            inputs=[],
            outputs=[active_jobs_display]
        )
        
        return {
            'active_jobs_display': active_jobs_display,
            'refresh_active_btn': refresh_active_btn,
        }
