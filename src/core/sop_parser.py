"""SOP Parser — rule-based extraction of tasks and dependencies from SOP text.

This is a deterministic, transparent extractor (no LLM needed for the demo).
It parses numbered-step SOP documents and "After X, Y" dependency patterns,
then feeds the results into the graph validation pipeline.

For the hackathon, this replaces hardcoded extraction data with real parsing.
In production, this would be augmented with GraphRAG SDK + LLM extraction.
"""

import re
import math
from typing import List, Dict, Tuple, Optional


def _normalize_word(word: str) -> str:
    """Simple normalization: lowercase, strip punctuation, remove common suffixes."""
    w = word.lower().strip()
    # Remove leading/trailing non-alphanumeric characters
    w = re.sub(r'^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$', '', w)
    if not w:
        return ''
    # Remove common suffixes for fuzzy matching (order matters: longest first)
    for suffix in ['ation', 'ment', 'ing', 'ed', 'es', 's']:
        if w.endswith(suffix) and len(w) > len(suffix) + 2:
            w = w[:-len(suffix)]
            break
    return w


_STOP_WORDS = {
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'is', 'are', 'be', 'it', 'its', 'this', 'that', 'before',
    'after', 'from', 'by', 'as', 'if', 'then', 'so', 'do', 'did', 'does',
    'have', 'has', 'had', 'was', 'were', 'been', 'being', 'will', 'would',
    'could', 'should', 'may', 'might', 'shall', 'can', 'all', 'each',
    'every', 'both', 'few', 'more', 'most', 'other', 'some', 'such', 'no',
    'not', 'only', 'own', 'same', 'than', 'too', 'very', 'just', 'also',
    'via', 'email', 'complete',
}


def _tokenize(text: str) -> List[str]:
    """Tokenize text into normalized words, excluding stop words."""
    words = re.split(r'[\s\-/]+', text.lower())
    return [w for w in (_normalize_word(w) for w in words) if w and w not in _STOP_WORDS]


def _compute_idf(tasks: List[dict]) -> Dict[str, float]:
    """Compute IDF for each word across task names.

    Words appearing in many tasks get low weight (not discriminative).
    Words appearing in few tasks get high weight (discriminative).
    """
    n = len(tasks)
    word_doc_count: Dict[str, int] = {}
    for task in tasks:
        words = set(_tokenize(task['name']))
        for w in words:
            word_doc_count[w] = word_doc_count.get(w, 0) + 1

    idf = {}
    for w, count in word_doc_count.items():
        idf[w] = math.log(n / count) + 1.0  # smoothed IDF
    return idf


def _words_match(w1: str, w2: str) -> bool:
    """Check if two words match, allowing prefix overlap for stems.

    Handles cases like 'verif' (from 'verification') matching 'verify'.
    """
    if w1 == w2:
        return True
    # Check prefix overlap (at least 4 chars, and the shorter is prefix of longer)
    min_len = min(len(w1), len(w2))
    if min_len >= 4 and w1[:4] == w2[:4]:
        return True
    return False


def _match_score(phrase: str, task_name: str, idf: Dict[str, float]) -> float:
    """Score how well a phrase matches a task name using IDF-weighted word overlap.

    Uses TF-IDF: discriminative words (low doc frequency) contribute more.
    Allows prefix matching for stemmed words (e.g., 'verif' matches 'verify').
    """
    phrase_words = set(_tokenize(phrase))
    name_words = set(_tokenize(task_name))
    if not name_words:
        return 0.0

    # IDF-weighted overlap: for each phrase word, find best-matching name word
    overlap_score = 0.0
    for pw in phrase_words:
        for nw in name_words:
            if _words_match(pw, nw):
                overlap_score += idf.get(nw, 1.0)
                break  # each phrase word matches at most one name word

    # Normalize by the total possible score for the task name
    max_score = sum(idf.get(w, 1.0) for w in name_words)
    if max_score == 0:
        return 0.0
    return overlap_score / max_score


def parse_sop_tasks(sop_text: str) -> List[dict]:
    """Parse numbered steps from SOP text into task dicts.

    Looks for lines like "1. Do something" or "2) Another step".
    Assigns sequential task IDs (task_1, task_2, ...).
    """
    tasks = []
    for line in sop_text.strip().split('\n'):
        line = line.strip()
        m = re.match(r'^(\d+)[.)]\s+(.+)', line)
        if m:
            name = m.group(2).strip()
            # Clean up trailing punctuation
            name = re.sub(r'[.,;:]+$', '', name).strip()
            tasks.append({
                'task_id': f'task_{len(tasks) + 1}',
                'name': name,
                'time_per_exec_hours': 0.25,  # default estimate
            })
    return tasks


def parse_sop_dependencies(sop_text: str, tasks: List[dict]) -> List[dict]:
    """Parse "After X, Y" patterns into dependency edges.

    Pattern: "After [prerequisite phrase], [dependent phrase]"
    Matches phrases to tasks using IDF-weighted word-overlap scoring.

    Convention: {'from': dependent_task_id, 'to': prerequisite_task_id}
    Meaning: dependent depends on prerequisite (prerequisite must complete first).
    """
    deps = []
    if not tasks:
        return deps

    # Pre-compute IDF weights for discriminative matching
    idf = _compute_idf(tasks)

    # Find all "After X, Y" sentences
    pattern = r'[Aa]fter\s+(.+?)[,.]\s+(.+)'
    for match in re.finditer(pattern, sop_text):
        prereq_phrase = match.group(1).strip()
        dependent_phrase = match.group(2).strip()

        # Find best-matching tasks
        prereq_id = _find_best_task(prereq_phrase, tasks, idf)
        dependent_id = _find_best_task(dependent_phrase, tasks, idf)

        if prereq_id and dependent_id and prereq_id != dependent_id:
            deps.append({
                'from': dependent_id,
                'to': prereq_id,
                'source_quote': match.group(0).strip(),
                'confidence': 0.8,
                'extraction_method': 'rule_based',
            })

    return deps


def _find_best_task(phrase: str, tasks: List[dict], idf: Dict[str, float]) -> Optional[str]:
    """Find the task ID that best matches the given phrase."""
    best_score = 0.0
    best_id = None
    for task in tasks:
        score = _match_score(phrase, task['name'], idf)
        if score > best_score:
            best_score = score
            best_id = task['task_id']
    # Only return if we have at least some match
    return best_id if best_score >= 0.15 else None


def parse_sop_document(sop_text: str) -> Tuple[List[dict], List[dict]]:
    """Parse an SOP document: extract tasks and dependencies.

    Returns: (tasks, dependencies)
    tasks: list of {'task_id', 'name', 'time_per_exec_hours'}
    dependencies: list of {'from', 'to', 'source_quote', 'confidence', 'extraction_method'}
    """
    tasks = parse_sop_tasks(sop_text)
    deps = parse_sop_dependencies(sop_text, tasks)
    return tasks, deps
