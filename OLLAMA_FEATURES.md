# Nowe funkcje - Zarządzanie modelami Ollama

## Co zostało dodane?

### 1. Moduł `ollama_manager.py`
Nowy moduł zarządzania modelami Ollama z następującymi funkcjami:

- `is_ollama_available()` - sprawdza, czy Ollama jest zainstalowane
- `get_installed_models()` - zwraca listę zainstalowanych modeli
- `is_model_installed(model_name)` - sprawdza, czy konkretny model jest zainstalowany
- `pull_model(model_name, progress_callback)` - pobiera model z obsługą callbacku postępu
- `get_available_models()` - lista rekomendowanych modeli do streszczania (< 10GB)
- `get_model_display_name(model_name, is_installed)` - formatuje nazwę dla UI

### 2. Rozszerzone UI (`user_interface.py`)
Do interfejsu Gradio dodano:

- **Dropdown wyboru modelu** z oznaczeniami:
  - ✓ = model zainstalowany
  - ○ = model do pobrania
- **Przycisk odświeżania** (🔄) - aktualizuje listę modeli po ręcznym zainstalowaniu
- **Automatyczne pobieranie** - jeśli wybrany model nie jest zainstalowany, UI automatycznie go pobierze przed rozpoczęciem scrapingu
- **Postęp pobierania** - wyświetlanie informacji o postępie pobierania modelu

### 3. Zmodyfikowane moduły
- `summary.py` - funkcja `summarize_document_with_kmeans_clustering()` przyjmuje teraz parametr `model_name`
- `scrape_script.py` - funkcje `get_summaries()` i `scrape()` przyjmują parametr `model_name`

## Rekomendowane modele (< 10GB)

Skonfigurowane w `ollama_manager.py`:

1. **llama3.2:latest** (~6GB) - doskonały do streszczania, dobry balans wydajność/rozmiar
2. **llama3.2:3b** (~2GB) - mniejszy wariant
3. **mistral:latest** (~4GB) - dobry kompromis
4. **phi3:latest** (~2.3GB) - efektywny model Microsoft
5. **gemma:7b** (~5GB) - model Google
6. **qwen2:7b** (~4.4GB) - model Alibaba

## Jak używać?

### W interfejsie graficznym:
1. Uruchom aplikację: `python user_interface.py`
2. W sekcji z parametrami znajdziesz dropdown "Ollama Model"
3. Wybierz model z listy:
   - Jeśli ma ✓ - jest gotowy do użycia
   - Jeśli ma ○ - zostanie automatycznie pobrany przy kliknięciu "Run"
4. Kliknij przycisk 🔄 aby odświeżyć listę modeli (np. po ręcznej instalacji)

### Automatyczne pobieranie:
Gdy wybierzesz model niepobrany i klikniesz "Run":
1. UI wyświetli komunikat o rozpoczęciu pobierania
2. Pobieranie postępu będzie widoczne w sekcji "Output"
3. Po zakończeniu pobierania automatycznie rozpocznie się scraping

### Programowo (Python):
```python
from ollama_manager import pull_model, is_model_installed

# Sprawdź, czy model jest zainstalowany
if not is_model_installed("llama3.2:latest"):
    success, message = pull_model("llama3.2:latest")
    print(message)

# Użyj modelu w streszczaniu
from summary import summarize_document_with_kmeans_clustering
summary = summarize_document_with_kmeans_clustering("path/to/file.pdf", "llama3.2:latest")
```

## Uwagi techniczne

- Pobieranie modelu może zająć kilka minut w zależności od rozmiaru i prędkości internetu
- UI używa generatora (yield) do pokazywania postępu pobierania bez blokowania interfejsu
- Funkcja `run_scrape_ui()` najpierw sprawdza dostępność modelu, pobiera go jeśli trzeba, a potem uruchamia scraping
- Parametr `num_predict` zastąpił `max_tokens` dla zgodności z najnowszym API ChatOllama

## Testowanie

Sprawdź dostępność Ollama:
```bash
ollama --version
```

Lista zainstalowanych modeli:
```bash
ollama list
```

Ręczne pobieranie modelu:
```bash
ollama pull llama3.2:latest
```
