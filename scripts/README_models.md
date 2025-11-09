# Recommended Ollama models for summarization

This folder contains helper scripts to install Ollama and pull recommended models.

Recommended small-to-medium models (<= 10GB) suitable for summarization:

- llama3.2:latest (approx 6GB) — Llama 3 is strong at general language tasks and summarization, good balance between performance and size.
- alpaca-7b (approx 4GB) — lightweight, good for short summaries and quick iterations.
- vicuna-7b (approx 4GB) — fine-tuned for chat-like tasks and instruction following, useful for concise summaries.
- gpt-neo-2.7b (approx 2GB) — small footprint, reasonable text generation capabilities.

How to use:

1. Install Ollama (see `install_ollama.sh`).
2. Verify `ollama --version` works.
3. Edit `models_to_pull.txt` if you want different models.
4. Run `download_models.sh` to pull models.

Notes:
- Model size estimates are approximate; always check actual sizes returned by your Ollama registry.
- Some model names used above are placeholders and may differ in your local Ollama index or provider.
- This repository does not bundle any model weights.
