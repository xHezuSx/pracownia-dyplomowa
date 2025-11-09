# 📊 Analiza Projektu GPW Scraper - Dogłębne Zrozumienie

**Data:** 9 listopada 2025  
**Autor analizy:** GitHub Copilot  
**Wersja projektu:** 2.0 (baza danych MySQL)

---

## 🎯 Twoje Wymagania (Cel Biznesowy)

### Tryb 1: Scraping Manualny (jednorazowy)
**Użytkownik wpisuje parametry → pobiera raporty → generuje streszczenia**

1. **Input od użytkownika:**
   - Nazwa spółki (np. "Asseco")
   - Zakres dat (od - do)
   - Parametry filtrowania (typ raportu, kategoria)

2. **Proces:**
   - Scraping strony GPW → pobieranie raportów (PDF/HTML)
   - Dla **każdego pojedynczego raportu**: lokalny LLM generuje **pojedyncze streszczenie**
   - Na podstawie **wszystkich pojedynczych streszczeń**: LLM tworzy **jedno duże zbiorcze streszczenie**

3. **Output:**
   - **Pojedyncze streszczenia** → zapisane gdzieś (plik .md lub baza)
   - **Duże zbiorcze streszczenie** → **PDF** + zapis w bazie
   - Użytkownik dostaje wynik od razu w UI

### Tryb 2: Scraping Okresowy (CRON)
**System automatycznie, co jakiś czas, scrapuje spółkę i generuje streszczenia**

1. **Konfiguracja CRON:**
   - Użytkownik ustawia: spółkę, harmonogram (np. co tydzień), model LLM
   - System zapisuje konfigurację

2. **Proces (automatyczny, w tle):**
   - CRON uruchamia scraping zgodnie z harmonogramem
   - Pobiera **nowe raporty** od ostatniego uruchomienia
   - Dla każdego nowego raportu → **pojedyncze streszczenie** (LLM)
   - Na podstawie wszystkich streszczeń → **duże zbiorcze streszczenie** dla tego uruchomienia

3. **Output:**
   - **Pojedyncze streszczenia** → zapisane gdzieś
   - **Duże zbiorcze streszczenie** → **PDF** + zapis w bazie

4. **Dodatkowa funkcja (META-ANALIZA):**
   - Jeśli system ma **co najmniej 2 duże zbiorcze streszczenia** (z różnych uruchomień CRON):
     - LLM analizuje **wszystkie duże streszczenia** razem
     - Generuje **meta-raport**: "Jak wiedzie się spółce w czasie?"
     - Format: PDF + zapis w bazie

---

## 📦 Co Jest Już Zrobione (Stan Obecny)

### ✅ Co Działa:

#### 1. **Scraping Manualny** (Tryb 1) - **80% gotowe**
- ✅ Interface Gradio (`app.py`) - zakładka "Scraping"
- ✅ Pobieranie raportów z GPW (`scrape_script.py`)
- ✅ Pobieranie załączników (PDF, HTML)
- ✅ Generowanie **pojedynczych streszczeń** przez LLM (`summary.py`)
  - Używa K-means clustering do wyciągania kluczowych fragmentów
  - Model Ollama (llama3.2, gemma, qwen2.5)
- ✅ Zapis do bazy MySQL:
  - Firma (`companies`)
  - Raporty (`reports`)
  - Historia wyszukiwań (`search_history`)
  - Pobrane pliki (`downloaded_files`) z deduplikacją MD5
- ✅ **Zbiorczy raport Markdown** (`generate_summary_report()` w `scrape_script.py`)
  - Tworzy plik `.md` w `SUMMARY_REPORTS/`
  - Zawiera: metadatę, listę raportów, wszystkie streszczenia z LLM
  - Zapisuje metadata do `summary_reports` w bazie

#### 2. **Scraping Okresowy** (Tryb 2) - **70% gotowe**
- ✅ Zarządzanie konfiguracjami (`config_manager.py`)
  - Zapis/odczyt z bazy `scheduled_jobs`
  - Parametry: firma, daty, model, harmonogram cron
- ✅ Instalacja zadań CRON (`cron_manager.py`)
  - Automatyczne dodawanie do systemowego crontab
  - Walidacja wyrażeń cron
- ✅ Skrypt wykonawczy (`run_scheduled.py`)
  - Uruchamiany przez CRON
  - Ładuje konfigurację, wywołuje `scrape()`
  - Zapisuje wyniki do `scheduled_results/`
  - Loguje wykonanie do `job_execution_log` w bazie
