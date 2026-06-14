from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Tuple

from .settings import PROVIDER_LABELS

TRANSCRIPT_CHAR_LIMIT = 6500


def build_prompt(transcript: str, num_clips: int, durations: List[int]) -> str:
    duration_text = ", ".join(f"{duration}s" for duration in durations[:num_clips])
    compact_transcript = transcript[:TRANSCRIPT_CHAR_LIMIT]
    return f"""You are Shortify's local video-selection agent.
Select exactly {num_clips} viral moments from the transcript for short-form compilation videos.
Target durations: {duration_text}

TRANSCRIPT:
{compact_transcript}

Rules:
- Use timestamps in seconds only.
- Pick moments with strong hooks, useful info, emotion, surprise, or controversy.
- Avoid intros, outros, sponsors, and boring filler.
- Keep every moment self-contained.
- Return only JSON. No markdown.

JSON shape:
{{"clips":[{{"clip_number":1,"title":"Short title","hook":"Opening line","start_seconds":45,"end_seconds":53,"duration_seconds":8,"why_viral":"One sentence","hashtags":["#shorts","#viral","#ai"]}}]}}"""


def parse_ai_json(raw: str) -> List[Dict[str, Any]]:
    raw = raw.strip()
    raw = re.sub(r"^```json\s*|^```\s*|\s*```$", "", raw, flags=re.MULTILINE)
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        raw = match.group(0)
    data = json.loads(raw)
    clips = data.get("clips", [])
    if not isinstance(clips, list) or not clips:
        raise ValueError("AI did not return any clips.")
    return clips


def check_ollama(url: str) -> bool:
    try:
        import requests

        return requests.get(f"{url.rstrip('/')}/api/tags", timeout=4).status_code == 200
    except Exception:
        return False


def provider_ready(settings: Dict[str, Any]) -> Tuple[bool, str]:
    provider = settings.get("ai_provider", "ollama")
    if provider == "ollama":
        ok = check_ollama(settings.get("ollama_url", "http://localhost:11434"))
        return ok, "Connected" if ok else "Not running"
    key = str(settings.get(f"{provider}_api_key", "")).strip()
    return bool(key), "API key saved" if key else "Missing key"


def test_provider_connection(settings: Dict[str, Any]) -> Tuple[bool, str]:
    """Run a quick provider-specific connection test for the selected provider."""
    provider = settings.get("ai_provider", "ollama")

    if provider == "ollama":
        url = settings.get("ollama_url", "http://localhost:11434")
        if check_ollama(url):
            return True, "Ollama is running and reachable."
        return False, "Ollama is not reachable. Start Ollama, then test again."

    key = str(settings.get(f"{provider}_api_key", "")).strip()
    if not key:
        return False, f"{PROVIDER_LABELS.get(provider, provider)} API key is missing."

    try:
        if provider == "openai":
            from openai import OpenAI

            OpenAI(api_key=key).models.list()
            return True, "OpenAI connection successful."

        if provider == "claude":
            import anthropic

            client = anthropic.Anthropic(api_key=key)
            client.messages.create(
                model=settings.get("claude_model", "claude-sonnet-4-6"),
                max_tokens=5,
                messages=[{"role": "user", "content": "Reply OK."}],
            )
            return True, "Claude connection successful."

        if provider == "gemini":
            import google.generativeai as genai

            genai.configure(api_key=key)
            list(genai.list_models())
            return True, "Gemini connection successful."

        return False, f"Unsupported provider: {provider}"
    except Exception as exc:
        return False, f"Connection failed: {exc}"


def analyze_ollama(transcript: str, num_clips: int, durations: List[int], settings: Dict[str, Any]) -> List[Dict[str, Any]]:
    import requests

    prompt = build_prompt(transcript, num_clips, durations)
    url = f"{settings['ollama_url'].rstrip('/')}/api/generate"
    payload = {
        "model": settings["ollama_model"],
        "prompt": prompt,
        "format": "json",
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_predict": 2200,
        },
    }
    response = requests.post(url, json=payload, timeout=300)
    if response.status_code >= 400:
        details = response.text.strip()[:500] or response.reason
        raise RuntimeError(
            f"Ollama returned {response.status_code}. Model: {settings['ollama_model']}. Details: {details}"
        )
    return parse_ai_json(response.json().get("response", ""))


def analyze_claude(transcript: str, num_clips: int, durations: List[int], settings: Dict[str, Any]) -> List[Dict[str, Any]]:
    import anthropic

    prompt = build_prompt(transcript, num_clips, durations)
    client = anthropic.Anthropic(api_key=settings["claude_api_key"])
    msg = client.messages.create(
        model=settings["claude_model"],
        max_tokens=3600,
        messages=[{"role": "user", "content": prompt}],
    )
    return parse_ai_json(msg.content[0].text)


def analyze_openai(transcript: str, num_clips: int, durations: List[int], settings: Dict[str, Any]) -> List[Dict[str, Any]]:
    from openai import OpenAI

    prompt = build_prompt(transcript, num_clips, durations)
    client = OpenAI(api_key=settings["openai_api_key"])
    msg = client.chat.completions.create(
        model=settings["openai_model"],
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
    )
    return parse_ai_json(msg.choices[0].message.content or "")


def analyze_gemini(transcript: str, num_clips: int, durations: List[int], settings: Dict[str, Any]) -> List[Dict[str, Any]]:
    import google.generativeai as genai

    prompt = build_prompt(transcript, num_clips, durations)
    genai.configure(api_key=settings["gemini_api_key"])
    model = genai.GenerativeModel(settings["gemini_model"])
    response = model.generate_content(prompt)
    return parse_ai_json(response.text or "")


def analyze_with_provider(transcript: str, num_clips: int, durations: List[int], settings: Dict[str, Any]) -> List[Dict[str, Any]]:
    provider = settings["ai_provider"]
    if provider == "ollama":
        return analyze_ollama(transcript, num_clips, durations, settings)
    if provider == "claude":
        return analyze_claude(transcript, num_clips, durations, settings)
    if provider == "openai":
        return analyze_openai(transcript, num_clips, durations, settings)
    if provider == "gemini":
        return analyze_gemini(transcript, num_clips, durations, settings)
    raise ValueError(f"Unsupported AI provider: {provider}")
