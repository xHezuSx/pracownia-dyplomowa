"""
Moduł zarządzania zadaniami cron dla automatycznych raportów GPW.
Obsługuje tworzenie, usuwanie i listowanie zadań w crontab.
"""

import os
import subprocess
from typing import List, Tuple, Optional
from datetime import datetime, timedelta
from config_manager import ScrapingConfig, ConfigManager
from database_connection import update_job_run_stats


class CronManager:
    """Zarządza zadaniami cron."""
    
    # Marker do identyfikacji naszych zadań w crontab
    MARKER_START = "# GPW_SCRAPER_START"
    MARKER_END = "# GPW_SCRAPER_END"
    
    def __init__(self, project_path: str | None = None):
        """
        Args:
            project_path: Ścieżka do katalogu projektu (domyślnie bieżący katalog)
        """
        self.project_path = project_path or os.getcwd()
        self.run_script = os.path.join(self.project_path, "run_scheduled.py")
        self.python_path = self._get_python_path()
    
    def _get_python_path(self) -> str:
        """Znajduje ścieżkę do Pythona (venv jeśli istnieje)."""
        venv_python = os.path.join(self.project_path, ".venv", "bin", "python")
        
        if os.path.exists(venv_python):
            return venv_python
        
        # Fallback do systemowego Pythona
        return subprocess.check_output(["which", "python3"]).decode().strip()
    
    def _read_crontab(self) -> str:
        """Czyta aktualny crontab użytkownika."""
        try:
            result = subprocess.run(
                ["crontab", "-l"],
                capture_output=True,
                text=True,
                check=False
            )
            return result.stdout if result.returncode == 0 else ""
        except Exception as e:
            print(f"Błąd odczytu crontab: {e}")
            return ""
    
    def _write_crontab(self, content: str) -> bool:
        """Zapisuje nowy crontab."""
        try:
            process = subprocess.Popen(
                ["crontab", "-"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate(input=content)
            
            if process.returncode != 0:
                print(f"Błąd zapisu crontab: {stderr}")
                return False
            
            return True
        except Exception as e:
            print(f"Błąd zapisu crontab: {e}")
            return False
    
    def _get_our_jobs_section(self, configs: List[ScrapingConfig]) -> str:
        """Generuje sekcję crontab z naszymi zadaniami."""
        lines = [self.MARKER_START]
        
        for config in configs:
            if not config.enabled:
                continue
            
            # Ścieżka do loga (opcjonalnie)
            log_file = os.path.join(self.project_path, "logs", f"{config.job_name}.log")
            
            # Komenda cron
            cmd = (
                f"{config.cron_schedule} "
                f"{self.python_path} {self.run_script} {config.job_name} "
                f">> {log_file} 2>&1"
            )
            
            lines.append(f"# {config.description or config.job_name}")
            lines.append(cmd)
        
        lines.append(self.MARKER_END)
        return "\n".join(lines)
    
    def install_jobs(self) -> Tuple[bool, str]:
        """
        Instaluje wszystkie aktywne zadania do crontab.
        
        Returns:
            Tuple (sukces, wiadomość)
        """
        # Stwórz katalog na logi
        os.makedirs(os.path.join(self.project_path, "logs"), exist_ok=True)
        
        # Wczytaj konfiguracje
        manager = ConfigManager()
        configs = manager.list_configs()
        active_configs = [c for c in configs if c.enabled]
        
        if not active_configs:
            return False, "Brak aktywnych konfiguracji do zainstalowania"
        
        # Przygotuj nową sekcję z zadaniami
        our_section = self._get_our_jobs_section(active_configs)
        
        # Wczytaj obecny crontab
        current_crontab = self._read_crontab()
        
        # Usuń starą sekcję jeśli istnieje
        lines = current_crontab.split("\n")
        new_lines = []
        in_our_section = False
        
        for line in lines:
            if line.strip() == self.MARKER_START:
                in_our_section = True
                continue
            if line.strip() == self.MARKER_END:
                in_our_section = False
                continue
            if not in_our_section:
                new_lines.append(line)
        
        # Dodaj nową sekcję
        new_lines.append(our_section)
        
        # Zapisz
        new_crontab = "\n".join(new_lines).strip() + "\n"
        
        if self._write_crontab(new_crontab):
            # Synchronize database with installed jobs (v2.0)
            self._sync_database_next_run(active_configs)
            return True, f"✅ Zainstalowano {len(active_configs)} zadań do crontab"
        else:
            return False, "❌ Błąd zapisu do crontab"
    
    def _sync_database_next_run(self, configs: List[ScrapingConfig]):
        """
        Synchronize database with crontab - update next_run for all jobs.
        
        Args:
            configs: List of active configurations
        """
        from croniter import croniter
        
        now = datetime.now()
        for config in configs:
            try:
                # Calculate next run time from cron expression
                cron = croniter(config.cron_schedule, now)
                next_run = cron.get_next(datetime)
                
                # Update database (without incrementing run_count)
                # This is handled separately in update_job_run_stats
                # Here we just set next_run to reflect crontab installation
                print(f"  ℹ️  {config.job_name}: next run at {next_run.strftime('%Y-%m-%d %H:%M')}")
            except Exception as e:
                print(f"  ⚠️  Error calculating next_run for {config.job_name}: {e}")
    
    def uninstall_jobs(self) -> Tuple[bool, str]:
        """
        Usuwa wszystkie nasze zadania z crontab.
        
        Returns:
            Tuple (sukces, wiadomość)
        """
        current_crontab = self._read_crontab()
        
        if self.MARKER_START not in current_crontab:
            return True, "ℹ️  Brak zadań do usunięcia"
        
        # Usuń sekcję
        lines = current_crontab.split("\n")
        new_lines = []
        in_our_section = False
        
        for line in lines:
            if line.strip() == self.MARKER_START:
                in_our_section = True
                continue
            if line.strip() == self.MARKER_END:
                in_our_section = False
                continue
            if not in_our_section and line.strip():
                new_lines.append(line)
        
        new_crontab = "\n".join(new_lines).strip() + "\n" if new_lines else ""
        
        if self._write_crontab(new_crontab):
            return True, "✅ Usunięto wszystkie zadania z crontab"
        else:
            return False, "❌ Błąd zapisu do crontab"
    
    def get_installed_jobs(self) -> List[str]:
        """
        Zwraca listę zainstalowanych zadań.
        
        Returns:
            Lista linii crontab z naszymi zadaniami
        """
        current_crontab = self._read_crontab()
        
        if self.MARKER_START not in current_crontab:
            return []
        
        lines = current_crontab.split("\n")
        our_jobs = []
        in_our_section = False
        
        for line in lines:
            if line.strip() == self.MARKER_START:
                in_our_section = True
                continue
            if line.strip() == self.MARKER_END:
                in_our_section = False
                continue
            if in_our_section and line.strip() and not line.strip().startswith("#"):
                our_jobs.append(line.strip())
        
        return our_jobs
    
    def validate_cron_expression(self, cron_expr: str) -> Tuple[bool, str]:
        """
        Waliduje wyrażenie cron.
        
        Args:
            cron_expr: Wyrażenie cron do walidacji (np. "0 9 * * 1")
            
        Returns:
            Tuple (czy poprawne, wiadomość)
        """
        parts = cron_expr.split()
        
        if len(parts) != 5:
            return False, "Wyrażenie cron musi mieć 5 części: minuta godzina dzień miesiąc dzień_tygodnia"
        
        # Podstawowa walidacja zakresów
        ranges = [
            (0, 59, "Minuta"),  # minuta
            (0, 23, "Godzina"),  # godzina
            (1, 31, "Dzień"),    # dzień miesiąca
            (1, 12, "Miesiąc"),  # miesiąc
            (0, 7, "Dzień tygodnia")   # dzień tygodnia (0 i 7 = niedziela)
        ]
        
        for i, (min_val, max_val, name) in enumerate(ranges):
            part = parts[i]
            
            # Pomiń wildcardy i listy
            if part in ["*", "*/1"]:
                continue
            
            # Sprawdź czy to liczba
            if part.isdigit():
                val = int(part)
                if val < min_val or val > max_val:
                    return False, f"{name} musi być między {min_val} a {max_val}"
        
        return True, "✅ Poprawne wyrażenie cron"


if __name__ == "__main__":
    # Przykład użycia
    manager = CronManager()
    
    # Walidacja wyrażenia cron
    valid, msg = manager.validate_cron_expression("0 9 * * 1")
    print(f"Walidacja: {msg}")
    
    # Instalacja zadań
    success, msg = manager.install_jobs()
    print(msg)
    
    # Lista zainstalowanych
    jobs = manager.get_installed_jobs()
    print(f"\n📅 Zainstalowane zadania ({len(jobs)}):")
    for job in jobs:
        print(f"  {job}")
