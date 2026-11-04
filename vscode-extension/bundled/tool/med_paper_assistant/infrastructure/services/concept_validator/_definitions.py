"""Static configuration for concept validation: section patterns, novelty and cache settings."""

# Section definitions for structural validation
SECTION_DEFINITIONS = {
    "novelty_statement": {
        "name": "🔒 NOVELTY STATEMENT",
        "required": True,
        "patterns": [r"🔒\s*NOVELTY STATEMENT", r"What is new\?", r"##.*novelty"],
        "min_words": 20,
    },
    "selling_points": {
        "name": "🔒 KEY SELLING POINTS",
        "required": True,
        "patterns": [
            r"🔒\s*KEY SELLING POINTS",
            r"#+.*KEY SELLING POINTS",
            r"Selling Point \d",
        ],
        "min_count": 3,
    },
    "background": {
        "name": "📝 Background",
        "required": False,
        "patterns": [
            r"📝\s*Background",
            r"##\s*Background",
            r"##\s*Project Background",
            r"##\s*Background and Rationale",
        ],
        "min_words": 30,
    },
    "research_gap": {
        "name": "📝 Research Gap",
        "required": False,
        "patterns": [r"📝\s*Research Gap", r"##\s*Research Gap", r"Identified Gap"],
        "min_words": 20,
    },
    "research_question": {
        "name": "📝 Research Question",
        "required": False,
        "patterns": [
            r"Research Question",
            r"Hypothesis",
            r"PICO",
            r"##\s*Objectives?",
            r"##\s*Thesis Statement",
        ],
        "min_words": 10,
    },
    "methods": {
        "name": "📝 Methods Overview",
        "required": False,
        "patterns": [
            r"📝\s*Methods",
            r"##\s*Methods",
            r"##\s*Methodology",
            r"##\s*Activities and Methods",
            r"Study Design",
        ],
        "min_words": 20,
    },
    "expected_outcomes": {
        "name": "📝 Expected Outcomes",
        "required": False,
        "patterns": [
            r"📝\s*Expected",
            r"##\s*Expected Outcomes",
            r"##\s*Expected Impact",
            r"##\s*Results and Deliverables",
            r"##\s*Learning Outcomes",
            r"Primary Outcomes",
        ],
        "min_words": 15,
    },
}

# Novelty scoring configuration
NOVELTY_CONFIG = {
    "rounds": 3,
    "threshold": 75,
    "required_passing_rounds": 3,  # All rounds must pass
}

# Cache settings
CACHE_DURATION_HOURS = 24
