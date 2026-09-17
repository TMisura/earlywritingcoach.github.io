from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
GRADES = ["K", "1", "2", "3", "4", "5", "6", "7", "8"]


@lru_cache(maxsize=1)
def rubric() -> dict:
    return json.loads((DATA / "rubric.json").read_text())


@lru_cache(maxsize=1)
def states() -> list[dict]:
    return json.loads((DATA / "standards" / "states.json").read_text())["jurisdictions"]


@lru_cache(maxsize=1)
def by_state() -> dict:
    return json.loads((DATA / "standards" / "by_state.json").read_text())


@lru_cache(maxsize=1)
def constructs() -> dict:
    return json.loads((DATA / "standards" / "constructs.json").read_text())


def state_meta(abbr: str) -> dict:
    abbr = abbr.upper()
    for row in states():
        if row["abbr"] == abbr:
            return row
    raise KeyError(f"Unknown jurisdiction {abbr}")


def standards_for(abbr: str, grade: str) -> list[dict]:
    grade = str(grade).upper()
    if grade == "0":
        grade = "K"
    pack = by_state()[abbr.upper()][grade]
    return pack


def _count_words(text: str) -> int:
    return len(re.findall(r"[A-Za-z']+", text))


def _sentences(text: str) -> list[str]:
    parts = re.split(r"[.!?]+", text)
    return [p.strip() for p in parts if p.strip()]


def _band_score(value: int, bands: dict) -> int:
    if value >= bands["exceeding"]:
        return 4
    if value >= bands["meeting"]:
        return 3
    if value >= bands["developing"]:
        return 2
    return 1


def _contains_any(text: str, phrases: list[str]) -> int:
    hay = text.lower()
    return sum(1 for p in phrases if p in hay)


def _convention_score(text: str, sentences: list[str]) -> int:
    if not text.strip():
        return 1
    letters = re.findall(r"[A-Za-z]", text)
    caps = re.findall(r"[A-Z]", text)
    cap_ratio = (len(caps) / len(letters)) if letters else 0
    # A little capitalization is good; all-caps or none is weak.
    if not sentences:
        return 1
    started = sum(1 for s in sentences if s[:1].isupper())
    start_ratio = started / len(sentences)
    end_punct = len(re.findall(r"[.!?]", text))
    punct_ratio = min(1.0, end_punct / max(1, len(sentences)))
    score = 1
    if start_ratio >= 0.5:
        score += 1
    if punct_ratio >= 0.5:
        score += 1
    if 0.02 <= cap_ratio <= 0.18:
        score += 1
    return min(4, score)


def _genre_score(text: str, genre: str) -> int:
    lists = rubric()["word_lists"]
    key = {"argument": "opinion", "expository": "informative", "letter": "correspondence"}.get(genre, genre)
    hits = _contains_any(text, lists.get(key, []))
    if key == "correspondence":
        if hits >= 2:
            return 4
        if hits >= 1:
            return 3
        return 2 if _count_words(text) >= 20 else 1
    if hits >= 3:
        return 4
    if hits >= 2:
        return 3
    if hits >= 1 or _count_words(text) >= 40:
        return 2
    return 1


def _organization_score(text: str, sentences: list[str], grade: str) -> int:
    paragraphs = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    temporal = _contains_any(text, rubric()["word_lists"]["temporal"])
    closing = _contains_any(text.lower(), ["in conclusion", "finally", "that is why", "sincerely", "the end", "overall"])
    score = 1
    if len(sentences) >= 2:
        score += 1
    if temporal or len(paragraphs) >= 2:
        score += 1
    if closing or (grade not in {"K", "1"} and len(paragraphs) >= 3):
        score += 1
    return min(4, score)


def _research_score(text: str) -> int:
    hits = _contains_any(text, rubric()["word_lists"]["evidence"])
    if hits >= 3:
        return 4
    if hits >= 2:
        return 3
    if hits >= 1:
        return 2
    return 1


