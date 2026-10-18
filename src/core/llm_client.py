"""LongCat LLM client — OpenAI-compatible API.

Uses the OpenAI SDK pointed at LongCat's endpoint.
API key configured via LONGCAT_API_KEY environment variable.

Usage:
    from core.llm_client import LongCatLLM, llm
    response = llm.complete("Summarize this incident response plan")
"""

import os
import json
from typing import Optional, Dict, Any, List

# Lazy import so the module loads even without the openai SDK installed
_openai = None


def _get_openai():
    """Lazy-load the openai module."""
    global _openai
    if _openai is None:
        try:
            import openai
            _openai = openai
        except ImportError:
            raise ImportError(
                "openai SDK not installed. Run: uv add openai"
            )
    return _openai


LONGCAT_BASE_URL = "https://api.longcat.ai/openai/v1"
LONGCAT_MODEL = "LongCat-2.5-Preview"


class LongCatLLM:
    """LongCat LLM client using the OpenAI-compatible SDK.

    Falls back gracefully if no API key is configured — all methods
    return None so the agent can degrade to keyword-based responses.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.environ.get("LONGCAT_API_KEY")
        self.model = model or os.environ.get("LONGCAT_MODEL", LONGCAT_MODEL)
        self._client = None

        if self.api_key:
            openai = _get_openai()
            self._client = openai.OpenAI(
                api_key=self.api_key,
                base_url=LONGCAT_BASE_URL,
            )

    @property
    def available(self) -> bool:
        """Whether the LLM client is configured and ready."""
        return self._client is not None

    def complete(
        self,
        prompt: str,
        system_prompt: str = "You are Company Brain, an AI assistant for enterprise operations.",
        max_tokens: int = 500,
        temperature: float = 0.3,
    ) -> Optional[str]:
        """Send a completion request to LongCat.

        Returns None if LLM is unavailable or on error.
        """
        if not self.available:
            return None

        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return response.choices[0].message.content
        except Exception as e:
            # Log but don't crash — agent falls back to keyword responses
            print(f"  ⚠️  LLM error: {e}")
            return None

    def classify_intent(self, query: str) -> Optional[str]:
        """Use LLM for intent classification (supplements keyword matching).

        Returns one of: incident_response, automation_assessment,
        process_extraction, cascade_analysis, compliance_check, general
        """
        if not self.available:
            return None

        prompt = (
            f"Classify this user query into exactly one intent category.\n"
            f"Respond with ONLY the category name, nothing else.\n\n"
            f"Categories:\n"
            f"- incident_response (security breaches, attacks, incidents)\n"
            f"- automation_assessment (what can be automated, RPA, feasibility)\n"
            f"- process_extraction (parsing SOPs, workflows, dependencies)\n"
            f"- cascade_analysis (blast radius, vendor impact, downstream effects)\n"
            f"- compliance_check (regulations, deadlines, GDPR, HIPAA, CCPA)\n"
            f"- general (anything else)\n\n"
            f"Query: {query}"
        )

        result = self.complete(prompt, max_tokens=20, temperature=0.0)
        if result:
            intent = result.strip().lower().split()[0]  # First word
            valid = {'incident_response', 'automation_assessment',
                     'process_extraction', 'cascade_analysis',
                     'compliance_check', 'general'}
            if intent in valid:
                return intent
        return None

    def summarize_response(self, context: str, data: Dict[str, Any]) -> Optional[str]:
        """Generate a natural-language summary of structured data."""
        if not self.available:
            return None

        prompt = (
            f"Given this context and structured data, write a concise 2-3 sentence summary.\n"
            f"Be factual. Only state what the data shows. Do not invent details.\n\n"
            f"Context: {context}\n\n"
            f"Data:\n{json.dumps(data, indent=2, default=str)}"
        )

        return self.complete(prompt, max_tokens=200, temperature=0.3)

    def extract_structured(self, query: str, schema: Dict[str, str]) -> Optional[Dict]:
        """Extract structured fields from a natural language query.

        Args:
            query: User's natural language input
            schema: Dict of field_name -> description
        """
        if not self.available:
            return None

        fields_desc = "\n".join(f"  {k}: {v}" for k, v in schema.items())
        prompt = (
            f"Extract the following fields from this query.\n"
            f"Respond with valid JSON only.\n\n"
            f"Fields:\n{fields_desc}\n\n"
            f"Query: {query}\n\n"
            f"JSON:"
        )

        result = self.complete(prompt, max_tokens=200, temperature=0.0)
        if result:
            try:
                # Try to parse JSON from the response
                text = result.strip()
                # Handle ```json ... ``` wrapping
                if text.startswith("```"):
                    text = text.split("```")[1]
                    if text.startswith("json"):
                        text = text[4:]
                    text = text.strip()
                return json.loads(text)
            except (json.JSONDecodeError, IndexError):
                return None
        return None


# Module-level singleton — imported elsewhere as `from core.llm_client import llm`
llm = LongCatLLM()
