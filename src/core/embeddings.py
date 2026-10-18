"""Embedding generation for Company Brain using FastEmbed.

FastEmbed uses ONNX Runtime internally — no torch/transformers needed.
Default model: BAAI/bge-small-en-v1.5 (384-dim, good quality, ~90MB).
"""

from typing import List, Optional

# Lazy import — only loaded when needed
_model = None


def get_model(model_name: str = 'BAAI/bge-small-en-v1.5'):
    """Get or create the embedding model (lazy loading)."""
    global _model
    if _model is None:
        from fastembed import TextEmbedding
        _model = TextEmbedding(model_name=model_name)
    return _model


def embed_text(text: str, model_name: str = 'BAAI/bge-small-en-v1.5') -> List[float]:
    """Generate a 384-dim embedding for a single text string."""
    model = get_model(model_name)
    embeddings = list(model.embed([text]))
    return [float(x) for x in embeddings[0]]


def embed_texts(texts: List[str], model_name: str = 'BAAI/bge-small-en-v1.5') -> List[List[float]]:
    """Generate embeddings for multiple texts."""
    model = get_model(model_name)
    embeddings = list(model.embed(texts))
    return [[float(x) for x in emb] for emb in embeddings]


def embed_task(task: dict) -> List[float]:
    """Generate embedding for a task node."""
    text = f"{task.get('name', '')}. {task.get('description', '')}"
    return embed_text(text)


def embed_document(doc: dict) -> List[float]:
    """Generate embedding for a document node."""
    text = f"{doc.get('title', '')}. {doc.get('type', '')}"
    return embed_text(text)


def embed_person(person: dict) -> List[float]:
    """Generate embedding for a person node."""
    text = f"{person.get('name', '')}. {person.get('role', '')} in {person.get('department', '')}"
    return embed_text(text)


def embed_incident(incident: dict) -> List[float]:
    """Generate embedding for an incident node."""
    text = f"{incident.get('type', '')} incident. Severity: {incident.get('severity', '')}. Status: {incident.get('status', '')}"
    return embed_text(text)


def embed_regulation(reg: dict) -> List[float]:
    """Generate embedding for a regulation node."""
    text = f"{reg.get('name', '')}. {reg.get('jurisdiction', '')}. {reg.get('citation', '')}"
    return embed_text(text)


def get_dimension() -> int:
    """Return the embedding dimension (384 for bge-small-en-v1.5)."""
    return 384
