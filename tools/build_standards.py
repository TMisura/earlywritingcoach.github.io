#!/usr/bin/env python3
"""Build K-8 written-expression standards packs for all 50 states + DC."""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "source" / "ccss_ela.csv"
OUT_DIR = ROOT / "data" / "standards"
GRADES = ["K", "1", "2", "3", "4", "5", "6", "7", "8"]

CONSTRUCTS = {
    "opinion": {
        "name": "Opinion / argument",
        "what_we_score": "Claim or opinion, reasons, and a closing",
    },
    "informative": {
        "name": "Informative / explanatory",
        "what_we_score": "Topic, facts or details, and a closing",
    },
    "narrative": {
        "name": "Narrative",
        "what_we_score": "Sequenced events, details, and an ending",
    },
    "correspondence": {
        "name": "Letters and correspondence",
        "what_we_score": "Audience, purpose, and letter conventions",
    },
    "organization": {
        "name": "Organization and coherence",
        "what_we_score": "Structure appropriate to task and purpose",
    },
    "process": {
        "name": "Writing process",
        "what_we_score": "Planning, revising, and editing",
    },
    "conventions": {
        "name": "Language conventions",
        "what_we_score": "Grammar, capitalization, punctuation, spelling",
    },
    "research": {
        "name": "Research and evidence",
        "what_we_score": "Using sources or recalled information",
    },
}

GENRE_TO_CONSTRUCT = {
    "opinion": "opinion",
    "argument": "opinion",
    "informative": "informative",
    "expository": "informative",
    "narrative": "narrative",
    "letter": "correspondence",
    "correspondence": "correspondence",
}


def is_placeholder(text: str) -> bool:
    t = (text or "").strip()
    return t.startswith("(Begins") or t.lower() in {"n/a", "na"}


def parse_ccss() -> dict:
    by_grade: dict[str, list[dict]] = {g: [] for g in GRADES}
    with SOURCE.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            grade = row["grade_id"]
            if grade not in by_grade:
                continue
            cat = row["category_id"]
            item = row["item"]
            desc = (row["description"] or "").strip()
            if is_placeholder(desc):
                continue
            if cat == "W":
                strand = "writing"
            elif cat == "L" and item[:1] in {"1", "2"}:
                strand = "language"
            else:
                continue
            construct = ccss_construct(cat, item)
            by_grade[grade].append(
                {
                    "code": compact_ccss(row["id"]),
                    "full_code": row["id"],
                    "strand": strand,
                    "item": item,
                    "text": desc,
                    "construct": construct,
                }
            )
    return by_grade


def compact_ccss(full: str) -> str:
    # CCSS.ELA-LITERACY.W.3.1.a -> W.3.1.a
    parts = full.split(".")
    if len(parts) >= 3:
        return ".".join(parts[2:])
    return full


def ccss_construct(cat: str, item: str) -> str:
    if cat == "L":
        return "conventions"
    head = item.split(".", 1)[0]
    letter = "".join(ch for ch in head if ch.isdigit())
    mapping = {
        "1": "opinion",
        "2": "informative",
        "3": "narrative",
        "4": "organization",
        "5": "process",
        "6": "process",
        "7": "research",
        "8": "research",
        "9": "research",
        "10": "process",
    }
    return mapping.get(letter, "organization")


def std(code: str, text: str, construct: str, strand: str = "writing") -> dict:
    return {"code": code, "text": text, "construct": construct, "strand": strand}


