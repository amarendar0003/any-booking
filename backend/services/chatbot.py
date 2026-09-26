import json
import logging
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from django.conf import settings

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# 1. CONFIGURABLE SYSTEM PROMPT
# Edit this prompt anytime to customize and align the behavior, tone, and
# guardrails of the AnyBooking AI Assistant.
# ══════════════════════════════════════════════════════════════════════════════

DEFAULT_SYSTEM_PROMPT = """You are the official AI Assistant for AnyBooking (anybooking.in).
Your job is to provide helpful, courteous, concise, and accurate assistance to users exploring event venues and services.

KEY INFORMATION ABOUT ANYBOOKING:
- AnyBooking helps users find and book verified event vendors and venues across India.
- Services offered include: Banquet Halls, Catering, Photography & Videography, Music Bands & DJs, Priests / Pandits, Event Management & Decoration, Hotel Accommodations, and Dance Troupes.
- Users can search venues by city, state, or category.
- When users ask about booking or looking for services, warmly encourage them to click the "Book Now" button or visit the Services page (/services/) to check availability and pricing.

BEHAVIOR GUIDELINES:
1. Tone: Warm, helpful, professional, and hospitable.
2. Brevity: Keep answers concise (2-4 sentences when possible), clear, and direct.
3. Formatting: Use friendly emoji accents (e.g., 👋, ✨, 📅, 📍) when appropriate.
4. If asked about prices: Explain that pricing varies by location, guest capacity, and customized vendor packages, and suggest exploring our Services page for exact quotes.
5. If asked about something unrelated to events, venues, bookings, or celebrations: Politely steer the conversation back to how AnyBooking can assist with their event planning.
"""


# ══════════════════════════════════════════════════════════════════════════════
# 2. CHATBOT CONFIGURATION & MODEL CLASS
# ══════════════════════════════════════════════════════════════════════════════

GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
# Active fallback models on Groq
FALLBACK_MODELS = [
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
    "qwen/qwen3.8-27b",
]


@dataclass
class ChatbotModelConfig:
    """
    Configuration model for the Groq Chatbot.
    All attributes are fully configurable at initialization or runtime.
    """
    api_key: str = ""
    model_name: str = ""
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    temperature: float = 0.7
    max_tokens: int = 800
    timeout: int = 15

    def __post_init__(self):
        import os
        # Auto-load defaults from Django settings or environment if not explicitly provided
        if not self.api_key:
            self.api_key = getattr(settings, "GROQ_API_KEY", "") or os.environ.get("GROQ_API_KEY", "")
        if not self.model_name:
            self.model_name = getattr(settings, "GROQ_MODEL", "") or os.environ.get("GROQ_MODEL", "") or "openai/gpt-oss-20b"


class GroqChatbotModel:
    """
    Standalone Groq Chatbot Model.
    Provides methods to query Groq LLM services with configurable system prompts,
    conversation history memory, and automatic model fallback.
    """

    def __init__(self, config: Optional[ChatbotModelConfig] = None):
        self.config = config or ChatbotModelConfig()

    def set_system_prompt(self, new_prompt: str) -> None:
        """Dynamically update the system prompt to align assistant behavior."""
        self.config.system_prompt = new_prompt.strip()

    def get_system_prompt(self) -> str:
        """Retrieve the currently active system prompt."""
        return self.config.system_prompt

    def _call_groq_api(self, messages: List[Dict[str, str]], model_name: str) -> Dict[str, Any]:
        """Low-level HTTP request to Groq API using standard urllib."""
        if not self.config.api_key:
            raise ValueError("GROQ_API_KEY is not configured in .env or settings.")

        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }

        req = urllib.request.Request(
            GROQ_ENDPOINT,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.api_key}",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
            data = resp.read().decode("utf-8")
            return json.loads(data)

    def generate_reply(
        self,
        user_message: str,
        history: Optional[List[Dict[str, str]]] = None,
        custom_system_prompt: Optional[str] = None,
    ) -> str:
        """
        Generate an assistant reply using Groq.
        
        Args:
            user_message: The latest text from the user.
            history: Optional list of past turns: [{"role": "user"|"assistant", "content": "..."}]
            custom_system_prompt: Optional override for this specific turn.
        
        Returns:
            The string response from the LLM.
        """
        prompt = custom_system_prompt if custom_system_prompt is not None else self.config.system_prompt

        messages: List[Dict[str, str]] = [{"role": "system", "content": prompt}]

        # Append sanitized history (limit to last 8 turns for speed & token efficiency)
        if history and isinstance(history, list):
            for turn in history[-8:]:
                role = turn.get("role")
                content = turn.get("content")
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": str(content)[:1000]})

        # Append current user prompt
        messages.append({"role": "user", "content": user_message.strip()})

        # Attempt with configured model first, fallback if invalid model identifier
        models_to_try = [self.config.model_name]
        for fb in FALLBACK_MODELS:
            if fb != self.config.model_name:
                models_to_try.append(fb)

        last_error = None
        for candidate_model in models_to_try:
            try:
                res = self._call_groq_api(messages, candidate_model)
                choices = res.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "").strip()
            except urllib.error.HTTPError as http_err:
                error_body = http_err.read().decode("utf-8", errors="ignore")
                logger.warning(
                    "Groq API error on model %s (HTTP %s): %s",
                    candidate_model,
                    http_err.code,
                    error_body,
                )
                last_error = f"HTTP {http_err.code}: {error_body}"
                # If model is not recognized (400 or 404), try next candidate
                if http_err.code in (400, 404):
                    continue
                break
            except Exception as e:
                logger.error("Unexpected error contacting Groq: %s", str(e))
                last_error = str(e)
                break

        if last_error:
            raise RuntimeError(f"Groq API request failed: {last_error}")

        return "I am here to help you! Feel free to ask about our banquet halls, catering, photography, or any event services."


# ══════════════════════════════════════════════════════════════════════════════
# 3. HELPER FUNCTION FOR EASY IMPORT & USE
# ══════════════════════════════════════════════════════════════════════════════

# Global default instance
_default_bot = GroqChatbotModel()


def ask_assistant(
    message: str,
    history: Optional[List[Dict[str, str]]] = None,
    system_prompt: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Convenience wrapper to ask the Groq AI Assistant.

    Returns:
        {"ok": True, "reply": "..."} on success
        {"ok": False, "error": "...", "reply": "..."} on failure with fallback text
    """
    if not message or not message.strip():
        return {"ok": False, "error": "Empty message", "reply": "How can I help you today?"}

    global _default_bot
    if not _default_bot.config.api_key or not _default_bot.config.model_name or "llama" in _default_bot.config.model_name.lower() or "mixtral" in _default_bot.config.model_name.lower():
        _default_bot.config.__post_init__()

    try:
        reply = _default_bot.generate_reply(
            user_message=message,
            history=history,
            custom_system_prompt=system_prompt,
        )
        return {"ok": True, "reply": reply}
    except Exception as exc:
        logger.exception("Assistant failure: %s", str(exc))
        return {
            "ok": False,
            "error": str(exc),
            "reply": (
                "Thank you for reaching out! I'm currently having a brief connection issue. "
                "In the meantime, you can explore all our venues and vendors by clicking 'Book Now' above!"
            ),
        }