- ✅ Interface Gradio - zakładka "Harmonogram"
  - Tworzenie/usuwanie konfiguracji
  - Instalacja/usunięcie z crontab
  - Podgląd aktywnych zadań
- ✅ Zakładka "Zbiorcze Raporty"
  - Przeglądanie wygenerowanych raportów
  - Filtrowanie po firmie/zadaniu
  - Podgląd treści

### ❌ Czego Brakuje:

#### 1. **Format PDF dla zbiorczego streszczenia**
- **Obecny stan:** Zbiorczy raport jest zapisywany jako **Markdown** (`.md`)
- **Twoje wymaganie:** Zbiorczy raport ma być w **PDF**
- **Co trzeba zrobić:**
  - Dodać konwersję `.md` → `.pdf` (np. biblioteka `markdown`, `pdfkit`, `weasyprint`)
  - Lub: generować PDF bezpośrednio (np. `reportlab`, `fpdf`)

#### 2. **Zapis pojedynczych streszczeń**
- **Obecny stan:** 
  - Pojedyncze streszczenia są generowane (`get_summaries()`)
  - Są **wyświetlane w UI** i **wstawiane do zbiorczego raportu MD**
  - **NIE są zapisywane osobno** jako pliki ani w dedykowanym polu bazy
- **Twoje wymaganie:** Pojedyncze streszczenia mają być zapisywane (plik .md lub baza)
- **Co trzeba zrobić:**
  - **Opcja A:** Zapisywać każde pojedyncze streszczenie jako osobny plik `.md` w folderze (np. `SUMMARY_REPORTS/single/`)
  - **Opcja B:** Zapisywać do bazy - w tabeli `downloaded_files` jest już kolumna `summary_text` (LONGTEXT) - **TO JUŻ ISTNIEJE!**
  - **Rekomendacja:** Wykorzystaj istniejącą kolumnę `summary_text` w `downloaded_files` — to najprostsze

#### 3. **META-ANALIZA (dla Trybu 2)**
- **Obecny stan:** **Nie istnieje**
- **Twoje wymaganie:** 
  - Gdy są ≥2 duże zbiorcze streszczenia (z różnych uruchomień CRON)
  - System automatycznie tworzy meta-raport: analiza trendu spółki w czasie
- **Co trzeba zrobić:**
  - Nowa funkcja: `generate_meta_report(company, summary_report_ids)`
  - Pobiera wszystkie duże streszczenia z bazy (`summary_reports`)
  - Wysyła je do LLM z promptem: "Przeanalizuj te raporty i opisz jak wiedzie się firmie w czasie"
  - Zapisuje jako osobny typ raportu (PDF + baza)

#### 4. **Drobne poprawki:**
- ❌ Pojedyncze streszczenia NIE są obecnie zapisywane do `downloaded_files.summary_text` (kod wywołuje `insert_downloaded_file` ale z `is_summarized=False` i bez `summary_text`)
- ❌ Format daty w bazie był błędny (ale to **już naprawione** dzisiaj)
- ❌ Brak pakietu `tabulate` (ale to **już naprawione** dzisiaj)

---

## 🔍 Jak Obecnie Działa System (Techniczne)

### Przepływ Tryb 1 (Manualny):
```
Użytkownik wypełnia formularz w Gradio
         ↓
app.py: run_scrape_ui()
         ↓
scrape_script.py: scrape()
         ↓
1. Pobiera HTML z GPW (BeautifulSoup)
2. Parsuje listę raportów
3. Pobiera załączniki (PDF/HTML)
4. Dla każdego pliku:
   - Wczytuje PDF/HTML
   - summary.py: summarize_document_with_kmeans_clustering()
     → K-means clustering → LLM → pojedyncze streszczenie
5. generate_summary_report():
   - Tworzy plik .md z:
     * Metadane (firma, daty, liczba raportów)
     * Tabela raportów (DataFrame.to_markdown())
     * Wszystkie pojedyncze streszczenia
   - Zapisuje do SUMMARY_REPORTS/
   - Zapisuje metadata do bazy (summary_reports)
6. Zwraca wyniki do UI
```