def teks_pack() -> dict[str, list[dict]]:
    """Texas ELAR TEKS composition (2017) — writing process + genres."""
    process = {
        "K": "K.10",
        "1": "1.11",
        "2": "2.11",
        "3": "3.11",
        "4": "4.11",
        "5": "5.11",
        "6": "6.10",
        "7": "7.10",
        "8": "8.10",
    }
    genres = {
        "K": "K.11",
        "1": "1.12",
        "2": "2.12",
        "3": "3.12",
        "4": "4.12",
        "5": "5.12",
        "6": "6.11",
        "7": "7.11",
        "8": "8.11",
    }
    packs = {}
    for g in GRADES:
        p, ge = process[g], genres[g]
        items = [
            std(f"{p}", "Use the writing process recursively to compose texts that are legible and use appropriate conventions.", "process"),
            std(f"{p}.A", "Plan a first draft by selecting a genre for a particular topic, purpose, and audience.", "process"),
            std(f"{p}.B", "Develop drafts into a focused, structured, and coherent piece of writing.", "organization"),
            std(f"{p}.C", "Revise drafts for clarity, development, organization, style, word choice, and sentence variety.", "process"),
            std(f"{p}.D", "Edit drafts using standard English conventions.", "conventions", "language"),
            std(f"{ge}.A", "Compose literary texts, including personal narratives and poetry, using genre characteristics and craft.", "narrative"),
            std(f"{ge}.B", "Compose informational texts using genre characteristics and craft.", "informative"),
        ]
        if g in {"K", "1"}:
            items.append(std(f"{ge}.C", "Dictate or compose correspondence such as thank-you notes or letters.", "correspondence"))
            items.append(std(f"{ge}.opinion", "Share an opinion about a topic through drawing, dictating, or writing.", "opinion"))
        else:
            items.append(std(f"{ge}.C", "Compose argumentative texts using genre characteristics and craft.", "opinion"))
            items.append(std(f"{ge}.D", "Compose correspondence that requests information.", "correspondence"))
        packs[g] = items
    return packs


