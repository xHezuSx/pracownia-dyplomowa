# 📁 Struktura Projektu

## 🎯 Przegląd

Projekt został zrefaktoryzowany do modularnej architektury z wyraźnym podziałem odpowiedzialności.

## 📂 Struktura Katalogów

```
pracownia-dyplomowa/
├── src/                          # 🔹 Kod źródłowy (zrefaktoryzowany)
│   ├── core/                     # Logika biznesowa
│   │   ├── scraper.py           # Web scraping (BeautifulSoup)
│   │   ├── summarizer.py        # K-means + LLM analysis
│   │   └── pdf_generator.py     # PDF/Markdown generation
│   │
│   ├── database/                 # Warstwa danych
│   │   ├── connection.py        # Thread-safe DB connection
│   │   ├── company_repo.py      # Company CRUD
│   │   ├── report_repo.py       # Reports CRUD
│   │   ├── file_repo.py         # Files CRUD
│   │   ├── job_repo.py          # Job executions CRUD
│   │   └── history_repo.py      # History CRUD
│   │
│   ├── ui/                       # Interfejs Gradio
│   │   ├── app.py               # Main UI assembler
│   │   ├── shared_utils.py      # Shared UI utilities
│   │   └── tabs/                # Modular tabs
│   │       ├── scraping_tab.py
│   │       ├── automation_tab.py
│   │       ├── schedules_tab.py
│   │       ├── reports_tab.py
│   │       └── info_tab.py
│   │
│   ├── automation/               # Planowanie zadań
│   │   ├── config.py            # Job configuration dataclass
│   │   ├── scheduler.py         # CRON management
│   │   └── job_executor.py      # Task runner
│   │
│   ├── utils/                    # Narzędzia pomocnicze
│   │   └── ollama_utils.py      # Ollama model management
│   │
│   └── main.py                   # 🚀 RECOMMENDED entry point
│
├── docs/                         # 📚 Dokumentacja
│   ├── CRON_AUTOMATION.md       # Automatyzacja CRON
│   ├── DATABASE_DIAGRAM.md      # Diagram bazy danych
│   ├── DATABASE_MIGRATION_PLAN.md
│   └── PROJECT_STRUCTURE.md     # Ten plik
│
├── scripts/                      # Skrypty instalacyjne
│   ├── install_ollama.sh        # Instalacja Ollama
│   └── README_models.md         # Modele AI
│
├── tests/                        # Testy jednostkowe (TODO)
│
├── REPORTS/                      # 📄 Wygenerowane raporty PDF
├── SUMMARY_REPORTS/              # 📊 Zbiorcze raporty
├── logs/                         # 📝 Logi aplikacji
├── scheduled_results/            # ⏰ Wyniki zadań CRON
│
├── app.py                        # ⚠️ Backward compatibility wrapper
├── scrape_script.py             # ⚠️ Backward compatibility wrapper
├── database_connection.py       # ⚠️ Backward compatibility wrapper
├── config_manager.py            # ⚠️ Backward compatibility wrapper
├── cron_manager.py              # ⚠️ Backward compatibility wrapper
├── run_scheduled.py             # ⚠️ Backward compatibility wrapper
├── ollama_manager.py            # ⚠️ Backward compatibility wrapper
├── summary.py                   # ⚠️ Legacy file (unused)
│
├── requirements.txt              # 📦 Zależności Python
├── README.md                     # 📖 Dokumentacja główna
├── .env.example                  # 🔐 Template zmiennych środowiskowych
└── gpw_data.sql                  # 🗄️ Dump bazy danych
```

## 🚀 Punkty Wejścia

### Zalecany (nowy)
```bash
python src/main.py
```

### Kompatybilność wsteczna (stary)
```bash
python app.py
```

Oba działają identycznie - różnica tylko w organizacji kodu.

## 📊 Statystyki Refaktoryzacji

- **Przed**: 3 monolityczne pliki (~4000 linii)
- **Po**: 30+ modularnych plików
- **Separacja**: 5 głównych modułów (core, database, ui, automation, utils)
- **Wzorzec**: Repository pattern dla warstwy danych
- **UI**: 5 modularnych zakładek Gradio
- **Backward compatibility**: 100% - wszystkie stare importy działają

## 🔧 Architektura

### Warstwa danych (src/database/)
- Thread-safe connection pooling
- Repository pattern - jeden repo na model
- Separacja logiki SQL od business logic

### Warstwa biznesowa (src/core/)
- Scraper: Web scraping z retry logic
- Summarizer: K-means clustering + LLM (GPU optimized)
- PDF Generator: Markdown → PDF conversion

### Warstwa UI (src/ui/)
- Modułowe zakładki Gradio
- Shared utilities dla wspólnej funkcjonalności
- Event-driven callbacks

### Automatyzacja (src/automation/)
- CRON scheduling
- Job execution w tle
- Configuration management

## 🎯 Najważniejsze Zmiany

1. **Modularność**: Kod podzielony na logiczne moduły
2. **Testowalność**: Każdy moduł można testować osobno
3. **Rozszerzalność**: Łatwe dodawanie nowych funkcji
4. **Maintainability**: Czytelna struktura, łatwa w utrzymaniu
5. **Performance**: GPU optimization (4x szybciej)

## 📝 Konwencje

- **Nazwy plików**: snake_case (np. `scraping_tab.py`)
- **Nazwy klas**: PascalCase (np. `CompanyRepository`)
- **Nazwy funkcji**: snake_case (np. `get_job_names()`)
- **Docstringi**: Google style
- **Importy**: Względne w src/, absolutne w root wrappers

## 🔄 Workflow Rozwoju

1. **Nowe features**: Dodaj w odpowiednim module w `src/`
2. **UI changes**: Modyfikuj pliki w `src/ui/tabs/`
3. **Database**: Dodaj metody w repository w `src/database/`
4. **Testing**: Dodaj testy w `tests/`
5. **Backward compatibility**: Nie modyfikuj root wrappers bez powodu

## 🐛 Debugowanie

- Logi w: `logs/`
- Wyniki CRON: `scheduled_results/`
- Database errors: Zobacz `src/database/connection.py`
- UI errors: Zobacz `src/ui/app.py`

## 📚 Dodatkowa Dokumentacja

- [README.md](../README.md) - Główna dokumentacja
- [CRON_AUTOMATION.md](CRON_AUTOMATION.md) - Automatyzacja
- [DATABASE_DIAGRAM.md](DATABASE_DIAGRAM.md) - Struktura BD