### Przepływ Tryb 2 (CRON):
```
Użytkownik tworzy konfigurację w UI
         ↓
config_manager.py: save_config()
         ↓
Zapis do bazy: scheduled_jobs
         ↓
Użytkownik klika "Zainstaluj do crontab"
         ↓
cron_manager.py: install_jobs()
         ↓
Dodaje wpis do systemowego crontab:
  "0 9 * * 1 /path/to/python run_scheduled.py job_name >> logs/job_name.log"
         ↓
--- W zaplanowanym czasie ---
         ↓
CRON uruchamia: run_scheduled.py job_name
         ↓
1. Ładuje konfigurację z bazy (scheduled_jobs)
2. Wywołuje scrape() (IDENTYCZNIE jak Tryb 1)
3. Zapisuje wyniki:
   - Plik tekstowy: scheduled_results/job_name_timestamp.txt
   - Metadata: job_execution_log (status, liczba raportów)
4. Aktualizuje statystyki: scheduled_jobs (last_run, run_count)
```

### Baza Danych (MySQL - struktura v2.0):
```
companies          - Spółki GPW (id, nazwa, sektor)
   ↓ (FK)
reports            - Pojedyncze raporty (data, tytuł, link, kurs giełdowy)
   ↓ (FK)
downloaded_files   - Pobrane pliki (PDF/HTML) z MD5, summary_text (LONGTEXT)
                     ↑ TO JEST MIEJSCE NA POJEDYNCZE STRESZCZENIA

scheduled_jobs     - Konfiguracje CRON (firma, harmonogram, last_run, run_count)
   ↓ (FK)
job_execution_log  - Historia uruchomień (status, czas trwania, błędy)
   ↓ (FK - opcjonalne)
summary_reports    - Zbiorcze raporty MD (ścieżka pliku, preview, tagi)

search_history     - Historia ręcznych wyszukiwań (użytkownik, parametry, data)
```

---

## 📋 Co Trzeba Zrobić (Konkretne Kroki)

### Prioryt 1: Zapis Pojedynczych Streszczeń
**Cel:** Każde pojedyncze streszczenie zapisane w bazie.

**Jak:**
1. W `scrape_script.py`, funkcja `get_summaries()`:
   - Dla każdego pliku, po wygenerowaniu streszczenia:
   - Znajdź `file_id` w `downloaded_files` (po `md5_hash` lub `file_name`)
   - Wywołaj `update_file_summary(file_id, summary_text)`
   
2. `database_connection.py` już ma funkcję `update_file_summary()` - gotowe!

**Prosta zmiana (~10 linii kodu).**

---

### Prioryt 2: Konwersja Zbiorczego Raportu do PDF
**Cel:** `generate_summary_report()` tworzy PDF zamiast (lub oprócz) MD.

**Opcje:**
- **Opcja A (Prosta):** Markdown → PDF
  - Biblioteka: `markdown` + `pdfkit` (wymaga `wkhtmltopdf`)
  - Lub: `markdown` + `weasyprint` (pure Python, lepsze formatowanie)
  
- **Opcja B (Bardziej kontroli):** Bezpośrednio PDF
  - Biblioteka: `reportlab` (niskopoziomowe, pełna kontrola)
  - Lub: `fpdf2` (prostsze API)

**Rekomendacja:** Opcja A z `weasyprint` - przyjazna, obsługuje CSS, ładne PDF-y.

**Kod (~30 linii):**
```python
# W scrape_script.py, po zapisaniu .md:
import markdown
from weasyprint import HTML

# Konwertuj MD → HTML
with open(filepath_md, 'r', encoding='utf-8') as f:
    md_text = f.read()
html_text = markdown.markdown(md_text, extensions=['tables'])

# HTML → PDF
filepath_pdf = filepath_md.replace('.md', '.pdf')
HTML(string=html_text).write_pdf(filepath_pdf)

# Aktualizuj bazę: file_format='pdf', file_path=filepath_pdf
```

---

### Prioryt 3: META-ANALIZA (dla Trybu 2)
**Cel:** Gdy ≥2 duże streszczenia → automatycznie generuj meta-raport.

