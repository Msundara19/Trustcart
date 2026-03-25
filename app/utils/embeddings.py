# app/utils/embeddings.py

import re
from typing import List, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# Stop words that add noise without semantic meaning in product titles
_NOISE_WORDS = {
    "the", "a", "an", "and", "or", "for", "of", "in", "on", "at", "to",
    "with", "is", "it", "this", "new", "brand", "item", "product", "lot",
    "free", "shipping", "fast", "sale", "buy", "get", "best", "top",
}


_COLOR_SYNONYMS = {
    "grey": "gray",
    "colour": "color",
}

_UNIT_SPLIT = re.compile(r"(\d+)\s*(gb|tb|mb|mhz|ghz|mp|inch|in|ft|kg|lb|oz|mm|cm)", re.IGNORECASE)


def _preprocess(title: str) -> str:
    """
    Normalize a product title for embedding:
    - Lowercase + synonym normalization (grey→gray)
    - Split numeric-unit compounds: 256gb → 256 gb
    - Remove non-alphanumeric chars (keep spaces)
    - Collapse whitespace
    - Drop high-frequency noise words
    """
    title = title.lower()

    # Normalize synonyms before splitting
    for variant, canonical in _COLOR_SYNONYMS.items():
        title = title.replace(variant, canonical)

    # Split "256gb" → "256 gb" so both spellings match the same tokens
    title = _UNIT_SPLIT.sub(r"\1 \2", title)

    title = re.sub(r"[^a-z0-9\s]", " ", title)
    tokens = [t for t in title.split() if t not in _NOISE_WORDS and len(t) > 1]
    return " ".join(tokens)


class TitleEmbedder:
    """
    TF-IDF vectorizer wrapper for product title embeddings.

    Produces L2-normalized vectors so that dot product == cosine similarity.
    Fitted lazily on the first call to embed().
    """

    def __init__(
        self,
        ngram_range: Tuple[int, int] = (1, 2),
        max_features: int = 10_000,
        min_df: int = 1,
    ):
        self._vectorizer = TfidfVectorizer(
            ngram_range=ngram_range,
            max_features=max_features,
            min_df=min_df,
            sublinear_tf=True,   # apply 1 + log(tf) scaling
        )
        self._fitted = False

    def embed(self, titles: List[str]) -> np.ndarray:
        """
        Fit (if needed) and transform a list of titles into an (N, D) float32 matrix.
        Rows are L2-normalised, enabling cosine similarity via dot product.
        """
        processed = [_preprocess(t) for t in titles]

        if not self._fitted:
            matrix = self._vectorizer.fit_transform(processed)
            self._fitted = True
        else:
            matrix = self._vectorizer.transform(processed)

        # Convert sparse → dense, cast to float32 for efficiency
        dense = matrix.toarray().astype(np.float32)

        # L2-normalise each row
        norms = np.linalg.norm(dense, axis=1, keepdims=True)
        norms[norms == 0] = 1.0          # avoid divide-by-zero for empty titles
        return dense / norms

    def similarity_matrix(self, titles: List[str]) -> np.ndarray:
        """
        Return an (N, N) cosine similarity matrix for a list of titles.
        Diagonal is 1.0 (self-similarity).
        """
        embeddings = self.embed(titles)
        return cosine_similarity(embeddings).astype(np.float32)
