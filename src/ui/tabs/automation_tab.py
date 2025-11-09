"""
Automation Tab - Job scheduling and management
"""

import gradio as gr
import os
import subprocess
import sys
from datetime import datetime
from config_manager import ConfigManager, ScrapingConfig
from cron_manager import CronManager
from database_connection import get_job_execution_logs
from pathlib import Path
from ..shared_utils import (
    schedule_to_cron,
    cron_to_human_readable,
    get_all_configs_as_text,
    get_installed_jobs_as_text,
    format_date_from_input,
    get_job_names,
)


def create_new_config_advanced(
    job_name, company, date_from, date_to, model, cron_schedule,
    description, enabled, report_limit=100, report_types=None, report_categories=None
):
    """
    Create new configuration with advanced options.
    
    NOTE: date_from and date_to are stored for compatibility but unused.
    All available reports are fetched (no date range limit).
    report_limit determines maximum search results.
    """
    try:
        config = ScrapingConfig(
            job_name=job_name,
            company=company,
            date_from=format_date_from_input(date_from),
            date_to=format_date_from_input(date_to),
            model=model,
            cron_schedule=cron_schedule,
            enabled=enabled,
            report_limit=report_limit,
            description=description,
            report_types=report_types if report_types else None,
            report_categories=report_categories if report_categories else None
        )
        
        manager = ConfigManager()
        manager.save_config(config)
        
        return (
            f"✅ Konfiguracja '{job_name}' została zapisana!",
            get_all_configs_as_text()
        )
    except Exception as e:
        return (f"❌ Błąd: {e}", get_all_configs_as_text())


def run_job_now(job_name):
    """Manually run a job without waiting for cron schedule."""
    if not job_name or job_name.strip() == "":
        return "❌ Wybierz zadanie do uruchomienia"

    try:
        # Run run_scheduled.py in background
        python_exe = sys.executable
        # Navigate from src/ui/tabs/automation_tab.py -> root (4x dirname)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        script_path = os.path.join(project_root, "run_scheduled.py")
        
        result = subprocess.run(
            [python_exe, script_path, job_name],
            capture_output=True,
            text=True,
            timeout=600,  # 10 min timeout for long-running jobs
            cwd=project_root  # Ensure working directory is project root
        )
        
        output = f"▶️ Uruchomiono zadanie '{job_name}'\n\n"
        output += "📝 **Output:**\n```\n"
        output += result.stdout if result.stdout else "(brak output)"
        output += "\n```\n"
        
        if result.stderr:
            output += "\n⚠️ **Errors:**\n```\n"
            output += result.stderr
            output += "\n```\n"
        
        if result.returncode == 0:
            output += "\n✅ **Status:** Zakończone pomyślnie"
        else:
            output += f"\n❌ **Status:** Błąd (kod {result.returncode})"
        
        return output
        
    except subprocess.TimeoutExpired:
        return f"⏱️ Przekroczono limit czasu (5 min) dla zadania '{job_name}'"
    except Exception as e:
        return f"❌ Błąd uruchamiania: {e}"


def get_execution_history(job_filter=None, limit=20):
    """
    Fetch job execution history from database.
    
    Returns:
        List of lists for Gradio DataFrame: [job_name, status, started_at, duration, reports_found, results, error_msg]
    """
    try:
        logs = get_job_execution_logs(job_name=job_filter if job_filter else None, limit=limit)
        
        rows = []
        for log in logs:
            # Status icon
            status_icon = {
                'success': '✅ Sukces',
                'failed': '❌ Błąd',
                'running': '⏳ W trakcie',
                'no_reports': 'ℹ️ Brak raportów'
            }.get(log.get('status', 'unknown'), '❓ Nieznany')
            
            # Duration calculation
            started = log.get('started_at')
            finished = log.get('finished_at')
            duration = "N/A"
            if started and finished:
                duration_sec = (finished - started).total_seconds()
                if duration_sec < 60:
                    duration = f"{duration_sec:.1f}s"
                else:
                    duration = f"{duration_sec/60:.1f}min"
            
            # Error message (truncate if too long)
            error_msg = log.get('error_message', '')
            if error_msg and len(error_msg) > 100:
                error_msg = error_msg[:97] + "..."
            
            # Result file info
            log_file = log.get('log_file_path', '')
            results_info = "-"
            if log_file and Path(log_file).exists():
                docs = log.get('documents_processed', 0)
                results_info = f"📄 {docs} doc" if docs > 0 else "📂 Log"
            
            rows.append([
                log.get('job_name', 'N/A'),
                status_icon,
                started.strftime('%Y-%m-%d %H:%M:%S') if started else 'N/A',
                duration,
                log.get('reports_found', 0),
                results_info,
                error_msg or '-'
            ])
        
        return rows if rows else [["Brak historii wykonań", "-", "-", "-", "-", "-", "-"]]
        
    except Exception as e:
        return [[f"Błąd: {e}", "-", "-", "-", "-", "-", "-"]]


