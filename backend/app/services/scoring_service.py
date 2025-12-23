"""LLM-assisted scoring for engagement heatmaps.

This module augments heuristic scores with an optional LLM pass. If no LLM
configuration is present, the heuristic scores are returned unchanged.
"""
import json
from typing import Any, Dict, List, Optional

import requests

from app.core.config import settings


def _call_openai_chat(prompt: str, model: str, api_key: str) -> str:
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are an editor who scores video moments for replay-worthiness."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 500,
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _call_ollama_chat(prompt: str, model: str, base_url: str) -> str:
    url = f"{base_url.rstrip('/')}/api/chat"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are an editor who scores video moments for replay-worthiness."},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "options": {"temperature": 0.3},
    }
    resp = requests.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data.get("message", {}).get("content", "")


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
            llm_raw = _call_openai_chat(prompt, model=model, api_key=settings.openai_api_key)
        elif provider == "ollama":
            llm_raw = _call_ollama_chat(prompt, model=model, base_url=settings.ollama_base_url)
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
