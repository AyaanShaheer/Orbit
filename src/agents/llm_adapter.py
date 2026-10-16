import logging
import os
import json
from typing import Dict, Any, Optional
from src.config import settings

logger = logging.getLogger("orbit.llm")

class LLMAdapter:
    """
    Unified LLM adapter for ORBIT.
    Defaults to deterministic mock mode for zero latency, zero cost, and 100% reproducible testing.
    Can seamlessly connect to OpenAI or Google Gemini if keys are provided.
    """
    def __init__(self):
        self.provider = settings.llm_provider
        self.use_mock = settings.use_mock_llm

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        """Generate a response using configured provider or mock fixtures."""
        if self.use_mock or self.provider == "mock":
            return self._mock_generate(prompt, system_prompt)

        # Real model invocation if enabled
        if self.provider == "openai" and settings.openai_api_key:
            return self._call_openai(prompt, system_prompt)
        elif self.provider == "gemini" and settings.gemini_api_key:
            return self._call_gemini(prompt, system_prompt)
        else:
            return self._mock_generate(prompt, system_prompt)

    def _mock_generate(self, prompt: str, system_prompt: str) -> str:
        """Deterministic mock responses for incident triage."""
        prompt_lower = prompt.lower()
        if "reconcile" in prompt_lower or "coordinator" in prompt_lower:
            return json.dumps({
                "selected_hypothesis": "Cache connection saturation check required before any recovery action",
                "rejected_hypotheses": ["Blind cache reboot", "Ignoring configuration shift"],
                "recommendation": "Execute read-only connection saturation inspection (PROC-INSPECT-POOL) before attempting recovery.",
                "rationale": "Historical incident INC-2026-0901 proved that restarting cache while connections are saturated triggers database stampede. Furthermore, systems agent verified checkout service was upgraded to Redis Cluster v2.4, so standalone restart procedures are invalid."
            })
        return "Deterministic analysis based on authoritative graph facts."

    def _call_openai(self, prompt: str, system_prompt: str) -> str:
        try:
            import httpx
            headers = {
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1
            }
            res = httpx.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=30.0)
            data = res.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning(f"OpenAI call failed, falling back to mock: {e}")
            return self._mock_generate(prompt, system_prompt)

    def _call_gemini(self, prompt: str, system_prompt: str) -> str:
        try:
            import httpx
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.gemini_api_key}"
            payload = {
                "contents": [{"parts": [{"text": f"{system_prompt}\n\n{prompt}"}]}]
            }
            res = httpx.post(url, json=payload, timeout=30.0)
            data = res.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            logger.warning(f"Gemini call failed, falling back to mock: {e}")
            return self._mock_generate(prompt, system_prompt)

llm_adapter = LLMAdapter()
