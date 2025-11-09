# 📊 Aktualizacja struktury bazy danych GPW Scraper v2.0

## 🔄 ZMIANY W STOSUNKU DO STAREJ WERSJI

### ✅ NOWE TABELE:

1. **`scheduled_jobs`** - Konfiguracje zadań cron
   - Zastępuje pliki JSON w `/configs/`
   - Przechowuje wszystkie parametry harmonogramu
   - Śledzi statystyki wykonań (`last_run`, `next_run`, `run_count`)
   - Wsparcie dla JSON: `report_types`, `report_categories`, `tags`

2. **`summary_reports`** - Zbiorcze raporty MD/PDF
   - Ścieżki do plików `.md` / `.pdf`
   - Metadata: liczba raportów, dokumentów, rozmiar
   - Podgląd (pierwsze 500 znaków)
   - System tagów i archiwizacji

3. **`job_execution_log`** - Historia wykonań zadań
   - Status: success, failed, running, cancelled
   - Czas wykonania, liczba przetworzonych dokumentów
   - Powiązanie z wygenerowanym raportem zbiorczym
   - Ścieżka do pliku logu

4. **`downloaded_files`** - Rejestr pobranych plików
   - Śledzenie wszystkich PDF/HTML/CSV
   - Hash MD5 do wykrywania duplikatów
   - Przechowywanie podsumowań AI dla pojedynczych plików
   - Powiązanie z raportami GPW

### 🔧 ULEPSZONE TABELE:

1. **`firma`**
   - ➕ `pelna_nazwa` - pełna nazwa firmy
   - ➕ `sektor` - sektor gospodarki (Technologia, Bankowość, itd.)
   - ➕ `data_dodania` - timestamp dodania

2. **`dane`**
   - ➕ `id_raportu` - PRIMARY KEY auto-increment
   - ➕ `data_pobrania` - kiedy raport został pobrany
   - ✅ Indeksy na: `data`, `typ_raportu`, `kategoria_raportu`
   - ✅ CASCADE delete przy usunięciu firmy

3. **`historia`**
   - ➕ `model_used` - jaki model AI był użyty
   - ➕ `execution_time` - czas wykonania scrapingu
   - ➕ `data_wyszukiwania` - timestamp
   - ✅ Indeksy na: `company_name`, `data_wyszukiwania`

### 📊 NOWE WIDOKI:

1. **`v_active_jobs`** - Aktywne zadania z ostatnim statusem
   ```sql
   SELECT * FROM v_active_jobs WHERE enabled = TRUE;
   ```

2. **`v_company_stats`** - Statystyki per firma
   ```sql
   SELECT * FROM v_company_stats ORDER BY total_reports DESC;
   ```

### ⚙️ PROCEDURY SKŁADOWANE:

1. **`update_job_stats()`** - Aktualizacja statystyk po wykonaniu zadania
   ```sql
   CALL update_job_stats('weekly_asseco', 'success', 15, 8, 120, 42);
   ```

---

## 🎯 KORZYŚCI Z NOWEJ STRUKTURY:

### 1. **Pełna integracja z systemem harmonogramów**
   - ❌ Koniec z plikami JSON w `/configs/`
   - ✅ Wszystko w bazie danych
   - ✅ Łatwe zarządzanie przez UI

### 2. **Śledzenie historii wykonań**
   - Kiedy, ile razy, jaki status
   - Powiązanie logu → raport zbiorczy
   - Wykrywanie błędów

### 3. **Deduplikacja plików**
   - Hash MD5 każdego pobranego pliku
   - Oszczędność miejsca
   - Unikanie wielokrotnego przetwarzania

### 4. **Lepsza wydajność zapytań**
   - Indeksy na wszystkich często używanych kolumnach
   - Widoki dla skomplikowanych zapytań
   - Foreign keys z CASCADE

### 5. **Rozszerzalność**
   - JSON dla elastycznych danych (tagi, config)
   - LONGTEXT dla podsumowań AI
   - ENUM dla typów (łatwo rozszerzyć)

---

## 📝 MIGRACJA - CO TRZEBA ZAKTUALIZOWAĆ W KODZIE:

### 1. **`database_connection.py`**
```python
# NOWE funkcje do dodania:

def wstaw_scheduled_job(job_name, company, date_from, date_to, model, cron_schedule, enabled, report_types, report_categories)
def aktualizuj_scheduled_job(job_id, **kwargs)
def pobierz_scheduled_jobs(enabled_only=False)
def usun_scheduled_job(job_name)

def wstaw_job_execution_log(job_name, status, started_at, finished_at, duration, reports_found, docs_processed, summary_report_id, error_msg, log_path)
def pobierz_ostatnie_wykonanie(job_name)

def wstaw_downloaded_file(company, report_id, file_name, file_path, file_type, file_size, md5_hash, summary_text)
def sprawdz_czy_plik_istnieje(md5_hash)
def aktualizuj_podsumowanie_pliku(file_id, summary_text)

# ZAKTUALIZOWANE:
def wstaw_historie(..., model_used, execution_time)  # + 2 parametry
```

### 2. **`config_manager.py`**
```python
# MIGRACJA z JSON → baza danych
# Opcja 1: Zachować JSON jako backup
# Opcja 2: Całkowicie przenieść do bazy

class ConfigManager:
    def __init__(self, use_database=True):  # Nowy parametr
        if use_database:
            # Użyj database_connection
        else:
            # Stary system JSON
```

### 3. **`cron_manager.py`**
```python
# Po instalacji do crontab → aktualizuj next_run w bazie
def install_jobs(self):
    # ... istniejący kod ...
    # DODAJ:
    db.aktualizuj_next_run(job_name, next_run_timestamp)
```

### 4. **`run_scheduled.py`**
```python
# Na początku zadania:
db.wstaw_job_execution_log(job_name, 'running', datetime.now(), ...)

# Na końcu:
db.aktualizuj_job_execution_log(log_id, status='success', finished_at=..., summary_report_id=...)

# Przy każdym pobranym pliku:
md5 = calculate_md5(file_path)
if not db.sprawdz_czy_plik_istnieje(md5):
    db.wstaw_downloaded_file(...)
```

### 5. **`scrape_script.py`**
```python
# Po pobraniu pliku:
md5_hash = hashlib.md5(open(file_path, 'rb').read()).hexdigest()
wstaw_downloaded_file(..., md5_hash=md5_hash)

# Przy zapisie zbiorczego raportu:
wstaw_zbiorczy_raport(..., document_count=len(files), summary_preview=summary[:500])
```

---

## 🚀 INSTALACJA NOWEJ BAZY:

### Krok 1: Backup starej bazy
```bash
mysqldump -u user -pqwerty123 "gpw data" > gpw_data_backup_$(date +%Y%m%d).sql
```

### Krok 2: Usuń i stwórz nową
```bash
mysql -u user -pqwerty123 < gpw_data_v2.sql
```

### Krok 3: Migruj dane (opcjonalnie)
```bash
# Jeśli chcesz zachować stare dane:
mysql -u user -pqwerty123 "gpw data" -e "
INSERT INTO firma (nazwa) SELECT DISTINCT company_name FROM historia_old;
"
```

---

## ❓ PYTANIA DO ROZWAŻENIA:

1. **Czy zachować pliki JSON w `/configs/` jako backup?**
   - ✅ Zaleta: Bezpieczeństwo, łatwy rollback
   - ❌ Wada: Duplikacja danych

2. **Czy przechowywać pełne podsumowania w `downloaded_files.summary_text`?**
   - ✅ Zaleta: Szybki dostęp, możliwość re-generacji zbiorczego raportu
   - ❌ Wada: Duża baza (LONGTEXT)
   - 💡 Propozycja: Tak, ale z możliwością archiwizacji starych

3. **Czy automatycznie przenosić stare raporty do archiwum?**
   - 💡 Propozycja: Po 90 dniach `is_archived = TRUE`
   - Dedykowana funkcja w UI: "Pokaż archiwum"

4. **Czy synchronizować `scheduled_jobs` z crontab?**
   - ✅ Zaleta: Jednoznaczne źródło prawdy
   - 💡 Propozycja: Przy każdym `install_jobs()` → INSERT/UPDATE w bazie

---

## ✅ TODO PRZED MIGRACJĄ:

- [ ] Przejrzeć i zatwierdzić strukturę `gpw_data_v2.sql`
- [ ] Zdecydować o strategii migracji danych
- [ ] Zaktualizować wszystkie funkcje w `database_connection.py`
- [ ] Zaktualizować `config_manager.py` (baza vs JSON)
- [ ] Dodać obsługę logów w `run_scheduled.py`
- [ ] Dodać hash MD5 w `scrape_script.py`
- [ ] Przetestować nową bazę
- [ ] Utworzyć backup starej bazy
- [ ] Wykonać migrację
