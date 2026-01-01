"""LLM-assisted scoring for engagement heatmaps.

This module augments heuristic scores with an optional LLM pass. If no LLM
configuration is present, the heuristic scores are returned unchanged.
"""
import json
from typing import Any, Dict, List, Optional

import requests

from app.core.config import settings


def _call_openai_chat(messages: List[Dict[str, str]], model: str, api_key: str) -> str:
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.5, # Slightly higher for creativity
        "max_tokens": 500,
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _call_ollama_chat(messages: List[Dict[str, str]], model: str, base_url: str) -> str:
    url = f"{base_url.rstrip('/')}/api/chat"
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.5},
    }
    resp = requests.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data.get("message", {}).get("content", "")


def _call_gemini_chat(messages: List[Dict[str, str]], api_key: str) -> str:
    # Convert OpenAI-style messages to Gemini content parts
    # Combine system and user messages into one prompt for simplicity in v1beta
    full_prompt = ""
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "system":
            full_prompt += f"System Instruction: {content}\n\n"
        else:
            full_prompt += f"User: {content}\n\n"
            
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [{"text": full_prompt}]
        }],
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 800,
        }
    }
    
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    
    # Extract text from response
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        return ""


def _build_prompt(top_segments: List[Dict[str, Any]], transcript_excerpt: str) -> str:
    summary_lines = []
    for seg in top_segments:
        summary_lines.append(
            f"- t={seg['start']:.1f}-{seg['end']:.1f}s, heuristic_score={seg['engagement_score']}, text='{seg.get('transcript_snippet', '')}'"
        )
    summary = "\n".join(summary_lines)

    return (
        "You are ranking short replay-worthy moments. Given transcript snippets and heuristic scores, "
        "assign an engagement score 1-10 and a short reason. Respond with JSON array of objects: "
        "[{\"start\": float, \"end\": float, \"llm_score\": float, \"reason\": str}].\n"
        f"Transcript excerpt:\n{transcript_excerpt}\n"
        f"Top heuristic segments:\n{summary}\n"
    )


def _extract_transcript_excerpt(transcript_segments: Optional[List[Dict[str, Any]]], max_chars: int = 1200) -> str:
    if not transcript_segments:
        return ""
    text_parts: List[str] = []
    total = 0
    for seg in transcript_segments:
        t = (seg.get("text") or "").strip()
        if not t:
            continue
        if total + len(t) > max_chars:
            break
        text_parts.append(t)
        total += len(t)
    return " ".join(text_parts)


def _attach_snippets(segments: List[Dict[str, Any]], transcript_segments: Optional[List[Dict[str, Any]]]) -> None:
    if not transcript_segments:
        return
    for seg in segments:
        # Find a transcript line that overlaps the segment
        snippet = ""
        for tseg in transcript_segments:
            if tseg.get("start") is None or tseg.get("end") is None:
                continue
            if tseg["start"] <= seg["start"] <= tseg["end"]:
                snippet = (tseg.get("text") or "").strip()
                break
        seg["transcript_snippet"] = snippet


