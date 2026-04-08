#!/usr/bin/env python3
"""Download the mxbai-edge-colbert-v0-17m model from HuggingFace.

Saves to ./models/ so it's available for the gateway without
downloading at runtime.

Usage:
    python download_model.py
    # or: pip install huggingface_hub && python download_model.py
"""

from pathlib import Path

MODEL_NAME = "mixedbread-ai/mxbai-edge-colbert-v0-17m"
MODEL_DIR = Path(__file__).parent / "models"


def main():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print("Installing huggingface_hub...")
        import subprocess
        import sys

        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "huggingface_hub"]
        )
        from huggingface_hub import snapshot_download

    print(f"Downloading {MODEL_NAME} to {MODEL_DIR}...")
    path = snapshot_download(
        repo_id=MODEL_NAME,
        cache_dir=str(MODEL_DIR),
    )
    print(f"Model downloaded to: {path}")
    print("Done.")


if __name__ == "__main__":
    main()
