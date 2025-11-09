"""
Configuration Manager v2.0 - Database-backed Storage
Manages scheduled job configurations using database instead of JSON files.
Provides backward compatibility with old config_manager.py interface.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

from database_connection import (
    insert_scheduled_job,
    get_scheduled_job,
    get_all_scheduled_jobs,
    delete_scheduled_job,
    update_job_run_stats
)


@dataclass
class ScrapingConfig:
    """Konfiguracja pojedynczego zadania scrapingu."""
    job_name: str  # Unikalna nazwa zadania
    company: str  # Nazwa firmy do monitorowania
    date_from: str  # Data początkowa (dd-mm-yyyy)
    date_to: str  # Data końcowa (dd-mm-yyyy)
    model: str  # Model Ollama do użycia
    cron_schedule: str  # Wyrażenie cron (np. "0 9 * * 1" = każdy poniedziałek o 9:00)
    enabled: bool = True  # Czy zadanie jest aktywne
    report_types: Optional[List[str]] = None  # Typy raportów (EBI, ESPI, itp.)
    report_categories: Optional[List[str]] = None  # Kategorie raportów
    email_notify: Optional[str] = None  # Email do powiadomień (opcjonalnie)
    description: str = ""  # Opis zadania
    
    # Database-specific fields (optional, populated when loading from DB)
    id: Optional[int] = None
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        """Konwertuje konfigurację do słownika."""
        data = asdict(self)
        # Filter out None values and database-only fields for clean export
        return {k: v for k, v in data.items() if v is not None}
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ScrapingConfig':
        """Tworzy konfigurację ze słownika."""
        # Filter only fields that exist in dataclass
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)
    
    @classmethod
    def from_db_row(cls, row: Dict) -> 'ScrapingConfig':
        """Create config from database row with field mapping."""
        return cls(
            id=row.get('id'),
            job_name=row.get('job_name'),
            company=row.get('company'),
            date_from=row.get('date_from'),
            date_to=row.get('date_to'),
            model=row.get('model'),
            cron_schedule=row.get('cron_schedule'),
            enabled=bool(row.get('enabled', True)),
            report_types=row.get('report_types'),  # Already parsed from JSON by db module
            report_categories=row.get('report_categories'),
            last_run=row.get('last_run'),
            next_run=row.get('next_run'),
            run_count=row.get('run_count', 0),
            created_at=row.get('created_at'),
            updated_at=row.get('updated_at')
        )


class ConfigManager:
    """
    Configuration Manager v2.0 - Database-backed.
    
    Fully compatible with old interface but uses database instead of JSON files.
    Migration path:
    - Old configs in /configs/*.json are still readable (via load_legacy_config)
    - New configs are saved to database
    - All list/get operations work from database
    """
    
    def __init__(self, config_dir: str = "configs"):
        """
        Args:
            config_dir: Legacy directory for backward compatibility (not actively used)
        """
        self.config_dir = config_dir  # Kept for backward compatibility
        # Database connection is already initialized in database_connection
    
    def save_config(self, config: ScrapingConfig) -> str:
        """
        Zapisuje konfigurację do bazy danych.
        
        Args:
            config: Konfiguracja do zapisania
            
        Returns:
            Job name (identifier in database)
        """
        insert_scheduled_job(
            job_name=config.job_name,
            company=config.company,
            date_from=config.date_from,
            date_to=config.date_to,
            model=config.model,
            cron_schedule=config.cron_schedule,
            enabled=config.enabled,
            report_types=config.report_types,
            report_categories=config.report_categories
        )
        
        return f"database:{config.job_name}"
    
    def load_config(self, job_name: str) -> Optional[ScrapingConfig]:
        """
        Ładuje konfigurację z bazy danych.
        
        Args:
            job_name: Nazwa zadania
            
        Returns:
            Obiekt konfiguracji lub None jeśli nie znaleziono
        """
        db_row = get_scheduled_job(job_name)
        
        if not db_row:
            return None
        
        return ScrapingConfig.from_db_row(db_row)
    
    def list_configs(self) -> List[ScrapingConfig]:
        """
        Zwraca listę wszystkich konfiguracji z bazy danych.
        
        Returns:
            Lista obiektów konfiguracji
        """
        db_rows = get_all_scheduled_jobs(enabled_only=False)
        return [ScrapingConfig.from_db_row(row) for row in db_rows]
    
    def list_active_configs(self) -> List[ScrapingConfig]:
        """
        Zwraca listę aktywnych konfiguracji.
        
        Returns:
            Lista enabled konfiguracji
        """
        db_rows = get_all_scheduled_jobs(enabled_only=True)
        return [ScrapingConfig.from_db_row(row) for row in db_rows]
    
    def delete_config(self, job_name: str) -> bool:
        """
        Usuwa konfigurację z bazy danych.
        
        Args:
            job_name: Nazwa zadania do usunięcia
            
        Returns:
            True jeśli usunięto, False jeśli nie znaleziono
        """
        config = self.load_config(job_name)
        if not config:
            return False
        
        delete_scheduled_job(job_name)
        return True
    
    def update_config(self, config: ScrapingConfig):
        """
        Aktualizuje istniejącą konfigurację w bazie.
        
        Args:
            config: Zaktualizowana konfiguracja
        """
        # insert_scheduled_job używa ON DUPLICATE KEY UPDATE
        self.save_config(config)
    
    def disable_config(self, job_name: str):
        """
        Wyłącza zadanie (ustawia enabled=False).
        
        Args:
            job_name: Nazwa zadania
        """
        config = self.load_config(job_name)
        if config:
            config.enabled = False
            self.update_config(config)
    
    def enable_config(self, job_name: str):
        """
        Włącza zadanie (ustawia enabled=True).
        
        Args:
            job_name: Nazwa zadania
        """
        config = self.load_config(job_name)
        if config:
            config.enabled = True
            self.update_config(config)
    
    def mark_job_executed(self, job_name: str, next_run: datetime = None):
        """
        Oznacza zadanie jako wykonane i aktualizuje statystyki.
        
        Args:
            job_name: Nazwa zadania
            next_run: Następny czas wykonania (opcjonalnie)
        """
        update_job_run_stats(job_name, next_run)
    
    # ========================================================================
    # LEGACY SUPPORT - Reading old JSON configs
    # ========================================================================
    
    def load_legacy_config(self, job_name: str) -> Optional[ScrapingConfig]:
        """
        Ładuje starą konfigurację z pliku JSON (backward compatibility).
        
        Args:
            job_name: Nazwa zadania
            
        Returns:
            Obiekt konfiguracji lub None
        """
        import os
        
        filepath = os.path.join(self.config_dir, f"{job_name}.json")
        
        if not os.path.exists(filepath):
            return None
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return ScrapingConfig.from_dict(data)
    
    def migrate_legacy_configs_to_db(self) -> int:
        """
        Migruje wszystkie stare konfiguracje JSON do bazy danych.
        
        Returns:
            Liczba zmigrowanych konfiguracji
        """
        import os
        
        if not os.path.exists(self.config_dir):
            return 0
        
        migrated = 0
        for filename in os.listdir(self.config_dir):
            if filename.endswith('.json'):
                job_name = filename[:-5]
                legacy_config = self.load_legacy_config(job_name)
                
                if legacy_config:
                    # Check if already in database
                    if not self.load_config(job_name):
                        self.save_config(legacy_config)
                        migrated += 1
                        print(f"✓ Migrated: {job_name}")
        
        return migrated
    
    # ========================================================================
    # VALIDATION HELPERS
    # ========================================================================
    
    def validate_config(self, config: ScrapingConfig) -> List[str]:
        """
        Waliduje konfigurację.
        
        Args:
            config: Konfiguracja do walidacji
            
        Returns:
            Lista błędów (pusta jeśli OK)
        """
        errors = []
        
        # Required fields
        if not config.job_name:
            errors.append("job_name is required")
        if not config.company:
            errors.append("company is required")
        if not config.model:
            errors.append("model is required")
        if not config.cron_schedule:
            errors.append("cron_schedule is required")
        
        # Date format validation (dd-mm-yyyy)
        from datetime import datetime
        for date_field, date_value in [('date_from', config.date_from), ('date_to', config.date_to)]:
            if date_value:
                try:
                    datetime.strptime(date_value, '%d-%m-%Y')
                except ValueError:
                    errors.append(f"{date_field} must be in dd-mm-yyyy format")
        
        return errors


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def create_config(
    job_name: str,
    company: str,
    date_from: str,
    date_to: str,
    model: str,
    cron_schedule: str,
    enabled: bool = True,
    report_types: List[str] = None,
    report_categories: List[str] = None,
    description: str = ""
) -> ScrapingConfig:
    """
    Tworzy i zapisuje nową konfigurację zadania.
    
    Returns:
        Utworzona konfiguracja
    """
    config = ScrapingConfig(
        job_name=job_name,
        company=company,
        date_from=date_from,
        date_to=date_to,
        model=model,
        cron_schedule=cron_schedule,
        enabled=enabled,
        report_types=report_types,
        report_categories=report_categories,
        description=description
    )
    
    manager = ConfigManager()
    errors = manager.validate_config(config)
    
    if errors:
        raise ValueError(f"Invalid configuration: {', '.join(errors)}")
    
    manager.save_config(config)
    return config


if __name__ == "__main__":
    # Test database-backed config manager
    print("=== Config Manager v2.0 - Database Test ===\n")
    
    manager = ConfigManager()
    
    # List all configs
    configs = manager.list_configs()
    print(f"Found {len(configs)} configurations in database:")
    for cfg in configs:
        status = "✓ ENABLED" if cfg.enabled else "✗ DISABLED"
        print(f"  {status} | {cfg.job_name} - {cfg.company} ({cfg.cron_schedule})")
    
    print("\n=== Test Complete ===")