**Jak:**
1. Nowa funkcja w `scrape_script.py` lub osobny plik `meta_analysis.py`:
   ```python
   def generate_meta_report(company: str, model_name: str):
       # 1. Pobierz wszystkie summary_reports dla company z bazy
       reports = get_summary_reports(company=company, limit=100)
       
       # 2. Jeśli < 2, return (za mało danych)
       if len(reports) < 2:
           return None
       
       # 3. Wczytaj treść każdego raportu (z file_path)
       summaries_text = []
       for report in reports:
           with open(report['file_path'], 'r') as f:
               summaries_text.append(f.read())
       
       # 4. Skleić wszystko i wysłać do LLM
       combined = "\n\n---\n\n".join(summaries_text)
       prompt = f"Przeanalizuj poniższe raporty z {company} i opisz trend: jak wiedzie się firmie w czasie?\n\n{combined}"
       
       # 5. Wywołaj LLM (podobnie jak w summary.py)
       llm = ChatOllama(model=model_name, temperature=0, num_predict=1500)
       response = llm.invoke(prompt)
       meta_summary = response.content
       
       # 6. Zapisz jako PDF + baza (podobnie jak generate_summary_report)
       save_meta_report_to_pdf(company, meta_summary, model_name)
   ```

2. Wywołanie:
   - **Opcja A:** W `run_scheduled.py`, po każdym sukcesie sprawdź liczbę raportów i wywołaj `generate_meta_report()`
   - **Opcja B:** Osobne zadanie CRON (np. raz w miesiącu)
   - **Opcja C:** Przycisk w UI "Wygeneruj meta-analizę"

**Rekomendacja:** Opcja A (automatycznie po każdym CRON) + Opcja C (ręcznie w UI).

**Kod (~50-80 linii).**

---

## 🛠️ Rekomendacje Implementacji (Priorytet i Prostota)

### Faza 1: Minimum Viable Product (MVP) - **2-3 godziny pracy**
1. ✅ **Prioryt 1** - Zapis pojedynczych streszczeń do bazy (~10 linii)
2. ✅ **Prioryt 2** - Konwersja MD → PDF (~30 linij + instalacja `weasyprint`)

Po Fazie 1: **Oba tryby (manualny + CRON) działają zgodnie z wymaganiami, PDF-y są generowane.**

---

### Faza 2: Advanced Feature - **1-2 godziny pracy**
3. ✅ **Prioryt 3** - META-ANALIZA (~50-80 linii + przycisk w UI)

Po Fazie 2: **Pełna funkcjonalność, w tym analiza trendów spółki w czasie.**

---

### Faza 3: Polishing (opcjonalnie) - **1 godzina pracy**
- Lepsze formatowanie PDF (CSS dla weasyprint)
- Email powiadomienia (już jest `config.email_notify`, tylko dodać wysyłkę)
- UI: podgląd pojedynczych streszczeń w zakładce "Zbiorcze Raporty"
- Archiwizacja starych raportów (auto-delete po 90 dniach)

---

## 🚨 Potencjalne Problemy i Rozwiązania

### Problem 1: Rozmiar bazy danych (LONGTEXT w `summary_text`)
- **Symptom:** Pojedyncze streszczenia mogą być duże (200-500 słów × 100 plików = 50KB-200KB na raport)
- **Rozwiązanie:** LONGTEXT w MySQL obsługuje do 4GB - wystarczy na lata danych

### Problem 2: Czas generowania meta-analizy
- **Symptom:** LLM musi przetworzyć wiele dużych streszczeń → może trwać 2-5 minut
- **Rozwiązanie:** 
  - Uruchamiać meta-analizę asynchronicznie (osobny proces)
  - Pokazać użytkownikowi "Generowanie... proszę czekać"
  - Opcjonalnie: limitować liczbę raportów (np. ostatnie 10)

### Problem 3: Formatowanie PDF
- **Symptom:** Tabele z Markdown mogą się źle renderować w PDF
- **Rozwiązanie:** 
  - Użyć `weasyprint` + CSS do stylowania
  - Lub: zamienić tabele na listy punktowane w MD przed konwersją

### Problem 4: Deduplikacja w CRON
- **Symptom:** Ten sam raport może być pobrany dwa razy (jeśli CRON uruchomi się dwa razy tego samego dnia)
- **Rozwiązanie:** **Już rozwiązane!** - MD5 hash w `downloaded_files` blokuje duplikaty

---

## 📊 Metryki Sukcesu (Jak Sprawdzić, Że Działa)

### Test Tryb 1 (Manualny):
1. ✅ Wpisz "Asseco", data "01-11-2025", pobierz PDF
2. ✅ Sprawdź `SUMMARY_REPORTS/` - jest plik **PDF** z nazwą `Asseco_TIMESTAMP_summary.pdf`
3. ✅ Otwórz PDF - zawiera:
   - Metadatę (firma, daty, liczba raportów)
   - Listę raportów (tabela)
   - Wszystkie pojedyncze streszczenia (po jednym na plik)
