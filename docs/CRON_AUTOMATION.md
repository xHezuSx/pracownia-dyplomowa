# 🤖 Automatyzacja raportów GPW - Funkcje Cron

## 📋 Przegląd

System automatyzacji pozwala na zaplanowanie regularnych raportów z GPW bez ręcznego uruchamiania scrapera.

## 🗂️ Nowe pliki

### 1. `config_manager.py`
Zarządza konfiguracjami zadań:
- `ScrapingConfig` - klasa danych konfiguracji (firma, daty, model, cron)
- `ConfigManager` - zapisywanie/ładowanie/usuwanie konfiguracji JSON
- Szablony: codzienny, tygodniowy, miesięczny raport

**Przykład użycia:**
```python
from config_manager import ConfigManager, create_from_template

# Utwórz konfigurację z szablonu
config = create_from_template("tygodniowy_raport", "Asseco")

# Zapisz
manager = ConfigManager()
manager.save_config(config)

# Wczytaj
loaded = manager.load_config("tygodniowy_raport_Asseco")
```

### 2. `cron_manager.py`
Zarządza zadaniami w systemowym crontab:
- `CronManager` - instalacja/usuwanie zadań cron
- Automatyczne znajdowanie Python venv
- Walidacja wyrażeń cron
- Bezpieczne modyfikowanie crontab (markery GPW_SCRAPER)

**Przykład użycia:**
```python
from cron_manager import CronManager

manager = CronManager()

# Zainstaluj wszystkie aktywne konfiguracje do crontab
success, msg = manager.install_jobs()
print(msg)  # ✅ Zainstalowano 3 zadań do crontab`

# Lista zainstalowanych
for job in manager.get_installed_jobs():
    print(job)

# Usuń wszystkie
manager.uninstall_jobs()
```

### 3. `run_scheduled.py`
Skrypt wykonawczy uruchamiany przez cron:
- Czyta konfigurację po nazwie zadania
- Uruchamia scraping
- Zapisuje wyniki do `scheduled_results/`
- Loguje do `logs/nazwa_zadania.log`

**Przykład użycia:**
```bash
# Ręczne uruchomienie (tak samo jak robi cron)
python run_scheduled.py tygodniowy_raport_Asseco

# Sprawdź logi
tail -f logs/tygodniowy_raport_Asseco.log
```

### 4. `scheduler_ui.py`
Interfejs Gradio do zarządzania harmonogramem:
- **Zakładka "Nowa konfiguracja"**: tworzenie z formularzem
- **Zakładka "Szablony"**: szybkie tworzenie z predefiniowanych wzorców
- **Zakładka "Konfiguracje"**: przeglądanie, usuwanie, import/export
- **Zakładka "Crontab"**: instalacja/usunięcie zadań, podgląd

## 🚀 Szybki start

### 1. Utwórz konfigurację

**Opcja A: Z szablonu (najszybsze)**
```bash
python -c "
from config_manager import create_from_template, ConfigManager

config = create_from_template('tygodniowy_raport', 'Asseco')
ConfigManager().save_config(config)
print(f'✅ Utworzono: {config.job_name}')
"
```

**Opcja B: Ręcznie**
```python
from config_manager import ScrapingConfig, ConfigManager

config = ScrapingConfig(
    job_name="moj_raport",
    company="PKN Orlen",
    date_from="01-10-2025",
    date_to="25-10-2025",
    model="llama3.2:latest",
    cron_schedule="0 10 * * 1",  # Każdy poniedziałek o 10:00
    enabled=True,
    description="Tygodniowy raport PKN"
)

ConfigManager().save_config(config)
```

### 2. Zainstaluj do crontab

```python
from cron_manager import CronManager