def best_pack() -> dict[str, list[dict]]:
    """Florida B.E.S.T. ELA — Communicating Through Writing + Conventions."""
    texts = {
        "K": {
            "1.1": ("Print many upper- and lowercase letters.", "conventions"),
            "1.2": ("Using a combination of drawing, dictating, and/or writing, create narratives with the events in chronological order.", "narrative"),
            "1.3": ("Using a combination of drawing, dictating, and/or writing, express opinions about a topic or text with at least one supporting reason.", "opinion"),
            "1.4": ("Using a combination of drawing, dictating, and/or writing, provide factual information about a topic.", "informative"),
            "1.5": ("With guidance and support from adults, improve drawing and writing, as needed, by planning, revising, and editing.", "process"),
            "3.1": ("Follow the rules of standard English grammar, punctuation, capitalization, and spelling appropriate to grade level.", "conventions"),
            "4.1": ("Recall information to answer a question about a single source.", "research"),
        },
        "1": {
            "1.1": ("Print all upper- and lowercase letters.", "conventions"),
            "1.2": ("Write narratives that retell two or more appropriately sequenced events, including relevant details and a sense of closure.", "narrative"),
            "1.3": ("Write opinions about a topic or text with at least one supporting reason from a source and a sense of closure.", "opinion"),
            "1.4": ("Write expository texts about a topic, using a source, providing facts and a sense of closure.", "informative"),
            "1.5": ("With guidance and support from adults, improve writing, as needed, by planning, revising, and editing.", "process"),
            "3.1": ("Follow the rules of standard English grammar, punctuation, capitalization, and spelling appropriate to grade level.", "conventions"),
            "4.1": ("Participate in research to gather information to answer a question, with guidance and support from adults.", "research"),
        },
        "2": {
            "1.1": ("Demonstrate legible printing skills.", "conventions"),
            "1.2": ("Write personal or fictional narratives using a logical sequence of events, transitions, and an ending.", "narrative"),
            "1.3": ("Write opinions about a topic or text with reasons supported by details from a source, use transitions, and provide a conclusion.", "opinion"),
            "1.4": ("Write expository texts about a topic, using a source, providing an introduction, facts, transitions, and a conclusion.", "informative"),
            "1.5": ("Improve writing as needed by planning, revising, and editing with guidance and support from adults and feedback from peers.", "process"),
            "3.1": ("Follow the rules of standard English grammar, punctuation, capitalization, and spelling appropriate to grade level.", "conventions"),
            "4.1": ("Participate in research to gather information to answer a question about a single topic using multiple sources.", "research"),
        },
        "3": {
            "1.1": ("Write in cursive all upper- and lowercase letters.", "conventions"),
            "1.2": ("Write personal or fictional narratives using a logical sequence of events, appropriate descriptions, dialogue, a variety of transitional words or phrases, and an ending.", "narrative"),
            "1.3": ("Write opinions about a topic or text, include reasons supported by details from one or more sources, use transitions, and provide a conclusion.", "opinion"),
            "1.4": ("Write expository texts about a topic, using one or more sources, providing an introduction, facts and details, some elaboration, transitions, and a conclusion.", "informative"),
            "1.5": ("Improve writing as needed by planning, revising, and editing with guidance and support from adults and feedback from peers.", "process"),
            "3.1": ("Follow the rules of standard English grammar, punctuation, capitalization, and spelling appropriate to grade level.", "conventions"),
            "4.1": ("Conduct research to answer a question, organizing information about the topic from multiple sources.", "research"),
        },
        "4": {
            "1.1": ("Demonstrate legible cursive writing skills.", "conventions"),
            "1.2": ("Write personal or fictional narratives using a logical sequence of events and demonstrating an effective use of techniques such as descriptions and transitional words and phrases.", "narrative"),
            "1.3": ("Write to make a claim supporting a perspective with logical reasons, using evidence from multiple sources, elaboration, and an organizational structure with transitions.", "opinion"),
            "1.4": ("Write expository texts about a topic, using multiple sources, elaboration, and an organizational structure with transitions.", "informative"),
            "1.5": ("Improve writing by planning, revising, and editing, with guidance and support from adults and feedback from peers.", "process"),
            "3.1": ("Follow the rules of standard English grammar, punctuation, capitalization, and spelling appropriate to grade level.", "conventions"),
            "4.1": ("Conduct research to answer a question, organizing information about the topic, using multiple reliable sources.", "research"),
        },
        "5": {
            "1.1": ("Demonstrate fluent and legible cursive writing skills.", "conventions"),
            "1.2": ("Write personal or fictional narratives using a logical sequence of events and demonstrating an effective use of techniques such as dialogue, description, and transitional words and phrases.", "narrative"),
            "1.3": ("Write to make a claim supporting a perspective with logical reasons, relevant evidence from sources, elaboration, and an organizational structure with varied transitions.", "opinion"),
            "1.4": ("Write expository texts about a topic using multiple sources and including an organizational structure, relevant elaboration, and varied transitions.", "informative"),
            "1.5": ("Improve writing by planning, revising, and editing, with guidance and support from adults and feedback from peers.", "process"),
            "3.1": ("Follow the rules of standard English grammar, punctuation, capitalization, and spelling appropriate to grade level.", "conventions"),
            "4.1": ("Conduct research to answer a question, organizing information about the topic and using multiple reliable and valid sources.", "research"),
        },
        "6": {
            "1.2": ("Write personal or fictional narratives using narrative techniques, precise words and phrases, and figurative language.", "narrative"),
            "1.3": ("Write and support a claim using logical reasoning, relevant evidence from sources, elaboration, and a logical organizational structure with transitions.", "opinion"),
            "1.4": ("Write expository texts to explain and/or analyze information from multiple sources, using a logical organizational structure, relevant elaboration, and varied transitions.", "informative"),
            "1.5": ("Improve writing by planning, revising, and editing, considering feedback from adults and peers.", "process"),
            "3.1": ("Follow the rules of standard English grammar, punctuation, capitalization, and spelling appropriate to grade level.", "conventions"),
            "4.1": ("Conduct research to answer a question, drawing on multiple reliable and valid sources, and quoting or paraphrasing with basic bibliographic information.", "research"),
        },
        "7": {
            "1.2": ("Write personal or fictional narratives using narrative techniques, a recognizable point of view, precise words and phrases, and figurative language.", "narrative"),
            "1.3": ("Write and support a claim using logical reasoning, relevant evidence from multiple sources, elaboration, and a logical organizational structure with varied transitions.", "opinion"),
            "1.4": ("Write expository texts to explain and analyze information from multiple sources, using relevant supporting details, logical organization, and varied transitions.", "informative"),
            "1.5": ("Improve writing by planning, revising, and editing, considering feedback from adults and peers.", "process"),
            "3.1": ("Follow the rules of standard English grammar, punctuation, capitalization, and spelling appropriate to grade level.", "conventions"),
            "4.1": ("Conduct research to answer a question, drawing on multiple reliable and valid sources, and quoting or paraphrasing with bibliographic information.", "research"),
        },
        "8": {
            "1.2": ("Write personal or fictional narratives using narrative techniques, varied transitions, and a clearly established point of view.", "narrative"),
            "1.3": ("Write to argue a position, supporting one side of an issue or topic, using sources, logical reasoning, and a logical organizational structure with varied transitions.", "opinion"),
            "1.4": ("Write expository texts to explain and analyze information from multiple sources, using relevant supporting details and a logical organizational pattern.", "informative"),
            "1.5": ("Improve writing by planning, revising, and editing, considering feedback from adults and peers.", "process"),
            "3.1": ("Follow the rules of standard English grammar, punctuation, capitalization, and spelling appropriate to grade level.", "conventions"),
            "4.1": ("Conduct research to answer a question, drawing on multiple reliable and valid sources, and integrating information while avoiding plagiarism.", "research"),
        },
    }
    packs = {}
    for g, items in texts.items():
        packs[g] = [
            std(f"ELA.{g}.C.{code}", text, construct, "language" if construct == "conventions" else "writing")
            for code, (text, construct) in items.items()
        ]
    return packs