def apply_llm_scoring(
    scored_segments: List[Dict[str, Any]],
    transcript_segments: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Augment heuristic scores with optional LLM scoring.

    If no LLM provider or credentials are configured, returns the original list.
    """
    if not settings.llm_enabled:
        return scored_segments

    provider = (settings.llm_provider or "").lower().strip()
    if not provider:
        return scored_segments

    model = settings.llm_model or "gpt-4o-mini"
    transcript_excerpt = _extract_transcript_excerpt(transcript_segments)

    # Select top heuristic segments to ask the LLM about
    top_segments = sorted(scored_segments, key=lambda s: s.get("engagement_score", 0), reverse=True)[:8]
    _attach_snippets(top_segments, transcript_segments)

    prompt = _build_prompt(top_segments, transcript_excerpt)

    llm_raw = ""
    try:
        if provider == "openai":
            if not settings.openai_api_key:
                return scored_segments
            messages = [
                {"role": "system", "content": "You are an editor who scores video moments for replay-worthiness."},
                {"role": "user", "content": prompt}
            ]
            llm_raw = _call_openai_chat(messages, model=model, api_key=settings.openai_api_key)
        elif provider == "ollama":
            messages = [
                {"role": "system", "content": "You are an editor who scores video moments for replay-worthiness."},
                {"role": "user", "content": prompt}
            ]
            llm_raw = _call_ollama_chat(messages, model=model, base_url=settings.ollama_base_url)
        elif provider == "gemini":
            if not settings.google_api_key:
                return scored_segments
            messages = [
                {"role": "system", "content": "You are an editor who scores video moments for replay-worthiness."},
                {"role": "user", "content": prompt}
            ]
            llm_raw = _call_gemini_chat(messages, api_key=settings.google_api_key)
        else:
            return scored_segments
    except Exception:
        return scored_segments

    try:
        llm_data = json.loads(llm_raw)
    except Exception:
        # Try to extract JSON block if the model wrapped it in text
        try:
            start = llm_raw.index("[")
            end = llm_raw.rindex("]") + 1
            llm_data = json.loads(llm_raw[start:end])
        except Exception:
            return scored_segments

    # Map llm scores by nearest start timestamp
    llm_by_start: Dict[float, Dict[str, Any]] = {}
    for item in llm_data:
        try:
            llm_by_start[float(item.get("start"))] = item
        except Exception:
            continue

    updated: List[Dict[str, Any]] = []
    for seg in scored_segments:
        llm_item = llm_by_start.get(round(seg.get("start", 0.0), 1))
        if llm_item and "llm_score" in llm_item:
            llm_score = float(llm_item.get("llm_score", seg["engagement_score"]))
            seg["llm_score"] = llm_score
            seg["reason"] = llm_item.get("reason")
            seg["engagement_score"] = round((seg["engagement_score"] * 0.4) + (llm_score * 0.6), 2)
        updated.append(seg)

    return updated


def generate_short_caption(transcript_text: str) -> str:
    """
    Generate a short, punchy social media caption/title (max 15 words) using LLM.
    Returns generic text if LLM fails or is disabled.
    """
    if not settings.llm_enabled or not transcript_text or len(transcript_text) < 10:
        return ""

    provider = (settings.llm_provider or "").lower().strip()
    if not provider:
        return ""

    model = settings.llm_model or "gpt-4o-mini"
    
    prompt = (
        f"Read this video transcript excerpt and write a SINGLE, SHORT, VIRAL caption (max 15 words). "
        f"No hashtags, no quotes, just the hook.\n\nTranscript:\n{transcript_text[:1000]}"
    )

    messages = [
        {"role": "system", "content": "You are a social media expert who writes viral hooks."},
        {"role": "user", "content": prompt}
    ]

    try:
        content = ""
        if provider == "openai":
            if settings.openai_api_key:
                content = _call_openai_chat(messages, model=model, api_key=settings.openai_api_key)
        elif provider == "ollama":
            content = _call_ollama_chat(messages, model=model, base_url=settings.ollama_base_url)
        elif provider == "gemini":
            if settings.google_api_key:
                content = _call_gemini_chat(messages, api_key=settings.google_api_key)
        
        # Cleanup quotes and extra spaces
        return content.strip().strip('"').strip("'")
            
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"LLM caption generation failed: {e}")
        return ""


def generate_video_title(transcript_text: str) -> str:
    """
    Generate a concise, engaging video title (max 5-7 words) from transcript.
    """
    if not settings.llm_enabled or not transcript_text or len(transcript_text) < 50:
        return ""

    provider = (settings.llm_provider or "").lower().strip()
    if not provider:
        return ""

    model = settings.llm_model or "gpt-4o-mini"
    
    prompt = (
        f"Generate a short, descriptive title (max 7 words) for this video based on the transcript. "
        f"Avoid clickbait, just describe the content accurately but engagingly.\n\nTranscript:\n{transcript_text[:1500]}"
    )

    messages = [
        {"role": "system", "content": "You are a professional video editor."},
        {"role": "user", "content": prompt}
    ]

    try:
        content = ""
        if provider == "openai":
            if settings.openai_api_key:
                content = _call_openai_chat(messages, model=model, api_key=settings.openai_api_key)
        elif provider == "ollama":
            content = _call_ollama_chat(messages, model=model, base_url=settings.ollama_base_url)
        elif provider == "gemini":
            if settings.google_api_key:
                content = _call_gemini_chat(messages, api_key=settings.google_api_key)
        
        return content.strip().strip('"').strip("'")
            
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"LLM title generation failed: {e}")
        return ""
