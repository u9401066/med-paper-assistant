"""Writing Hooks — Anti-AI phrase and structural-signal constants (A3 / A3b / P2)."""

from __future__ import annotations

# ── Anti-AI phrase list (A3 / P2) ──────────────────────────────────
# Union of: auto-paper SKILL.md A3 (7), git-precommit SKILL.md P2 (10),
# DomainConstraintEngine V002 (16), + expanded AI-detection corpus.
# Deduplicated. Keep sorted by category.

ANTI_AI_PHRASES: list[str] = [
    # ── Classic AI filler ──
    "in recent years",
    "it is worth noting",
    "it is important to note",
    "it should be noted",
    "it is widely recognized",
    "it is imperative",
    "it is essential to",
    "it is well established",
    # ── Grandiose / buzzword (Pattern 1: Significance inflation) ──
    "plays a crucial role",
    "plays a vital role",
    "plays a pivotal role",
    "pivotal role",
    "has garnered significant attention",
    "a comprehensive understanding",
    "comprehensive overview",
    "this groundbreaking",
    "groundbreaking",
    "cutting-edge",
    "state-of-the-art",
    "paradigm shift",
    "game-changer",
    "indelible mark",
    "deeply rooted",
    "focal point",
    "key turning point",
    "setting the stage for",
    "marking a pivotal moment",
    "enduring testament",
    "evolving landscape",
    "enduring legacy",
    "profound impact",
    # ── Metaphorical cliché ──
    "delve into",
    "shed light on",
    "pave the way",
    "a myriad of",
    "in the realm of",
    "a testament to",
    "at the forefront",
    "the landscape of",
    "cornerstone of",
    "tapestry of",
    "stands as",
    "rich tapestry",
    "intricate tapestry",
    "vibrant tapestry",
    # ── Promotional language (Pattern 4) ──
    "breathtaking",
    "must-visit",
    "nestled in",
    "in the heart of",
    "natural beauty",
    "boasts a",
    "exemplifies",
    "commitment to excellence",
    # ── Vague academic padding ──
    "multifaceted",
    "underscores the importance",
    "underscores the need",
    "highlights the importance",
    "notably",
    "leveraging",
    "utilizing",
    "a growing body of evidence",
    "has emerged as",
    "increasingly recognized",
    "is of paramount importance",
    "remains an area of active research",
    "warrants further investigation",
    "merits further investigation",
    "nuanced understanding",
    "robust framework",
    "holistic approach",
    # ── AI vocabulary (Pattern 7: High-frequency AI words) ──
    "aligns with",
    "underscores",
    "fostering",
    "showcasing",
    "intricate",
    "intricacies",
    "interplay of",
    "pivotal",
    # ── Copula avoidance (Pattern 8) ──
    "serves as a",
    "stands as a",
    "functions as a",
    # ── Formulaic conclusion / transition ──
    "in conclusion, our study",
    "in summary, this study",
    "taken together, these findings",
    "in light of these findings",
    "despite these challenges",
    "to the best of our knowledge",
    "first and foremost",
    "a deeper understanding",
    "this study adds to the growing literature",
    "this highlights the need",
    "the importance of this cannot be overstated",
    # ── Generic conclusions (Pattern 24) ──
    "the future looks bright",
    "exciting times lie ahead",
    "continues to thrive",
    "journey toward excellence",
    "as we move forward",
    "continues to evolve",
    # ── AI-specific phrasing patterns ──
    "demonstrate the efficacy",
    "elucidate the mechanisms",
    "elucidating",
    "meticulous",
    "bolster",
    "a critical aspect",
    "serve as a foundation",
    "offers a promising avenue",
    # ── Filler phrases (Pattern 22) ──
    "in order to",
    "due to the fact that",
    "at this point in time",
    "in the event that",
    "has the ability to",
    "it goes without saying",
    "needless to say",
    # ── Chatbot artifacts (Pattern 19) ──
    "i hope this helps",
    "let me know if",
    "here is a comprehensive",
    "here's a comprehensive",
    # ── Cutoff disclaimers (Pattern 20) ──
    "while details are limited",
    "based on available information",
    "as of my last",
    # ── Sycophantic tone (Pattern 21) ──
    "great question",
    "excellent point",
    # ── Vague attributions (Pattern 5) ──
    "many scholars argue",
    "experts believe",
    "it is widely believed",
    "according to many",
    "some researchers suggest",
]

# These phrases are only flagged at paragraph start (not mid-sentence).
ANTI_AI_PARAGRAPH_START_ONLY: list[str] = [
    "furthermore",
    "moreover",
    "additionally",
    "in summary",
    "it is noteworthy that",
    "importantly",
    "interestingly",
    "remarkably",
]

# ── Structural AI signal: transition / connector words ─────────────
# Overuse of these at sentence start signals AI-generated text.
AI_TRANSITION_WORDS: set[str] = {
    "additionally",
    "also",
    "collectively",
    "consequently",
    "conversely",
    "correspondingly",
    "crucially",
    "essentially",
    "fundamentally",
    "furthermore",
    "hence",
    "however",
    "importantly",
    "indeed",
    "interestingly",
    "likewise",
    "meanwhile",
    "moreover",
    "nevertheless",
    "nonetheless",
    "notably",
    "overall",
    "remarkably",
    "significantly",
    "similarly",
    "specifically",
    "strikingly",
    "subsequently",
    "therefore",
    "thus",
    "ultimately",
    "undeniably",
    "undoubtedly",
}

# ── Negative parallelism patterns (Pattern 9) ──────────────────────
# "not just X, it's Y" / "not only X, but (also) Y" — overused by AI
AI_NEGATIVE_PARALLELISM_PATTERNS: list[str] = [
    r"\bnot\s+just\b[^.]{3,40},\s*(?:it(?:'s|\s+is)|but)\b",
    r"\bnot\s+only\b[^.]{3,40},?\s*but\s+(?:also\s+)?",
    r"\bnot\s+merely\b[^.]{3,40},?\s*but\b",
]

# ── Copula avoidance verbs (Pattern 8) ─────────────────────────────
# AI avoids "is/has" by substituting impressive-sounding verbs.
AI_COPULA_AVOIDANCE_VERBS: list[str] = [
    "serves as",
    "stands as",
    "functions as",
    "acts as",
    "remains",
    "represents",
    "constitutes",
    "embodies",
]

# ── False range patterns (Pattern 12) ──────────────────────────────
# "from X to Y" — AI loves enumerating vague ranges.
AI_FALSE_RANGE_PATTERN: str = r"\bfrom\s+\w+(?:\s+\w+)?\s+to\s+\w+(?:\s+\w+)?"

# ── Em dash pattern (Pattern 13) ───────────────────────────────────
# AI overuses em dashes (—) for parenthetical asides.
AI_EM_DASH_PATTERN: str = r"—"