4. ✅ Sprawdź bazę:
   - `downloaded_files`: kolumna `summary_text` wypełniona dla każdego pliku
   - `summary_reports`: nowy rekord z `file_format='pdf'`, `file_path` wskazuje na PDF

### Test Tryb 2 (CRON):
1. ✅ Utwórz konfigurację "asseco_test" w UI (harmonogram: */5 * * * * - co 5 minut)
2. ✅ Kliknij "Zainstaluj do crontab"
3. ✅ Poczekaj 5 minut
4. ✅ Sprawdź `scheduled_results/` - nowy plik tekstowy z wynikami
5. ✅ Sprawdź `logs/asseco_test.log` - logi wykonania
6. ✅ Sprawdź bazę:
   - `job_execution_log`: nowy rekord ze statusem 'success'
   - `summary_reports`: nowy PDF wygenerowany

### Test META-ANALIZA:
1. ✅ Uruchom CRON dwa razy (lub manualnie dwa razy dla tej samej firmy, różne daty)
2. ✅ Sprawdź `summary_reports` - są ≥2 rekordy dla firmy
3. ✅ Kliknij "Wygeneruj meta-analizę" (lub poczekaj na auto)
4. ✅ Nowy PDF z meta-analizą w `SUMMARY_REPORTS/META/`
5. ✅ PDF zawiera: analizę trendu, porównanie raportów, wnioski o stanie firmy

---

## 🎯 Podsumowanie - Co Rozumiem

### Stan Obecny:
- **80-90% funkcjonalności już działa**
- Scraping, LLM, baza danych, CRON, UI - wszystko jest
- Brakuje głównie: **PDF zamiast MD**, **zapis pojedynczych streszczeń do bazy**, **meta-analiza**

### Co Trzeba Dodać:
1. **~10 linii kodu** - zapis streszczeń do `downloaded_files.summary_text`
2. **~30 linii kodu** - konwersja MD → PDF (`weasyprint`)
3. **~50-80 linii kodu** - meta-analiza (opcjonalne, ale wartościowe)

### Moja Ocena:
- **To NIE jest rocket science** - są to proste rozszerzenia istniejącego kodu
- **Projekt jest dobrze zorganizowany** - wszystkie elementy są na miejscu
- **Baza danych v2.0 jest przygotowana** - `summary_text` w `downloaded_files` już czeka

### Kluczowe Decyzje Do Podjęcia:
1. **Biblioteka do PDF:** `weasyprint` (moja rekomendacja) vs `reportlab` vs `pdfkit`?
2. **Gdzie zapisać pojedyncze streszczenia:**
   - Tylko baza (`downloaded_files.summary_text`) ← **REKOMENDACJA**
   - Tylko pliki `.md` (folder `SUMMARY_REPORTS/single/`)
   - Oba miejsca (redundancja, ale bezpieczne)
3. **Kiedy uruchamiać meta-analizę:**
   - Automatycznie po każdym CRON (jeśli ≥2 raporty) ← **REKOMENDACJA**
   - Osobne zadanie CRON (np. raz w miesiącu)
   - Tylko ręcznie w UI

---

## ✅ Następne Kroki (Po Porozumieniu)

### Krok 1: Potwierdzenie Zrozumienia
- Przeczytaj ten dokument
- Potwierdź, że rozumiemy problem tak samo
- Zdecyduj o kluczowych wyborach (PDF lib, meta-analiza trigger)

### Krok 2: Implementacja (Po Twojej Akceptacji)
- Zaimplementuję zmiany w kolejności priorytetu
- Będę pisał **minimalny kod** (bez nadmiaru)
- Będę testował każdą zmianę przed przejściem dalej

### Krok 3: Testy
- Przetestujemy razem oba tryby
- Sprawdzimy PDF-y
- Zweryfikujemy bazę

---

## 💬 Pytania Do Ciebie

1. **Czy tak rozumiesz problem jak ja opisałem?**
2. **Czy wybór `weasyprint` dla PDF jest OK?** (alternatywnie: `reportlab`)
3. **Pojedyncze streszczenia - tylko baza czy też pliki `.md`?** (polecam: tylko baza)
4. **Meta-analiza - automatycznie po każdym CRON czy ręcznie w UI?** (polecam: oba)
5. **Czy masz inne uwagi lub pytania?**

---

**Gdy odpowiesz na powyższe pytania, zacznę implementację. Będę działał małymi krokami, testując każdy krok, i informując Cię o postępach.**
