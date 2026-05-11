"""Curated Google/YouTube classification cases for integration tests.

These cases are intentionally derived from existing test intent in:
- tests/core/classification/classifiers/domains/test_google.py
- tests/integration/classification/test_youtube_classifier.py

Keep this file as the single source for cross-test classification probes.

For YouTube, ``expected_category`` is the **LLM / product-intent** label used by live
LLM tests. When rule-based classification differs, set ``rules_expected_category``
(used by ``test_curated_classification_matrix``).
"""

from __future__ import annotations

from typing import NotRequired, TypedDict


class ClassificationCase(TypedDict):
    name: str
    domain: str
    url: str
    title: str
    expected_category: str


class YouTubeClassificationCase(TypedDict):
    """YouTube probe with optional legacy annotations."""

    name: str
    domain: str
    url: str
    title: str
    expected_category: str
    description: NotRequired[str]
    expected_usefulness: NotRequired[str]
    #: When rule-based classification disagrees with LLM intent (e.g. Bach, trailer).
    rules_expected_category: NotRequired[str]


GOOGLE_CURATED_CASES: list[ClassificationCase] = [
    {
        "name": "google_scholar_education",
        "domain": "scholar.google.com",
        "url": "https://scholar.google.com/scholar?q=machine+learning",
        "title": "Google Scholar",
        "expected_category": "EDUCATION",
    },
    {
        "name": "google_tutorial_education",
        "domain": "www.google.com",
        "url": "https://www.google.com/search?q=python+tutorial+for+beginners",
        "title": "python tutorial for beginners - Google Search",
        "expected_category": "EDUCATION",
    },
    {
        "name": "google_memes_entertainment",
        "domain": "www.google.com",
        "url": "https://www.google.com/search?q=funny+cat+memes",
        "title": "funny cat memes - Google Search",
        "expected_category": "ENTERTAINMENT",
    },
    {
        "name": "google_pdf_textbook_education",
        "domain": "www.google.com",
        "url": "https://www.google.com/search?q=calculus+textbook+pdf",
        "title": "[PDF] Calculus Textbook - Free Download",
        "expected_category": "EDUCATION",
    },
    {
        "name": "google_pdf_fiction_entertainment",
        "domain": "www.google.com",
        "url": "https://www.google.com/search?q=harry+potter+novel+pdf+free",
        "title": "harry potter novel pdf free - Google Search",
        "expected_category": "ENTERTAINMENT",
    },
    {
        "name": "google_shopping",
        "domain": "www.google.com",
        "url": "https://www.google.com/search?q=best+laptop+2024&tbm=shop",
        "title": "best laptop 2024 - Google Shopping",
        "expected_category": "SHOPPING",
    },
]


YOUTUBE_CURATED_CASES: list[YouTubeClassificationCase] = [
    {
        "name": "youtube_python_tutorial",
        "domain": "www.youtube.com",
        "url": "https://www.youtube.com/watch?v=_uQrJ0TkZlc",
        "title": "Python Tutorial for Beginners",
        "expected_category": "EDUCATION",
        "expected_usefulness": "EDUCATIONAL",
        "description": "Python Tutorial for Beginners (Programming with Mosh)",
    },
    {
        "name": "youtube_python_full_course",
        "domain": "www.youtube.com",
        "url": "https://www.youtube.com/watch?v=rfscVS0vtbw",
        "title": "Learn Python - Full Course for Beginners",
        "expected_category": "EDUCATION",
        "expected_usefulness": "EDUCATIONAL",
        "description": "Learn Python - Full Course for Beginners (freeCodeCamp)",
    },
    {
        "name": "youtube_algo_tutorial",
        "domain": "www.youtube.com",
        "url": "https://www.youtube.com/watch?v=8hly31xKli0",
        "title": "Algorithms and Data Structures Tutorial",
        "expected_category": "EDUCATION",
        "expected_usefulness": "EDUCATIONAL",
        "description": "Algorithms and Data Structures Tutorial (freeCodeCamp)",
    },
    {
        "name": "youtube_minecraft_trailer",
        "domain": "www.youtube.com",
        "url": "https://www.youtube.com/watch?v=MmB9b5njVbA",
        "title": "Official Minecraft Trailer",
        "expected_category": "ENTERTAINMENT",
        "rules_expected_category": "GAMING",
        "expected_usefulness": "DISTRACTION",
        "description": "Official Minecraft Trailer (game trailer = entertainment)",
    },
    {
        "name": "youtube_minecraft_shorts_gameplay",
        "domain": "www.youtube.com",
        "url": "https://www.youtube.com/shorts/tNRcypF_RjU",
        "title": "Minecraft Let's Play gameplay",
        # Rules: gaming keywords; LLM often labels humor/meme Minecraft shorts as ENTERTAINMENT.
        "expected_category": "ENTERTAINMENT",
        "rules_expected_category": "GAMING",
        "expected_usefulness": "DISTRACTION",
        "description": "Minecraft Let's Play gameplay video",
    },
    {
        "name": "youtube_fortnite_gameplay",
        "domain": "www.youtube.com",
        "url": "https://www.youtube.com/shorts/JnEkheSMQcA",
        "title": "Fortnite gameplay highlights",
        "expected_category": "GAMING",
        "expected_usefulness": "DISTRACTION",
        "description": "Fortnite gameplay highlights",
    },
    {
        "name": "youtube_music_video",
        "domain": "www.youtube.com",
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "title": "Never Gonna Give You Up (Music Video)",
        "expected_category": "ENTERTAINMENT",
        "expected_usefulness": "DISTRACTION",
        "description": "Rick Astley - Never Gonna Give You Up (Music Video)",
    },
    {
        "name": "youtube_bach_violin",
        "domain": "www.youtube.com",
        "url": "https://www.youtube.com/watch?v=I03Hs6dwj7E",
        "title": "Bach Violin Sonata (Classical Performance)",
        "expected_category": "EDUCATION",
        "rules_expected_category": "ENTERTAINMENT",
        "expected_usefulness": "EDUCATIONAL",
        "description": "Bach Violin Sonata (Classical Performance)",
    },
]
