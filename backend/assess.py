from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
GRADES = ["K", "1", "2", "3", "4", "5", "6", "7", "8"]

FOCUS_COPY = {
    "conventions": {
        "title": "Complete sentences: capitals and end marks",
        "noticed": "Sentences are not yet consistently started with a capital letter and closed with a period, question mark, or exclamation point.",
        "home_practice": [
            "Read the piece out loud. Every time you stop, check: Did that sentence start with a capital? Did it end with a mark?",
            "On a whiteboard, write three of the child’s own sentences together. The child adds the capital and the end mark; you do not grade the ideas.",
            "Keep this to two or three sentences a night. One clean habit beats a long edit.",
        ],
        "teacher_share": "At home we are practicing starting each sentence with a capital and ending it with punctuation. We are not scoring the writing; we are reinforcing that one convention.",
    },
    "organization": {
        "title": "A beginning, a middle, and an end",
        "noticed": "The ideas are there, but a reader still has to work to follow the order from start to finish.",
        "home_practice": [
            "Fold a paper into three boxes: Beginning / Middle / End. Retell this assignment in those three boxes only.",
            "Use one oral rehearsal before any rewriting: “First… Then… Last…”",
            "If the school assignment is a story, sequence events. If it is informational, use “topic / two facts / wrap-up.”",
        ],
        "teacher_share": "At home we are practicing a three-part plan (beginning, middle, end) so the child’s school writing is easier to follow. We are not assigning extra graded work.",
    },
    "opinion": {
        "title": "An opinion plus a reason",
        "noticed": "The writing does not yet make a clear claim and back it with a reason a reader can hear.",
        "home_practice": [
            "Finish this frame together: “I think ____ because ____.”",
            "Ask for a second because: “What’s one more reason?” Stop at two reasons.",
            "This works for any school prompt — book response, science claim, or “should we…?” homework.",
        ],
        "teacher_share": "At home we are practicing stating an opinion and giving one or two reasons. This is meant to support classroom opinion/argument writing, not replace it.",
    },
    "informative": {
        "title": "Name the topic, then add facts",
        "noticed": "A reader may not yet see a clear topic sentence followed by facts that teach something.",
        "home_practice": [
            "Write a one-line topic: “This is about ____.” Then add two facts the child actually knows.",
            "After each fact, ask “How do you know?” Keep the answer short.",
            "End with one wrap-up sentence, not a new topic.",
        ],
        "teacher_share": "At home we are practicing a topic sentence, two facts, and a closing. We are reinforcing informative writing the child already does at school.",
    },
    "narrative": {
        "title": "What happened, in order, with one detail",
        "noticed": "Events are not yet easy to follow, or the piece still needs one concrete detail (what was seen, said, or felt).",
        "home_practice": [
            "Tell the story with three fingers: first, next, last. Then write those three sentences.",
            "Add one detail to the middle sentence only (a sound, a feeling, or what someone did).",
            "Stop there. Do not rewrite the whole assignment.",
        ],
        "teacher_share": "At home we are practicing sequencing a beginning-middle-end and adding one detail. This is brief oral-then-written practice, not a new project.",
    },
    "correspondence": {
        "title": "A real letter to a real person",
        "noticed": "The piece still needs a clear audience (Dear…) and a closing, or a sentence that says why the child is writing.",
        "home_practice": [
            "Start with Dear and a name. Write two sentences: why you are writing, and one thing you want them to know.",
            "End with a closing the child chooses (Love, Thank you, Sincerely) and a name.",
            "If the school assignment is not a letter, still use audience: “Who is supposed to read this?”",
        ],
        "teacher_share": "At home we are practicing writing to a real audience with a greeting, a purpose, and a closing.",
    },
    "research": {
        "title": "One fact and where it came from",
        "noticed": "The writing does not yet point to a fact from a source, class notes, or a remembered text.",
        "home_practice": [
            "Add one sentence that starts with “For example…” or “In the book/article…”",
            "If there was no source, use school knowledge: “In class we learned…”",
            "Do not add a bibliography unless the teacher asked. One sourced fact is the habit.",
        ],
        "teacher_share": "At home we are practicing adding one fact and naming where it came from, to support evidence-based writing at school.",
    },
    "process": {
        "title": "Reread and change one thing on purpose",
        "noticed": "This still reads like a first pass. A short reread with one planned change would help more than starting over.",
        "home_practice": [
            "Read the piece aloud once. Circle one sentence that was hard to say.",
            "Change that sentence only — a stronger word, a missing word, or a split into two sentences.",
            "Praise the change, not a perfect paper.",
        ],
        "teacher_share": "At home we are practicing rereading and making one planned revision, not rewriting the whole assignment.",
    },
}


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
    return by_state()[abbr.upper()][grade]


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
    if not text.strip() or not sentences:
        return 1
    letters = re.findall(r"[A-Za-z]", text)
    caps = re.findall(r"[A-Z]", text)
    cap_ratio = (len(caps) / len(letters)) if letters else 0
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
    key = {"argument": "opinion", "expository": "informative", "letter": "correspondence", "any": "informative"}.get(genre, genre)
    hits = _contains_any(text, lists.get(key, lists["informative"]))
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
    return 4 if hits >= 3 else 3 if hits >= 2 else 2 if hits >= 1 else 1


