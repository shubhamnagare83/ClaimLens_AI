"""
ClaimLens AI — Policy RAG Retrieval Service
Embeds policy chunks and retrieves relevant clauses using FAISS/NumPy.
"""
import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional
from backend.config import POLICY_DIR, EMBEDDINGS_DIR
from backend.services import gemini_service

_policy_chunks = []
_embeddings = None
_chunk_index = []


def init_retrieval():
    """Load policy chunks and embeddings. Generate if not cached."""
    global _policy_chunks, _embeddings, _chunk_index

    EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)
    embeddings_path = EMBEDDINGS_DIR / "policy_embeddings.npy"
    index_path = EMBEDDINGS_DIR / "policy_index.json"

    # Load policy chunks
    _policy_chunks = _create_policy_chunks()

    if embeddings_path.exists() and index_path.exists():
        try:
            _embeddings = np.load(str(embeddings_path))
            with open(index_path, 'r') as f:
                _chunk_index = json.load(f)
            if len(_chunk_index) == len(_policy_chunks):
                print("  [OK] Policy embeddings loaded from cache")
                return True
        except Exception as e:
            print(f"  [!] Error loading cached embeddings: {e}")

    # Generate embeddings
    if gemini_service.is_available():
        texts = [c['text'] for c in _policy_chunks]
        emb = gemini_service.generate_embeddings(texts)
        if emb:
            _embeddings = np.array(emb)
            _chunk_index = [{'chunk_id': c['chunk_id'], 'clause_id': c['clause_id'],
                            'category': c['category']} for c in _policy_chunks]
            np.save(str(embeddings_path), _embeddings)
            with open(index_path, 'w') as f:
                json.dump(_chunk_index, f)
            print("  [OK] Policy embeddings generated and cached")
            return True

    print("  [!] Running without embeddings — using keyword matching fallback")
    return False


def _create_policy_chunks() -> List[Dict]:
    """Create chunked policy data for embedding."""
    policy_path = POLICY_DIR / "motor_policy.json"
    if not policy_path.exists():
        return []

    with open(policy_path, 'r') as f:
        policy = json.load(f)

    chunks = []
    for clause in policy.get('clauses', []):
        chunk = {
            'chunk_id': f"{clause['clause_id']}-001",
            'clause_id': clause['clause_id'],
            'title': clause['title'],
            'category': clause['category'],
            'text': f"{clause['clause_id']} — {clause['title']}: {clause['rule']}",
            'rule': clause['rule'],
            'conditions': clause.get('conditions', []),
            'exceptions': clause.get('exceptions', []),
            'required_evidence': clause.get('required_evidence', []),
        }
        chunks.append(chunk)
    return chunks


def retrieve_relevant_clauses(query: str, top_k: int = 10, category: str = None) -> List[Dict]:
    """Retrieve most relevant policy clauses for a query."""
    if _embeddings is not None and gemini_service.is_available():
        return _retrieve_with_embeddings(query, top_k, category)
    return _retrieve_with_keywords(query, top_k, category)


def _retrieve_with_embeddings(query: str, top_k: int, category: str = None) -> List[Dict]:
    """Semantic retrieval using embeddings."""
    query_emb = gemini_service.generate_embeddings([query])
    if not query_emb:
        return _retrieve_with_keywords(query, top_k, category)

    query_vec = np.array(query_emb[0])
    # Cosine similarity
    norms = np.linalg.norm(_embeddings, axis=1) * np.linalg.norm(query_vec)
    norms = np.where(norms == 0, 1, norms)
    similarities = np.dot(_embeddings, query_vec) / norms

    # Filter by category if specified
    indices = np.argsort(similarities)[::-1]

    results = []
    for idx in indices:
        if len(results) >= top_k:
            break
        chunk = _policy_chunks[idx]
        if category and chunk['category'] != category:
            continue
        results.append({
            **chunk,
            'relevance_score': float(similarities[idx])
        })

    return results


def _retrieve_with_keywords(query: str, top_k: int, category: str = None) -> List[Dict]:
    """Keyword-based fallback retrieval."""
    query_lower = query.lower()
    query_words = set(query_lower.split())

    scored = []
    for chunk in _policy_chunks:
        if category and chunk['category'] != category:
            continue
        text_lower = chunk['text'].lower()
        text_words = set(text_lower.split())
        overlap = len(query_words & text_words)
        if overlap > 0:
            score = overlap / max(len(query_words), 1)
            scored.append({**chunk, 'relevance_score': score})

    scored.sort(key=lambda x: x['relevance_score'], reverse=True)
    return scored[:top_k]


def get_clause_by_id(clause_id: str) -> Optional[Dict]:
    """Get a specific policy clause by ID."""
    for chunk in _policy_chunks:
        if chunk['clause_id'] == clause_id:
            return chunk
    return None


def get_all_clauses() -> List[Dict]:
    """Get all policy clauses."""
    return _policy_chunks


def get_clauses_by_category(category: str) -> List[Dict]:
    """Get clauses filtered by category."""
    return [c for c in _policy_chunks if c['category'] == category]