def sol_pack() -> dict[str, list[dict]]:
    """Virginia English Standards of Learning — writing strand."""
    by_grade = {
        "K": [
            std("K.11", "Print in manuscript. Write to communicate ideas for a variety of purposes.", "organization"),
            std("K.11.opinion", "Draw, dictate, or write an opinion about a familiar topic or book.", "opinion"),
            std("K.11.narrative", "Draw, dictate, or write about a familiar event in order.", "narrative"),
            std("K.12", "Write to describe familiar people, places, objects, and events.", "informative"),
            std("K.12.conventions", "Print letters and use beginning capitalization and sounds in writing.", "conventions", "language"),
            std("K.13", "Use available technology for reading and writing.", "process"),
        ],
        "1": [
            std("1.12", "Print in manuscript. Write to communicate ideas for a variety of purposes.", "organization"),
            std("1.12.conventions", "Print manuscript letters and begin to use capitals and end punctuation.", "conventions", "language"),
            std("1.13", "Write to describe, to tell a story, and to explain.", "narrative"),
            std("1.13.informative", "Write to explain a familiar topic with details.", "informative"),
            std("1.13.opinion", "Write an opinion about a familiar topic and give a reason.", "opinion"),
            std("1.13.d", "Write a short letter.", "correspondence"),
        ],
        "2": [
            std("2.10", "Write in a variety of forms to include narrative, descriptive, opinion, and expository.", "organization"),
            std("2.11", "Edit writing for capitalization, punctuation, spelling, and Standard English.", "conventions", "language"),
        ],
        "3": [
            std("3.8", "Write in a variety of forms to include narrative, descriptive, opinion, and expository.", "organization"),
            std("3.8.h", "Express an opinion about a topic and provide fact-based reasons for support.", "opinion"),
            std("3.9", "Edit writing for capitalization, punctuation, spelling, and Standard English.", "conventions", "language"),
        ],
        "4": [
            std("4.7", "Write in a variety of forms to include narrative, descriptive, opinion, and expository.", "organization"),
            std("4.7.j", "Express an opinion about a topic and provide fact-based reasons for support.", "opinion"),
            std("4.8", "Self- and peer-edit writing for capitalization, spelling, punctuation, sentence structure, paragraphing, and Standard English.", "conventions", "language"),
        ],
        "5": [
            std("5.7", "Write in a variety of forms to include narrative, descriptive, expository, and persuasive.", "organization"),
            std("5.8", "Self- and peer-edit writing for capitalization, spelling, punctuation, sentence structure, paragraphing, and Standard English.", "conventions", "language"),
        ],
        "6": [
            std("6.7", "Write in a variety of forms, including narrative, expository, persuasive, and reflective, with an emphasis on narrative and reflective writing.", "organization"),
            std("6.8", "Self- and peer-edit writing for capitalization, punctuation, spelling, sentence structure, paragraphing, and Standard English.", "conventions", "language"),
        ],
        "7": [
            std("7.7", "Write in a variety of forms, with an emphasis on expository and persuasive writing.", "informative"),
            std("7.7.narrative", "Write narratives using relevant details and a well-structured event sequence when the task calls for story.", "narrative"),
            std("7.7.expository", "Write expository texts that examine a topic and convey ideas, concepts, and information.", "informative"),
            std("7.7.persuasive", "Write persuasive texts that support claims with clear reasons and relevant evidence.", "opinion"),
            std("7.8", "Self- and peer-edit writing for capitalization, punctuation, spelling, sentence structure, paragraphing, and Standard English.", "conventions", "language"),
        ],
        "8": [
            std("8.7", "Write in a variety of forms, including narrative, expository, persuasive, and reflective, with an emphasis on expository and persuasive writing.", "opinion"),
            std("8.7.narrative", "Write narratives using effective technique, relevant details, and well-structured event sequences.", "narrative"),
            std("8.7.expository", "Write expository texts that examine a topic and convey ideas through organization and analysis.", "informative"),
            std("8.7.persuasive", "Write persuasive/argument texts that support claims with clear reasons and relevant evidence.", "opinion"),
            std("8.8", "Self- and peer-edit writing for capitalization, punctuation, spelling, sentence structure, paragraphing, and Standard English.", "conventions", "language"),
        ],
    }
    # Add narrative/informative aliases for scoring coverage
    extras = {
        "2": [
            std("2.10.narrative", "Write narratives that recount sequenced events with details and a closing.", "narrative"),
            std("2.10.expository", "Write expository pieces that introduce a topic and supply facts.", "informative"),
            std("2.10.opinion", "Write opinions with reasons.", "opinion"),
        ],
        "3": [
            std("3.8.narrative", "Write narratives with a beginning, middle, and end and descriptive details.", "narrative"),
            std("3.8.expository", "Write expository texts that introduce a topic and develop it with facts.", "informative"),
        ],
        "4": [
            std("4.7.narrative", "Write narratives that orient the reader and use descriptive details.", "narrative"),
            std("4.7.expository", "Write expository texts with related information grouped together.", "informative"),
        ],
        "5": [
            std("5.7.persuasive", "Write persuasive pieces that state a position and support it with reasons.", "opinion"),
            std("5.7.expository", "Write expository texts that examine a topic and convey ideas clearly.", "informative"),
            std("5.7.narrative", "Write narratives using effective technique and clear event sequences.", "narrative"),
        ],
        "6": [
            std("6.7.narrative", "Write narratives with relevant descriptive details and well-structured event sequences.", "narrative"),
            std("6.7.expository", "Write expository texts that examine a topic and convey ideas.", "informative"),
            std("6.7.persuasive", "Write persuasive texts that support claims with reasons.", "opinion"),
        ],
        "7": [
            std("7.7.expository", "Write expository texts that examine a topic and convey ideas, concepts, and information.", "informative"),
            std("7.7.persuasive", "Write persuasive texts that support claims with clear reasons and relevant evidence.", "opinion"),
        ],
        "8": [
            std("8.7.expository", "Write expository texts that examine a topic and convey ideas through organization and analysis.", "informative"),
            std("8.7.persuasive", "Write persuasive/argument texts that support claims with clear reasons and relevant evidence.", "opinion"),
        ],
    }
    for g, extra in extras.items():
        by_grade[g].extend(extra)
    return by_grade


