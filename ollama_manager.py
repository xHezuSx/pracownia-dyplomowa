"""
ollama_manager.py
Helper module for managing Ollama models: listing, checking if installed, and pulling.
"""
import subprocess
import shutil
from typing import List, Tuple, Optional
import re


def is_ollama_available() -> bool:
    """Check if ollama CLI is available in PATH."""
    return shutil.which("ollama") is not None


def get_installed_models() -> List[str]:
    """
    Get list of currently installed Ollama models.
    Returns list of model names (e.g., ['llama3.2:latest', 'mistral:latest']).
    """
    if not is_ollama_available():
        return []
    
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=10,
            check=True
        )
        
        # Parse output - typically format is:
        # NAME                    ID              SIZE      MODIFIED
        # llama3.2:latest        abc123          4.7 GB    2 days ago
        
        models = []
        for line in result.stdout.strip().split('\n')[1:]:  # Skip header
            if line.strip():
                # Extract first column (model name)
                parts = line.split()
                if parts:
                    models.append(parts[0])
        
        return models
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, Exception) as e:
        print(f"Error getting installed models: {e}")
        return []


def is_model_installed(model_name: str) -> bool:
    """Check if a specific model is installed."""
    installed = get_installed_models()
    return model_name in installed


def pull_model(model_name: str, progress_callback=None) -> Tuple[bool, str]:
    """
    Pull (download) an Ollama model.
    
    Args:
        model_name: Name of the model to pull (e.g., 'llama3.2:latest')
        progress_callback: Optional function to call with progress updates (str)
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    if not is_ollama_available():
        return False, "Ollama nie jest zainstalowane lub niedostępne w PATH"
    
    try:
        # Use Popen for streaming output
        proc = subprocess.Popen(
            ["ollama", "pull", model_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        output_lines = []
        if proc.stdout is None:
            return False, "Nie można przechwycić wyjścia procesu"
        
        for line in proc.stdout:
            line = line.strip()
            output_lines.append(line)
            if progress_callback:
                progress_callback(line)
        
        return_code = proc.wait()
        
        if return_code == 0:
            return True, f"Model {model_name} został pomyślnie pobrany"
        else:
            return False, f"Błąd pobierania modelu (kod {return_code}):\n" + "\n".join(output_lines[-10:])
            
    except Exception as e:
        return False, f"Błąd podczas pobierania modelu: {str(e)}"


# Recommended models for summarization (< 10GB)
RECOMMENDED_MODELS = [
    "llama3.2:latest",      # ~6GB, excellent for summarization
    "llama3.2:3b",          # ~2GB, smaller variant
    "mistral:latest",       # ~4GB, good balance
    "phi3:latest",          # ~2.3GB, Microsoft's efficient model
    "gemma:7b",             # ~5GB, Google's model
    "qwen2:7b",             # ~4.4GB, Alibaba's model
]


def get_available_models() -> List[str]:
    """
    Get list of recommended models, with installed ones marked.
    Returns list of model names.
    """
    return RECOMMENDED_MODELS.copy()


def get_model_display_name(model_name: str, is_installed: bool) -> str:
    """Format model name for display in UI."""
    if is_installed:
        return f"✓ {model_name} (zainstalowany)"
    else:
        return f"○ {model_name} (do pobrania)"