def delete_config_ui(job_name):
    """Delete configuration."""
    manager = ConfigManager()
    
    if manager.delete_config(job_name):
        return (f"✅ Usunięto konfigurację '{job_name}'", get_all_configs_as_text())
    else:
        return (f"❌ Nie znaleziono konfiguracji '{job_name}'", get_all_configs_as_text())


def install_cron_jobs():
    """Install jobs to crontab."""
    cron_mgr = CronManager()
    success, message = cron_mgr.install_jobs()
    
    return (message, get_installed_jobs_as_text())


def uninstall_cron_jobs():
    """Remove jobs from crontab."""
    cron_mgr = CronManager()
    success, message = cron_mgr.uninstall_jobs()
    
    return (message, get_installed_jobs_as_text())


def create_automation_tab():
    """Create the Automation tab UI."""
    with gr.Tab("⏰ Automatyzacja"):
        gr.Markdown("## 🤖 Automatyczne raporty - Proste i intuicyjne")
        
        # Section 1: Create new job
        with gr.Accordion("➕ Utwórz nowe zadanie", open=True):
            gr.Markdown("### Szybka konfiguracja zadania")
            
            with gr.Row():
                with gr.Column(scale=2):
                    auto_job_name = gr.Textbox(
                        label="📝 Nazwa zadania",
                        placeholder="np. PKO_codzienny",
                        info="Bez spacji (użyj _ zamiast)"
                    )
                    auto_company = gr.Textbox(label="🏢 Firma", placeholder="np. PKO")
                    
                    auto_report_limit = gr.Slider(
                        label="📝 Ile raportów pobrać?",
                        minimum=1,
                        maximum=100,
                        value=5,
                        step=1,
                        info="Limit wyników wyszukiwania"
                    )
                    
                    auto_model = gr.Dropdown(
                        label="🤖 Model AI",
                        choices=["llama3.2:latest", "gemma:7b", "qwen2.5:7b"],
                        value="llama3.2:latest"
                    )
                
                with gr.Column(scale=1):
                    gr.Markdown("### ⏰ Harmonogram")
                    auto_frequency = gr.Dropdown(
                        label="Częstotliwość",
                        choices=["Codziennie", "Co tydzień", "Co miesiąc"],
                        value="Codziennie"
                    )
                    
                    with gr.Row():
                        auto_hour = gr.Slider(label="Godzina", minimum=0, maximum=23, value=9, step=1)
                        auto_minute = gr.Slider(label="Minuta", minimum=0, maximum=59, value=0, step=5)
                    
                    auto_day_of_week = gr.Dropdown(
                        label="Dzień tygodnia",
                        choices=["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"],
                        value="Poniedziałek",
                        visible=False
                    )
                    
                    auto_day_of_month = gr.Slider(
                        label="Dzień miesiąca",
                        minimum=1, maximum=31, value=1, step=1, visible=False
                    )
                    
                    auto_schedule_preview = gr.Markdown("**⏰ Codziennie o 09:00**")
                    
                    def update_preview(freq, hour, minute, dow, dom):
                        time_str = f"{int(hour):02d}:{int(minute):02d}"
                        if freq == "Codziennie":
                            return f"**⏰ Codziennie o {time_str}**"
                        elif freq == "Co tydzień":
                            return f"**⏰ Co tydzień w {dow} o {time_str}**"
                        else:
                            return f"**⏰ Co miesiąc {int(dom)}. dnia o {time_str}**"
                    
                    def toggle_fields(freq):
                        if freq == "Co tydzień":
                            return gr.update(visible=True), gr.update(visible=False)
                        elif freq == "Co miesiąc":
                            return gr.update(visible=False), gr.update(visible=True)
                        return gr.update(visible=False), gr.update(visible=False)
                    
                    auto_frequency.change(fn=toggle_fields, inputs=[auto_frequency], outputs=[auto_day_of_week, auto_day_of_month])
                    
                    for comp in [auto_frequency, auto_hour, auto_minute, auto_day_of_week, auto_day_of_month]:
                        comp.change(fn=update_preview, inputs=[auto_frequency, auto_hour, auto_minute, auto_day_of_week, auto_day_of_month], outputs=[auto_schedule_preview])
            
            gr.Markdown("---")
            gr.Markdown("### ⚙️ Opcje zaawansowane (opcjonalne)")
            
            with gr.Accordion("🔧 Szczegóły scrapingu", open=False):
                with gr.Row():
                    auto_report_types = gr.CheckboxGroup(
                        label="📑 Typy raportów",
                        choices=["current", "quarterly", "semi-annual", "annual", "interim"],
                        value=["current", "quarterly", "semi-annual", "annual"],
                        info="Wybierz, które typy raportów pobrać"
                    )
                    
                    auto_report_categories = gr.CheckboxGroup(
                        label="📂 Kategorie",
                        choices=["ESPI", "EBI"],
                        value=["ESPI", "EBI"],
                        info="ESPI = raporty giełdowe, EBI = raporty bankowe"
                    )
            
            create_job_btn = gr.Button("✨ Utwórz zadanie", variant="primary", size="lg")
            create_job_output = gr.Textbox(label="Status")
            
            def create_job_simple(job_name, company, report_limit, model, freq, h, m, dow, dom, rep_types, rep_cats):
                cron = schedule_to_cron(freq, int(h), int(m), dow, int(dom))
                # Use advanced options if provided
                report_types = rep_types if rep_types else None
                report_categories = rep_cats if rep_cats else None
                # Use today's date for compatibility, report_limit is the key param
                today_str = datetime.now().strftime("%d-%m-%Y")
                return create_new_config_advanced(job_name, company, today_str, today_str, model, cron, f"{freq} - {company}", True, int(report_limit), report_types, report_categories)[0]
            
            create_job_btn.click(
                fn=create_job_simple,
                inputs=[auto_job_name, auto_company, auto_report_limit, auto_model, auto_frequency, auto_hour, auto_minute, auto_day_of_week, auto_day_of_month, auto_report_types, auto_report_categories],
                outputs=[create_job_output]
            )
        
        gr.Markdown("---")
        
        # Section 2: Manage jobs
        with gr.Accordion("📋 Moje zadania", open=True):
            refresh_btn = gr.Button("🔄 Odśwież", variant="secondary")
            
            jobs_table = gr.Dataframe(
                headers=["Nazwa", "Firma", "Model", "Harmonogram", "Status"],
                interactive=False
            )
            
            def get_jobs_table():
                from config_manager import ConfigManager
                from cron_manager import CronManager
                
                mgr = ConfigManager()
                cron_mgr = CronManager()
                configs = mgr.list_configs()
                
                installed = set()
                for line in cron_mgr.get_installed_jobs():
                    if "run_scheduled.py" in line:
                        name = line.split("run_scheduled.py")[1].split()[0].strip() if len(line.split("run_scheduled.py")) > 1 else ""
                        if name:
                            installed.add(name)
                
                rows = []
                for cfg in configs:
                    status = "✅ Aktywne" if cfg.enabled else "⏸️ Wyłączone"
                    if cfg.enabled and cfg.job_name not in installed:
                        status += " (brak w cron)"
                    
                    rows.append([
                        cfg.job_name,
                        cfg.company,
                        cfg.model,
                        cron_to_human_readable(cfg.cron_schedule),
                        status
                    ])
                
                return rows if rows else [["Brak zadań", "-", "-", "-", "-"]]
            
            refresh_btn.click(fn=get_jobs_table, outputs=[jobs_table])
            
            gr.Markdown("### ⚡ Akcje")
            
            # Load job names for dropdown initialization
            initial_job_names = get_job_names()
            
            with gr.Row():
                with gr.Column(scale=2):
                    gr.Markdown("**▶️ Uruchom teraz**")
                    run_select = gr.Dropdown(
                        label="Wybierz zadanie", 
                        choices=initial_job_names,
                        interactive=True,
                        scale=1
                    )
                    run_btn = gr.Button("▶️ Uruchom", variant="primary")
                    run_output = gr.Textbox(label="Log", lines=10)
                
                with gr.Column(scale=2):
                    gr.Markdown("**🗑️ Usuń zadanie**")
                    del_select = gr.Dropdown(
                        label="Wybierz zadanie", 
                        choices=initial_job_names,
                        interactive=True,
                        scale=1
                    )
                    del_btn = gr.Button("🗑️ Usuń", variant="stop")
                    del_output = gr.Textbox(label="Status")
            
            # Refresh button for names
            refresh_names_btn = gr.Button("🔄 Odśwież listę zadań", size="sm")
            
            def get_names():
                names = get_job_names()
                return gr.update(choices=names), gr.update(choices=names)
            
            # Setup callbacks to refresh dropdowns
            refresh_names_btn.click(fn=get_names, outputs=[run_select, del_select])
            refresh_btn.click(fn=get_names, outputs=[run_select, del_select])
            
            run_btn.click(fn=run_job_now, inputs=[run_select], outputs=[run_output])
            del_btn.click(fn=delete_config_ui, inputs=[del_select], outputs=[del_output])
        
        gr.Markdown("---")
        
        # Section 3: System installation
        with gr.Accordion("🔧 Instalacja w systemie cron", open=False):
            gr.Markdown("**Zainstaluj w crontab** aby zadania uruchamiały się automatycznie")
            
            with gr.Row():
                install_btn = gr.Button("✅ Zainstaluj", variant="primary")
                uninstall_btn = gr.Button("🗑️ Odinstaluj", variant="stop")
            
            cron_status = gr.Textbox(label="Status", lines=3)
            
            install_btn.click(fn=install_cron_jobs, outputs=[cron_status])
            uninstall_btn.click(fn=uninstall_cron_jobs, outputs=[cron_status])
            
            refresh_cron_btn = gr.Button("🔄 Pokaż zainstalowane")
            cron_display = gr.Markdown(value=get_installed_jobs_as_text())
            refresh_cron_btn.click(fn=get_installed_jobs_as_text, outputs=[cron_display])
        
        gr.Markdown("---")
        
        # Section 4: Execution history
        with gr.Accordion("📊 Historia wykonań", open=True):
            gr.Markdown("### 📜 Ostatnie uruchomienia")
            
            with gr.Row():
                hist_filter = gr.Dropdown(
                    label="Filtruj",
                    choices=["Wszystkie"],
                    value="Wszystkie"
                )
                hist_refresh = gr.Button("🔄 Odśwież")
            
            hist_table = gr.Dataframe(
                headers=["Zadanie", "Status", "Start", "Czas", "Raporty", "Wyniki", "Błąd"],
                interactive=False
            )
            
            def refresh_hist(flt):
                return get_execution_history(None if flt == "Wszystkie" else flt, 30)
            
            hist_refresh.click(fn=refresh_hist, inputs=[hist_filter], outputs=[hist_table])
            
            def update_filter():
                from config_manager import ConfigManager
                names = [c.job_name for c in ConfigManager().list_configs()]
                return gr.update(choices=["Wszystkie"] + names)
            
            refresh_btn.click(fn=update_filter, outputs=[hist_filter])
        
        return {
            'jobs_table': jobs_table,
            'refresh_btn': refresh_btn,
            'hist_table': hist_table,
        }
