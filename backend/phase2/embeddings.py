import os
import logging

os.environ.setdefault("TRANSFORMERS_OFFLINE", "0")
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

from sentence_transformers import SentenceTransformer

_model = None


def get_model():
    global _model
    if _model is None:
        logging.info("Loading embedding model (paraphrase-multilingual-MiniLM-L12-v2, ~120MB)...")
        try:
            _model = SentenceTransformer(
                "paraphrase-multilingual-MiniLM-L12-v2",
                device="cpu",
            )
        except Exception:
            logging.warning("Network unavailable, falling back to local cache")
            _model = SentenceTransformer(
                "paraphrase-multilingual-MiniLM-L12-v2",
                device="cpu",
                local_files_only=True,
            )
        logging.info("Embedding model loaded successfully")
    return _model


def encode(texts: list[str]) -> list[list[float]]:
    model = get_model()
    return model.encode(texts, normalize_embeddings=True).tolist()
