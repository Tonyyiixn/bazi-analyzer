"""Lightweight keyword retrieval over the curated Bazi principles library.

Uses TF-IDF instead of embeddings - the corpus is a handful of short
markdown files, and Bazi terminology (Ten God names, element names) is
consistent vocabulary, so exact/keyword matching does the job without
pulling in a heavyweight embedding model. Revisit if the corpus grows large
enough that paraphrased queries start missing relevant docs.
"""
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

PRINCIPLES_DIR = Path(__file__).resolve().parent / "knowledge" / "principles"


class PrincipleIndex:
    def __init__(self, directory: Path = PRINCIPLES_DIR):
        self._paths = sorted(directory.glob("*.md"))
        self._docs = [p.read_text(encoding="utf-8") for p in self._paths]
        self._vectorizer = TfidfVectorizer(stop_words="english")
        self._matrix = self._vectorizer.fit_transform(self._docs) if self._docs else None

    def search(self, query: str, k: int = 3) -> list[dict]:
        if not self._docs:
            return []
        query_vec = self._vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self._matrix)[0]
        ranked = scores.argsort()[::-1][:k]
        return [
            {"topic": self._paths[i].stem, "content": self._docs[i]}
            for i in ranked
            if scores[i] > 0
        ]


_index: PrincipleIndex | None = None


def get_index() -> PrincipleIndex:
    global _index
    if _index is None:
        _index = PrincipleIndex()
    return _index
