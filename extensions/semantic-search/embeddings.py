"""MiniLM embedding model for semantic search."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"
MODEL_DIR = Path(__file__).parent / "models"

_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        _model = SentenceTransformer(MODEL_NAME, cache_folder=str(MODEL_DIR))
    return _model


def encode(texts: list[str], show_progress: bool = False) -> np.ndarray:
    model = get_model()
    return model.encode(
        texts,
        batch_size=64,
        show_progress_bar=show_progress,
        normalize_embeddings=True,
    )


def content_to_text(item: dict[str, Any]) -> str:
    parts = []

    if item.get("title"):
        parts.append(f"title: {item['title']}")
    if item.get("name"):
        parts.append(f"name: {item['name']}")
    if item.get("description"):
        parts.append(f"description: {item['description']}")
    if item.get("app_mode"):
        parts.append(f"type: {item['app_mode']}")

    owner = item.get("owner")
    if owner:
        name = f"{owner.get('first_name', '')} {owner.get('last_name', '')}".strip()
        if name:
            parts.append(f"author: {name}")
        if owner.get("username"):
            parts.append(f"owner: {owner['username']}")

    tags = item.get("tags")
    if tags:
        tag_names = [t.get("name", "") for t in tags if t.get("name")]
        if tag_names:
            parts.append(f"tags: {', '.join(tag_names)}")

    if item.get("r_version"):
        parts.append(f"r_version: {item['r_version']}")
    if item.get("py_version"):
        parts.append(f"python_version: {item['py_version']}")
    if item.get("quarto_version"):
        parts.append(f"quarto_version: {item['quarto_version']}")

    return "\n".join(parts)