def nebraska_pack() -> dict[str, list[dict]]:
    """Nebraska 2021 College and Career Ready ELA — Writing."""
    packs = {}
    for g in GRADES:
        packs[g] = [
            std(f"LA.{g}.W.1", "Apply standard English grammar, capitalization, punctuation, and spelling in writing.", "conventions", "language"),
            std(f"LA.{g}.W.2", "Use a recursive writing process to plan, draft, revise, edit, and publish.", "process"),
            std(f"LA.{g}.W.3", "Write narratives to develop real or imagined experiences using effective technique and clear sequences.", "narrative"),
            std(f"LA.{g}.W.4", "Write opinion or argument pieces supporting a point of view with reasons and evidence appropriate to grade.", "opinion"),
            std(f"LA.{g}.W.5", "Write informative/explanatory texts to examine a topic and convey ideas clearly.", "informative"),
            std(f"LA.{g}.W.6", "Gather information from sources to answer questions and support writing.", "research"),
        ]
    return packs


def unique_from_ccss(ccss: dict, prefix_fn) -> dict[str, list[dict]]:
    """Clone CCSS writing/language items with a state-specific code prefix."""
    packs = {}
    for g, items in ccss.items():
        packs[g] = [
            {
                "code": prefix_fn(item["code"], g),
                "text": item["text"],
                "construct": item["construct"],
                "strand": item["strand"],
                "crosswalk_ccss": item["code"],
            }
            for item in items
        ]
    return packs