def _kid_note(construct: str, score: int, genre: str) -> str:
    tips = {
        ("opinion", 1): "Name what you think. Try starting with “I think…”",
        ("opinion", 2): "You shared an opinion. Add a second reason that starts with “because.”",
        ("opinion", 3): "Clear opinion with reasons. Can you add an example that proves one reason?",
        ("opinion", 4): "Strong argument. You told the reader what you think and why.",
        ("informative", 1): "Name your topic in the first sentence.",
        ("informative", 2): "Good start. Add two facts the reader might not already know.",
        ("informative", 3): "Solid information. Group related facts and end with a wrap-up sentence.",
        ("informative", 4): "You taught the reader something with clear facts and a closing.",
        ("narrative", 1): "Tell what happened first. Then what happened next.",
        ("narrative", 2): "The story is underway. Add a feeling or a small detail at one moment.",
        ("narrative", 3): "Nice sequence. Try a stronger ending that shows what changed.",
        ("narrative", 4): "The reader can follow the events and feel the moment.",
        ("correspondence", 1): "Start with Dear and the person’s name.",
        ("correspondence", 2): "You wrote to someone. Tell them why you are writing in the first lines.",
        ("correspondence", 3): "This reads like a real letter. Add a closing such as Sincerely or Love.",
        ("correspondence", 4): "Clear audience, purpose, and letter shape.",
        ("organization", 1): "Put a beginning, a middle, and an end on separate lines.",
        ("organization", 2): "Order is showing up. Use a word like first, then, or finally.",
        ("organization", 3): "The piece holds together. Check that each paragraph has one job.",
        ("organization", 4): "The structure matches the job of this kind of writing.",
        ("process", 1): "Read it out loud. Fix one sentence that is hard to say.",
        ("process", 2): "You have a draft. Change one word to a stronger one.",
        ("process", 3): "This is ready for a polish pass: spelling and punctuation.",
        ("process", 4): "This reads like a piece you revised on purpose.",
        ("conventions", 1): "Start each sentence with a capital and end it with a period.",
        ("conventions", 2): "Capitals are starting to show up. Check the end of every sentence.",
        ("conventions", 3): "Conventions are mostly in place. Hunt for one missing period or capital.",
        ("conventions", 4): "Sentences look complete and easy to read.",
        ("research", 1): "Add one fact you learned, and say where it came from.",
        ("research", 2): "You used information. Add the words “for example” before one fact.",
        ("research", 3): "Evidence is in the piece. Name the source in a short phrase.",
        ("research", 4): "You used information on purpose to support the writing.",
    }
    return tips.get((construct, score), "Keep going — write a little more and reread it.")


def assess(text: str, state: str, grade: str, genre: str) -> dict:
    grade = str(grade).upper()
    if grade == "0":
        grade = "K"
    if grade not in GRADES:
        raise ValueError("Grade must be K–8")
    genre = (genre or "informative").lower()
    if genre == "argument":
        genre = "opinion"
    if genre == "expository":
        genre = "informative"
    if genre == "letter":
        genre = "correspondence"
    meta = state_meta(state)
    r = rubric()
    words = _count_words(text)
    sentences = _sentences(text)
    length_score = _band_score(words, r["length_bands"][grade])
    sentence_score = _band_score(len(sentences), r["sentence_bands"][grade])
    development = min(4, round((length_score + sentence_score) / 2 + 0.25))
    organization = _organization_score(text, sentences, grade)
    conventions = _convention_score(text, sentences)
    genre_score = _genre_score(text, genre)
    research = _research_score(text)
    process = 3 if words >= r["length_bands"][grade]["meeting"] else (2 if words >= r["length_bands"][grade]["developing"] else 1)

    construct_scores = {
        "organization": organization,
        "conventions": conventions,
        "process": process,
        "research": research,
        genre if genre in {"opinion", "informative", "narrative", "correspondence"} else "informative": genre_score,
    }
    # Development rides with the genre construct.
    primary = genre if genre in construct_scores else "informative"
    construct_scores[primary] = max(construct_scores.get(primary, 1), development)

    pack = standards_for(state, grade)
    by_construct: dict[str, list[dict]] = {}
    for item in pack:
        by_construct.setdefault(item["construct"], []).append(item)

    results = []
    for construct, score in construct_scores.items():
        linked = by_construct.get(construct, [])[:4]
        if not linked:
            continue
        results.append(
            {
                "construct": construct,
                "name": constructs()["constructs"][construct]["name"],
                "score": score,
                "label": r["labels"][str(score)],
                "kid_note": _kid_note(construct, score, genre),
                "standards": [{"code": s["code"], "text": s["text"]} for s in linked],
            }
        )

    overall = round(sum(c["score"] for c in results) / max(1, len(results)))
    overall = min(4, max(1, overall))
    return {
        "state": meta["abbr"],
        "state_name": meta["name"],
        "framework": meta["framework"],
        "alignment": meta["alignment"],
        "framework_note": meta["note"],
        "grade": grade,
        "genre": genre,
        "word_count": words,
        "sentence_count": len(sentences),
        "overall": overall,
        "overall_label": r["labels"][str(overall)],
        "constructs": results,
        "next_step": results[0]["kid_note"] if results else "Write a little more and try again.",
    }
