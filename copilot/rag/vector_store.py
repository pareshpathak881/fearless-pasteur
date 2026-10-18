"""Hybrid Vector Store and Entitlement-Aware Retriever for Project Atlas.

Implements dense-sparse hybrid search with re-ranking, metadata filtering,
and strict client entitlement isolation.
"""

import os
import json
import re
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from copilot.rag.chunker import DocumentChunk, ReportChunker


class HybridVectorStore:
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path or os.path.join(
            os.path.dirname(__file__), "..", "..", "data", "vector_store.json"
        )
        self.chunks: List[DocumentChunk] = []
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.tfidf_matrix: Optional[np.ndarray] = None
        self._load_if_exists()

    def _load_if_exists(self):
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.chunks = [DocumentChunk(**item) for item in data]
                self._rebuild_index()
            except Exception as e:
                print(f"[VectorStore] Warning: Failed to load existing index: {e}")

    def ingest_reports_directory(self, reports_dir: str) -> int:
        """Parse all markdown reports in directory, chunk them, and build the index."""
        chunker = ReportChunker()
        all_chunks: List[DocumentChunk] = []

        if not os.path.exists(reports_dir):
            raise FileNotFoundError(f"Reports directory not found: {reports_dir}")

        for fname in sorted(os.listdir(reports_dir)):
            if fname.endswith(".md"):
                fpath = os.path.join(reports_dir, fname)
                chunks = chunker.parse_report_file(fpath)
                all_chunks.extend(chunks)

        self.chunks = all_chunks
        self._rebuild_index()
        self.save()
        return len(self.chunks)

    def _rebuild_index(self):
        if not self.chunks:
            return

        corpus = [f"{c.report_title} {c.sector} {c.region} {c.content}" for c in self.chunks]
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            sublinear_tf=True,
            stop_words="english",
            max_features=5000
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(corpus)

    def save(self):
        os.makedirs(os.path.dirname(os.path.abspath(self.storage_path)), exist_ok=True)
        serializable = [c.to_dict() for c in self.chunks]
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(serializable, f, indent=2)

    def _keyword_score(self, query: str, content: str) -> float:
        """Compute keyword lexical match score with emphasis on numbers and acronyms."""
        tokens = re.findall(r"\b[A-Za-z0-9\-\.]+\b", query.lower())
        if not tokens:
            return 0.0
        
        content_lower = content.lower()
        score = 0.0
        for t in tokens:
            if len(t) < 3 and not t.isdigit():
                continue
            if t in content_lower:
                # Higher weight for numbers/acronyms like '2030', 'apac', 'cagr', 'r-101'
                if t.isdigit() or t in ["apac", "cagr", "ami", "amr", "r-101", "r-102", "r-103"]:
                    score += 2.0
                else:
                    score += 1.0
        return min(1.0, score / (len(tokens) + 1e-5))

    def search_entitled(
        self,
        query: str,
        allowed_report_ids: List[str],
        top_k: int = 5,
        min_score: float = 0.05
    ) -> List[Tuple[DocumentChunk, float]]:
        """Search vector index strictly filtering by client's allowed report IDs BEFORE ranking.
        
        Guarantees that unpurchased report content is NEVER included in LLM context.
        """
        if not self.chunks or self.vectorizer is None or self.tfidf_matrix is None:
            return []

        # 1. ENTITLEMENT FILTERING: Filter candidate indices strictly first
        allowed_set = set(allowed_report_ids)
        candidate_indices = [
            i for i, c in enumerate(self.chunks) if c.report_id in allowed_set
        ]

        if not candidate_indices:
            return []

        # 2. Vector Cosine Similarity
        query_vec = self.vectorizer.transform([query])
        sub_matrix = self.tfidf_matrix[candidate_indices]
        cos_sims = cosine_similarity(query_vec, sub_matrix)[0]

        # 3. Hybrid Re-Ranking
        ranked_results: List[Tuple[DocumentChunk, float]] = []
        for local_idx, orig_idx in enumerate(candidate_indices):
            c_score = float(cos_sims[local_idx])
            k_score = self._keyword_score(query, self.chunks[orig_idx].content)
            # Re-ranker formula: 65% vector similarity + 35% lexical keyword boost
            hybrid_score = (0.65 * c_score) + (0.35 * k_score)
            
            if hybrid_score >= min_score or k_score > 0.3:
                ranked_results.append((self.chunks[orig_idx], hybrid_score))

        # Sort descending by hybrid score
        ranked_results.sort(key=lambda x: x[1], reverse=True)
        return ranked_results[:top_k]

    def check_unowned_reports(
        self,
        query: str,
        allowed_report_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """Identify if relevant reports exist in the catalog that the client has NOT purchased.
        
        Returns high-level metadata (Report ID, Title, Publisher, Sector) for upgrade path,
        without revealing ANY confidential numerical data or chunk content!
        """
        if not self.chunks or self.vectorizer is None or self.tfidf_matrix is None:
            return []

        allowed_set = set(allowed_report_ids)
        unowned_indices = [
            i for i, c in enumerate(self.chunks) if c.report_id not in allowed_set
        ]

        if not unowned_indices:
            return []

        query_vec = self.vectorizer.transform([query])
        sub_matrix = self.tfidf_matrix[unowned_indices]
        cos_sims = cosine_similarity(query_vec, sub_matrix)[0]

        unowned_matches = {}
        for local_idx, orig_idx in enumerate(unowned_indices):
            score = float(cos_sims[local_idx])
            chunk = self.chunks[orig_idx]
            k_score = self._keyword_score(query, chunk.content)
            hybrid_score = (0.65 * score) + (0.35 * k_score)

            # If there is a strong match to an unowned report (e.g. asking for smart water meter or R-101)
            if hybrid_score > 0.15 or chunk.report_id.lower() in query.lower():
                if chunk.report_id not in unowned_matches:
                    unowned_matches[chunk.report_id] = {
                        "report_id": chunk.report_id,
                        "title": chunk.report_title,
                        "publisher": chunk.publisher,
                        "sector": chunk.sector,
                        "year": chunk.year,
                        "score": hybrid_score
                    }
                else:
                    unowned_matches[chunk.report_id]["score"] = max(
                        unowned_matches[chunk.report_id]["score"], hybrid_score
                    )

        # Return sorted by score
        return sorted(list(unowned_matches.values()), key=lambda x: x["score"], reverse=True)


vector_store = HybridVectorStore()