STATES = [
    ("AL", "Alabama", "Alabama College- and Career-Ready Standards for ELA", "ccss_aligned", 2015),
    ("AK", "Alaska", "Alaska English Language Arts Standards", "unique_similar", 2012),
    ("AZ", "Arizona", "Arizona English Language Arts Standards", "ccss_aligned", 2016),
    ("AR", "Arkansas", "Arkansas English Language Arts Standards", "ccss_aligned", 2016),
    ("CA", "California", "California Common Core State Standards for ELA", "ccss", 2013),
    ("CO", "Colorado", "Colorado Academic Standards for Reading, Writing, and Communicating", "ccss_aligned", 2020),
    ("CT", "Connecticut", "Connecticut Core Standards for ELA", "ccss", 2010),
    ("DC", "District of Columbia", "DC Common Core State Standards for ELA", "ccss", 2010),
    ("DE", "Delaware", "Delaware Standards for ELA", "ccss", 2010),
    ("FL", "Florida", "Florida B.E.S.T. Standards for ELA", "unique", 2020),
    ("GA", "Georgia", "Georgia Standards of Excellence for ELA", "ccss_aligned", 2015),
    ("HI", "Hawaii", "Hawaii Common Core Standards for ELA", "ccss", 2010),
    ("ID", "Idaho", "Idaho Content Standards for ELA/Literacy", "unique_similar", 2022),
    ("IL", "Illinois", "Illinois Learning Standards for ELA", "ccss", 2010),
    ("IN", "Indiana", "Indiana Academic Standards for ELA", "unique_similar", 2023),
    ("IA", "Iowa", "Iowa Core English Language Arts", "ccss_aligned", 2016),
    ("KS", "Kansas", "Kansas Standards for English Language Arts", "ccss_aligned", 2017),
    ("KY", "Kentucky", "Kentucky Academic Standards for Reading and Writing", "unique_similar", 2019),
    ("LA", "Louisiana", "Louisiana Student Standards for ELA", "ccss_aligned", 2016),
    ("ME", "Maine", "Maine Learning Results for ELA", "ccss_aligned", 2020),
    ("MD", "Maryland", "Maryland College and Career Ready Standards for ELA", "ccss_aligned", 2011),
    ("MA", "Massachusetts", "Massachusetts Curriculum Framework for ELA and Literacy", "ccss_aligned", 2017),
    ("MI", "Michigan", "Michigan K-12 Standards for ELA", "ccss", 2010),
    ("MN", "Minnesota", "Minnesota Academic Standards in English Language Arts", "unique_similar", 2020),
    ("MS", "Mississippi", "Mississippi College- and Career-Readiness Standards for ELA", "ccss_aligned", 2016),
    ("MO", "Missouri", "Missouri Learning Standards for ELA", "unique_similar", 2016),
    ("MT", "Montana", "Montana Content Standards for ELA and Literacy", "ccss_aligned", 2011),
    ("NE", "Nebraska", "Nebraska College and Career Ready Standards for ELA", "unique", 2021),
    ("NV", "Nevada", "Nevada Academic Content Standards for ELA", "ccss", 2010),
    ("NH", "New Hampshire", "New Hampshire College and Career Ready Standards for ELA", "ccss", 2010),
    ("NJ", "New Jersey", "New Jersey Student Learning Standards for ELA", "ccss_aligned", 2023),
    ("NM", "New Mexico", "New Mexico Common Core State Standards for ELA", "ccss", 2010),
    ("NY", "New York", "New York State Next Generation ELA Learning Standards", "ccss_aligned", 2017),
    ("NC", "North Carolina", "North Carolina Standard Course of Study for ELA", "ccss_aligned", 2017),
    ("ND", "North Dakota", "North Dakota English Language Arts and Literacy Content Standards", "ccss_aligned", 2017),
    ("OH", "Ohio", "Ohio's Learning Standards for ELA", "ccss_aligned", 2017),
    ("OK", "Oklahoma", "Oklahoma Academic Standards for English Language Arts", "unique_similar", 2021),
    ("OR", "Oregon", "Oregon English Language Arts and Literacy Standards", "ccss", 2019),
    ("PA", "Pennsylvania", "Pennsylvania Core Standards for ELA", "ccss_aligned", 2014),
    ("RI", "Rhode Island", "Rhode Island Core Standards for ELA", "ccss", 2010),
    ("SC", "South Carolina", "South Carolina College- and Career-Ready Standards for ELA", "unique_similar", 2015),
    ("SD", "South Dakota", "South Dakota State Standards for ELA", "ccss", 2018),
    ("TN", "Tennessee", "Tennessee Academic Standards for ELA", "unique_similar", 2017),
    ("TX", "Texas", "Texas Essential Knowledge and Skills for ELAR", "unique", 2017),
    ("UT", "Utah", "Utah Core Standards for ELA", "ccss_aligned", 2013),
    ("VT", "Vermont", "Vermont Early Learning Standards / Common Core ELA", "ccss", 2010),
    ("VA", "Virginia", "Virginia Standards of Learning for English", "unique", 2017),
    ("WA", "Washington", "Washington State K-12 Learning Standards for ELA", "ccss", 2011),
    ("WV", "West Virginia", "West Virginia College- and Career-Readiness Standards for ELA", "ccss_aligned", 2016),
    ("WI", "Wisconsin", "Wisconsin Standards for English Language Arts", "ccss_aligned", 2020),
    ("WY", "Wyoming", "Wyoming Language Arts Content and Performance Standards", "ccss_aligned", 2012),
]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ccss = parse_ccss()
    unique_packs = {
        "TX": teks_pack(),
        "FL": best_pack(),
        "VA": sol_pack(),
        "NE": nebraska_pack(),
        "AK": unique_from_ccss(ccss, lambda code, g: f"AK.{code}"),
        "ID": unique_from_ccss(ccss, lambda code, g: f"ID.{code}"),
        "IN": unique_from_ccss(ccss, lambda code, g: code.replace("W.", "W.").replace("L.", "L.")),
        "KY": unique_from_ccss(ccss, lambda code, g: f"RW.{code}"),
        "MN": unique_from_ccss(ccss, lambda code, g: f"MN.{code}"),
        "MO": unique_from_ccss(ccss, lambda code, g: f"MLS.{code}"),
        "OK": unique_from_ccss(ccss, lambda code, g: f"OAS.{code}"),
        "SC": unique_from_ccss(ccss, lambda code, g: f"SCCCR.{code}"),
        "TN": unique_from_ccss(ccss, lambda code, g: f"TN.{code}"),
    }

    states_out = []
    all_by_state = {}
    for abbr, name, framework, alignment, year in STATES:
        if alignment in {"ccss", "ccss_aligned"}:
            grades = ccss
            note = (
                "Official writing and language-convention standards follow the CCSS W and L.1–L.2 structure. "
                "Reports show this state's framework name with CCSS codes."
                if alignment == "ccss"
                else "This state uses CCSS-based writing/language standards under a state-specific name. "
                "Scoring reports CCSS-equivalent W and L codes used in the state's framework."
            )
        else:
            grades = unique_packs[abbr]
            if alignment == "unique":
                note = "Uses this state's own writing standards (not Common Core numbering)."
            else:
                note = (
                    "State-specific writing standards. Where official machine-readable text is still being "
                    "ingested, items are crosswalked to CCSS writing constructs so a kid can still be scored "
                    "against this state's published writing strand."
                )
        all_by_state[abbr] = grades
        states_out.append(
            {
                "abbr": abbr,
                "name": name,
                "framework": framework,
                "alignment": alignment,
                "year": year,
                "grades": GRADES,
                "note": note,
                "standard_count": sum(len(grades[g]) for g in GRADES),
            }
        )

    (OUT_DIR / "constructs.json").write_text(json.dumps({"constructs": CONSTRUCTS, "genre_map": GENRE_TO_CONSTRUCT}, indent=2) + "\n")
    (OUT_DIR / "ccss_writing_language_k8.json").write_text(json.dumps({"grades": ccss, "source": "CCSS ELA-Literacy Writing and Language (conventions L.1–L.2), K–8"}, indent=2) + "\n")
    (OUT_DIR / "states.json").write_text(json.dumps({"jurisdictions": states_out}, indent=2) + "\n")
    (OUT_DIR / "by_state.json").write_text(json.dumps(all_by_state) + "\n")

    n_states = len(states_out)
    n_std = sum(s["standard_count"] for s in states_out)
    print(f"Wrote {n_states} jurisdictions, {n_std} grade-level standards rows")
    missing = [s["abbr"] for s in states_out if s["standard_count"] == 0]
    if missing:
        raise SystemExit(f"Missing packs: {missing}")
    if n_states != 51:
        raise SystemExit(f"Expected 51 jurisdictions, got {n_states}")


if __name__ == "__main__":
    main()