def _guess_genre(text: str) -> str:
    lists = rubric()["word_lists"]
    scores = {key: _contains_any(text, phrases) for key, phrases in lists.items() if key in {"opinion", "informative", "narrative", "correspondence"}}
    best = max(scores, key=scores.get)
    return best if scores[best] else "informative"


def _analyze(text: str, grade: str, genre: str) -> dict[str, int]:
    r = rubric()
    words = _count_words(text)
    sentences = _sentences(text)
    length_score = _band_score(words, r["length_bands"][grade])
    sentence_score = _band_score(len(sentences), r["sentence_bands"][grade])
    development = min(4, round((length_score + sentence_score) / 2 + 0.25))
    primary = genre if genre in FOCUS_COPY else "informative"
    scores = {
        "organization": _organization_score(text, sentences, grade),
        "conventions": _convention_score(text, sentences),
        "process": 3 if words >= r["length_bands"][grade]["meeting"] else (2 if words >= r["length_bands"][grade]["developing"] else 1),
        "research": _research_score(text),
        primary: min(_genre_score(text, primary), development),
    }
    scores[primary] = min(scores.get(primary, 4), development)
    return scores


def _pick_focuses(scores: dict[str, int]) -> list[str]:
    ranked = sorted(scores.items(), key=lambda kv: (kv[1], kv[0]))
    chosen = [name for name, score in ranked if score <= 2][:2]
    if not chosen:
        chosen = [ranked[0][0]]
    return chosen[:2]


def coach(text: str, state: str, grade: str, assignment_label: str = "", genre: str = "any") -> dict:
    """Return 1–2 parent/tutor focuses. Never includes the writing sample."""
    grade = str(grade).upper()
    if grade == "0":
        grade = "K"
    if grade not in GRADES:
        raise ValueError("Grade must be K–8")
    genre = (genre or "any").lower()
    if genre in {"argument"}:
        genre = "opinion"
    if genre in {"expository"}:
        genre = "informative"
    if genre in {"letter"}:
        genre = "correspondence"
    if genre in {"any", "", "assignment", "school"}:
        genre = _guess_genre(text)
    meta = state_meta(state)
    scores = _analyze(text, grade, genre)
    pack = standards_for(state, grade)
    by_construct: dict[str, list[dict]] = {}
    for item in pack:
        by_construct.setdefault(item["construct"], []).append(item)

    focuses = []
    for construct in _pick_focuses(scores):
        copy = FOCUS_COPY[construct]
        linked = by_construct.get(construct, [])[:2]
        focuses.append(
            {
                "construct": construct,
                "title": copy["title"],
                "noticed": copy["noticed"],
                "home_practice": copy["home_practice"],
                "teacher_share": copy["teacher_share"],
                "standards": [{"code": s["code"], "text": s["text"]} for s in linked],
            }
        )

    slug = "-".join(f["construct"] for f in focuses) or "writing"
    filename = f"early-writing-coach-note-grade-{grade}-{meta['abbr']}-{slug}.html"
    return {
        "state": meta["abbr"],
        "state_name": meta["name"],
        "framework": meta["framework"],
        "alignment": meta["alignment"],
        "framework_note": meta["note"],
        "grade": grade,
        "assignment_label": (assignment_label or "School writing assignment").strip(),
        "writing_stored": False,
        "save_now": True,
        "save_cue": "The writing sample is not kept. Save this coaching note on your computer or print it now if you want a copy for the teacher.",
        "save_where": [
            "On your computer: use Save this note — it downloads an HTML file you can keep or attach to an email.",
            "On paper: use Print this note and put it in the homework folder.",
            "In your Early Writing Coach account (if you are signed in): only the skill names and home/school talking points are stored — never the writing.",
        ],
        "save_filename": filename,
        "focuses": focuses,
    }