manager = CronManager()
success, message = manager.install_jobs()
print(message)
```

Lub:
```bash
python cron_manager.py
```

### 3. Sprawdź instalację

```bash
crontab -l
```

Powinieneś zobaczyć:
```
# GPW_SCRAPER_START
# Tygodniowy raport (ostatnie 7 dni)
0 9 * * 1 /ścieżka/do/.venv/bin/python /ścieżka/do/run_scheduled.py tygodniowy_raport_Asseco >> /ścieżka/do/logs/tygodniowy_raport_Asseco.log 2>&1
# GPW_SCRAPER_END
```

### 4. Testuj ręcznie

Nie czekaj na harmonogram - uruchom od razu:
```bash
python run_scheduled.py tygodniowy_raport_Asseco
```

Wyniki znajdziesz w `scheduled_results/`.

## 📅 Wyrażenia cron

Format: `minuta godzina dzień miesiąc dzień_tygodnia`

**Przykłady:**

| Wyrażenie | Znaczenie |
|-----------|-----------|
| `0 9 * * *` | Codziennie o 9:00 |
| `0 9 * * 1` | Każdy poniedziałek o 9:00 |
| `0 10 1 * *` | 1. dzień miesiąca o 10:00 |
| `*/30 * * * *` | Co 30 minut |
| `0 8-17 * * 1-5` | Co godzinę 8:00-17:00, pon-pt |
| `0 0 * * 0` | Każdą niedzielę o północy |

## 📂 Struktura katalogów

```
pracownia-dyplomowa/
├── configs/                    # Konfiguracje JSON
│   ├── tygodniowy_raport_Asseco.json
│   └── codzienny_raport_PKN.json
├── logs/                       # Logi wykonania
│   ├── tygodniowy_raport_Asseco.log
│   └── codzienny_raport_PKN.log
├── scheduled_results/          # Wyniki automatyczne
│   ├── tygodniowy_raport_Asseco_20251025_090000.txt
│   └── ...
└── REPORTS/                    # Pobrane PDF-y (jak wcześniej)
```

## 🔧 Rozwiązywanie problemów

### Problem: "crontab: command not found"
```bash
# Zainstaluj crona
sudo apt install cron  # Ubuntu/Debian
sudo systemctl enable cron
sudo systemctl start cron
```

### Problem: Zadanie nie wykonuje się

1. **Sprawdź logi:**
```bash
tail -f logs/nazwa_zadania.log
```

2. **Sprawdź czy cron działa:**
```bash
systemctl status cron
```

3. **Test ręczny:**
```bash
/ścieżka/do/.venv/bin/python run_scheduled.py nazwa_zadania
```

### Problem: Brak uprawnień

Crontab działa na uprawnieniach użytkownika - nie potrzeba sudo.
Jeśli masz problemy z zapisem do `/var/log`, logi są zapisywane do lokalnego katalogu `logs/`.

## 🎯 Najlepsze praktyki

1. **Nazwy zadań**: Używaj underscore zamiast spacji (`tygodniowy_raport_Asseco`)
2. **Harmonogram**: Nie planuj dużych zadań w godzinach szczytu
3. **Logowanie**: Regularnie sprawdzaj `logs/` pod kątem błędów
4. **Backup**: Exportuj konfiguracje przed zmianami
5. **Testing**: Zawsze testuj ręcznie przed dodaniem do crona

## 📊 Przykładowe scenariusze

### Scenario 1: Cotygodniowy monitoring 5 firm

```python
from config_manager import create_from_template, ConfigManager

firmy = ["Asseco", "PKN Orlen", "PZU", "CD Projekt", "LPP"]
manager = ConfigManager()

for firma in firmy:
    config = create_from_template("tygodniowy_raport", firma)
    config.cron_schedule = f"0 {8 + firmy.index(firma)} * * 1"  # 8:00, 9:00, 10:00...
    manager.save_config(config)

# Zainstaluj wszystkie
from cron_manager import CronManager
CronManager().install_jobs()
```

### Scenario 2: Raporty kwartalne

```python
from config_manager import ScrapingConfig, ConfigManager
from datetime import datetime, timedelta

# Ostatni kwartał
dzisiaj = datetime.now()
trzy_miesiace_temu = dzisiaj - timedelta(days=90)

config = ScrapingConfig(
    job_name="kwartalny_raport_Asseco",
    company="Asseco",
    date_from=trzy_miesiace_temu.strftime("%d-%m-%Y"),
    date_to=dzisiaj.strftime("%d-%m-%Y"),
    model="gemma:7b",
    cron_schedule="0 12 1 */3 *",  # 1. dzień co 3 miesiące o 12:00
    enabled=True,
    description="Raport kwartalny"
)

ConfigManager().save_config(config)
```

## 🔜 Przyszłe funkcje (TODO)

- [ ] Agregowane raporty tygodniowe (podsumowanie podsumowań)

## 📝 Struktura konfiguracji JSON

```json
{
  "job_name": "tygodniowy_raport_Asseco",
  "company": "Asseco",
  "date_from": "18-10-2025",
  "date_to": "25-10-2025",
  "model": "llama3.2:latest",
  "cron_schedule": "0 9 * * 1",
  "enabled": true,
  "email_notify": null,
  "description": "Tygodniowy raport (ostatnie 7 dni)"
}
```

## 💡 Wskazówki

- **Cron uruchamia zadania w tle** - nie zobaczysz żadnych komunikatów, tylko w logach
- **Ścieżki muszą być bezwzględne** - cron nie zna twojego katalogu roboczego
- **Environment variables**: cron ma minimalny environment, wszystko jest w skrypcie
- **Testuj lokalnie**: `python run_scheduled.py nazwa` przed dodaniem do crona

---

**Utworzono**: 25.10.2025  
**Autor**: GPW Scraper Team  
**Status**: ✅ Produkcyjny
