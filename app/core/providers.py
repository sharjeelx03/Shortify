from __future__ import annotations

import json
import re
import time
from typing import Any, Callable, Dict, List, Tuple

from .settings import PROVIDER_LABELS

TRANSCRIPT_CHAR_LIMIT = 20000
PLACEHOLDER_WORDS = {"short title", "title", "clip", "untitled", "opening line", "hook"}


def _clean_text(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text if text else fallback


def _dynamic_output_tokens(num_clips: int) -> int:
    return max(1200, min(6000, 600 + (int(num_clips) * 280)))


def _transcript_limit(settings: Dict[str, Any] | None = None) -> int:
    if not settings:
        return TRANSCRIPT_CHAR_LIMIT
    try:
        return max(3000, min(50000, int(settings.get("transcript_char_limit", TRANSCRIPT_CHAR_LIMIT))))
    except Exception:
        return TRANSCRIPT_CHAR_LIMIT


def build_prompt(
    transcript: str,
    num_clips: int,
    durations: List[int],
    settings: Dict[str, Any] | None = None,
    retry_note: str = "",
) -> str:
    transcript_limit = _transcript_limit(settings)
    duration_text = ", ".join(f"{duration}s" for duration in durations[:num_clips])
    compact_transcript = transcript[:transcript_limit]
    retry_block = f"\nPrevious response problem: {retry_note}\nReturn a corrected JSON object only.\n" if retry_note else ""
    return f"""You are Shortify's local video-selection agent.
Select exactly {num_clips} viral moments from the transcript for short-form compilation videos.
Target durations: {duration_text}
Transcript slice used: first {transcript_limit} characters.
{retry_block}
TRANSCRIPT:
{compact_transcript}

Rules:
- Use timestamps in seconds only.
- Pick moments with strong hooks, useful info, emotion, surprise, or controversy.
- Avoid intros, outros, sponsors, and boring filler.
- Keep every moment self-contained.
- No placeholder titles such as "Short title", "Clip", or "Hook".
- end_seconds must be greater than start_seconds.
- duration_seconds should roughly match the requested duration.
- Return only JSON. No markdown.

JSON shape:
{{"clips":[{{"clip_number":1,"title":"Specific short title","hook":"Specific opening line","start_seconds":45,"end_seconds":53,"duration_seconds":8,"why_viral":"One sentence","hashtags":["#shorts","#viral","#ai"]}}]}}"""


def parse_ai_json(raw: str) -> List[Dict[str, Any]]:
    raw = str(raw or "").strip()
    raw = re.sub(r"^```json\s*|^```\s*|\s*```$", "", raw, flags=re.MULTILINE)
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        raw = match.group(0)
    data = json.loads(raw)
    clips = data.get("clips", [])
    if not isinstance(clips, list) or not clips:
        raise ValueError("AI did not return any clips.")
    return clips


def validate_clip_payload(clips: List[Dict[str, Any]], requested_count: int, durations: List[int]) -> List[Dict[str, Any]]:
    """Normalize AI clip JSON before ffmpeg touches it."""
    normalized: List[Dict[str, Any]] = []
    used_starts: set[int] = set()

    for index, item in enumerate(clips, start=1):
        if not isinstance(item, dict):
            continue
        try:
            start = int(float(item.get("start_seconds")))
            end = int(float(item.get("end_seconds")))
        except Exception:
            continue

        target_duration = int(durations[min(len(durations) - 1, index - 1)]) if durations else 8
        if start < 0:
            start = 0
        if end <= start:
            end = start + max(3, target_duration)
        if end - start > 90:
            end = start + max(3, target_duration)
        if start in used_starts:
            continue
        used_starts.add(start)

        title = _clean_text(item.get("title"), f"Moment {index}")
        hook = _clean_text(item.get("hook"), title)
        if title.lower() in PLACEHOLDER_WORDS:
            title = f"Moment {index}"
        if hook.lower() in PLACEHOLDER_WORDS:
            hook = title

        hashtags = item.get("hashtags", ["#shorts", "#viral"])
        if isinstance(hashtags, str):
            hashtags = [tag for tag in hashtags.split() if tag.startswith("#")]
        if not isinstance(hashtags, list) or not hashtags:
            hashtags = ["#shorts", "#viral"]

        normalized.append(
            {
                "clip_number": int(item.get("clip_number") or len(normalized) + 1),
                "title": title[:90],
                "hook": hook[:140],
                "start_seconds": start,
                "end_seconds": end,
                "duration_seconds": max(1, end - start),
                "why_viral": _clean_text(item.get("why_viral"), "This moment has strong short-form retention potential.")[:220],
                "hashtags": [str(tag).strip() for tag in hashtags[:10] if str(tag).strip()],
            }
        )
        if len(normalized) >= requested_count:
            break

    if not normalized:
        raise ValueError("AI returned clips, but none had valid timestamps. Try a smaller video or another provider.")
    return normalized


def _is_placeholder_payload(clips: List[Dict[str, Any]]) -> bool:
    for clip in clips:
        title = str(clip.get("title", "")).strip().lower()
        hook = str(clip.get("hook", "")).strip().lower()
        if title in PLACEHOLDER_WORDS or hook in PLACEHOLDER_WORDS:
            return True
    return False


def _with_retries(operation: Callable[[str], List[Dict[str, Any]]], retries: int = 2) -> List[Dict[str, Any]]:
    last_error: Exception | None = None
    retry_note = ""
    for attempt in range(retries + 1):
        try:
            clips = operation(retry_note)
            if _is_placeholder_payload(clips) and attempt < retries:
                retry_note = "Output used placeholder titles/hooks. Use specific titles and hooks from the transcript."
                continue
            return clips
        except Exception as exc:
            last_error = exc
            retry_note = str(exc)[:260]
            if attempt < retries:
                time.sleep(0.8 * (attempt + 1))
    raise RuntimeError(f"AI analysis failed after retries: {last_error}")


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
        return False, friendly_ai_error(exc, provider)


def friendly_ai_error(exc: Exception, provider: str = "AI") -> str:
    message = str(exc)
    low = message.lower()
    if "404" in low and "ollama" in provider.lower():
        return "Ollama is running, but the selected model was not found. Run: ollama pull llama3.2:3b"
    if "connection" in low or "refused" in low:
        return "AI provider is not reachable. Check internet/API key, or start Ollama for local mode."
    if "api key" in low or "authentication" in low or "unauthorized" in low:
        return "API key failed. Recheck the key in Settings and save again."
    if "context" in low or "token" in low or "too long" in low:
        return "Transcript is too long for this model. Lower Transcript Characters in Settings or use a larger model/context."
    if "json" in low:
        return "AI returned invalid JSON. Shortify retried, but the provider still returned malformed output."
    return f"{PROVIDER_LABELS.get(provider, provider)} error: {message}"


def analyze_ollama_once(transcript: str, num_clips: int, durations: List[int], settings: Dict[str, Any], retry_note: str = "") -> List[Dict[str, Any]]:
    import requests
    prompt = build_prompt(transcript, num_clips, durations, settings, retry_note=retry_note)
    url = f"{settings['ollama_url'].rstrip('/')}/api/generate"
    payload = {
        "model": settings["ollama_model"],
        "prompt": prompt,
        "format": "json",
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": _dynamic_output_tokens(num_clips)},
    }
    response = requests.post(url, json=payload, timeout=300)
    if response.status_code >= 400:
        details = response.text.strip()[:500] or response.reason
        raise RuntimeError(f"Ollama returned {response.status_code}. Model: {settings['ollama_model']}. Details: {details}")
    return parse_ai_json(response.json().get("response", ""))


def analyze_ollama(transcript: str, num_clips: int, durations: List[int], settings: Dict[str, Any]) -> List[Dict[str, Any]]:
    return _with_retries(lambda note: validate_clip_payload(analyze_ollama_once(transcript, num_clips, durations, settings, note), num_clips, durations))


def analyze_claude_once(transcript: str, num_clips: int, durations: List[int], settings: Dict[str, Any], retry_note: str = "") -> List[Dict[str, Any]]:
    import anthropic
    prompt = build_prompt(transcript, num_clips, durations, settings, retry_note=retry_note)
    client = anthropic.Anthropic(api_key=settings["claude_api_key"])
    msg = client.messages.create(
        model=settings["claude_model"],
        max_tokens=_dynamic_output_tokens(num_clips),
        messages=[{"role": "user", "content": prompt}],
    )
    return parse_ai_json(msg.content[0].text)


def analyze_claude(transcript: str, num_clips: int, durations: List[int], settings: Dict[str, Any]) -> List[Dict[str, Any]]:
    return _with_retries(lambda note: validate_clip_payload(analyze_claude_once(transcript, num_clips, durations, settings, note), num_clips, durations))


def analyze_openai_once(transcript: str, num_clips: int, durations: List[int], settings: Dict[str, Any], retry_note: str = "") -> List[Dict[str, Any]]:
    from openai import OpenAI
    prompt = build_prompt(transcript, num_clips, durations, settings, retry_note=retry_note)
    client = OpenAI(api_key=settings["openai_api_key"])
    kwargs = dict(
        model=settings["openai_model"],
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=_dynamic_output_tokens(num_clips),
        response_format={"type": "json_object"},
    )
    try:
        msg = client.chat.completions.create(**kwargs)
    except TypeError:
        kwargs.pop("response_format", None)
        msg = client.chat.completions.create(**kwargs)
    return parse_ai_json(msg.choices[0].message.content or "")


def analyze_openai(transcript: str, num_clips: int, durations: List[int], settings: Dict[str, Any]) -> List[Dict[str, Any]]:
    return _with_retries(lambda note: validate_clip_payload(analyze_openai_once(transcript, num_clips, durations, settings, note), num_clips, durations))


def analyze_gemini_once(transcript: str, num_clips: int, durations: List[int], settings: Dict[str, Any], retry_note: str = "") -> List[Dict[str, Any]]:
    import google.generativeai as genai
    prompt = build_prompt(transcript, num_clips, durations, settings, retry_note=retry_note)
    genai.configure(api_key=settings["gemini_api_key"])
    model = genai.GenerativeModel(settings["gemini_model"])
    try:
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
    except TypeError:
        response = model.generate_content(prompt)
    return parse_ai_json(response.text or "")


def analyze_gemini(transcript: str, num_clips: int, durations: List[int], settings: Dict[str, Any]) -> List[Dict[str, Any]]:
    return _with_retries(lambda note: validate_clip_payload(analyze_gemini_once(transcript, num_clips, durations, settings, note), num_clips, durations))


def analyze_with_provider(transcript: str, num_clips: int, durations: List[int], settings: Dict[str, Any]) -> List[Dict[str, Any]]:
    provider = settings["ai_provider"]
    try:
        if provider == "ollama":
            return analyze_ollama(transcript, num_clips, durations, settings)
        if provider == "claude":
            return analyze_claude(transcript, num_clips, durations, settings)
        if provider == "openai":
            return analyze_openai(transcript, num_clips, durations, settings)
        if provider == "gemini":
            return analyze_gemini(transcript, num_clips, durations, settings)
        raise ValueError(f"Unsupported AI provider: {provider}")
    except Exception as exc:
        raise RuntimeError(friendly_ai_error(exc, provider)) from exc
