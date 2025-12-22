"""
Shared constants used across the application.
"""

# Paper types with their characteristics
PAPER_TYPES = {
    "original-research": {
        "name": "Original Research",
        "sections": ["Introduction", "Methods", "Results", "Discussion", "Conclusion"],
        "description": "Clinical trial, cohort study, cross-sectional study",
    },
    "systematic-review": {
        "name": "Systematic Review",
        "sections": ["Introduction", "Methods", "Results", "Discussion", "Conclusion"],
        "description": "Systematic literature review without meta-analysis",
    },
    "meta-analysis": {
        "name": "Meta-Analysis",
        "sections": ["Introduction", "Methods", "Results", "Discussion", "Conclusion"],
        "description": "Systematic review with quantitative synthesis",
    },
    "case-report": {
        "name": "Case Report",
        "sections": ["Introduction", "Case Presentation", "Discussion", "Conclusion"],
        "description": "Single case or case series",
    },
    "review-article": {
        "name": "Review Article",
        "sections": ["Introduction", "Main Body", "Conclusion"],
        "description": "Narrative or invited review",
    },
    "letter": {
        "name": "Letter to the Editor",
        "sections": ["Main Text"],
        "description": "Brief communication or correspondence",
    },
    "other": {
        "name": "Other",
        "sections": ["Introduction", "Main Body", "Conclusion"],
        "description": "Editorial, perspective, commentary, etc.",
    },
}

# Default word limits for journal sections
DEFAULT_WORD_LIMITS = {
    "Abstract": 250,
    "Introduction": 800,
    "Methods": 1500,
    "Materials and Methods": 1500,
    "Results": 1500,
    "Discussion": 1500,
    "Conclusions": 300,
}

# Project directory structure
PROJECT_DIRECTORIES = ["drafts", "references", "data", "results", ".memory"]

# Citation styles
CITATION_STYLES = ["vancouver", "apa", "harvard", "nature", "ama", "nlm", "mdpi"]
