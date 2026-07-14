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
        "sections": ["Introduction", "Body (multiple sections)", "Conclusion"],
        "description": "Narrative review or invited review",
    },
    "letter": {
        "name": "Letter / Correspondence",
        "sections": ["Main Text"],
        "description": "Brief communication or commentary",
    },
    "research-proposal": {
        "name": "Research Proposal",
        "sections": [
            "Executive Summary",
            "Background and Rationale",
            "Objectives",
            "Methods",
            "Timeline",
            "Ethics and Data Management",
            "Budget and Resources",
            "Expected Impact",
        ],
        "description": "Grant, protocol, dissertation, or institutional research plan",
    },
    "project-closeout-report": {
        "name": "Project Closeout Report",
        "sections": [
            "Executive Summary",
            "Objectives",
            "Activities and Methods",
            "Results and Deliverables",
            "Deviations and Corrective Actions",
            "Budget and Resources",
            "Lessons Learned",
            "Data and Artifact Disposition",
            "Conclusion",
        ],
        "description": "Auditable final report of objectives, delivery, variance, and lessons learned",
    },
    "student-paper": {
        "name": "Student Paper",
        "sections": [
            "Abstract",
            "Introduction",
            "Literature Review",
            "Main Analysis",
            "Discussion",
            "Conclusion",
            "References",
        ],
        "description": "Course paper, capstone, term paper, or assessed academic essay",
    },
    "conference-paper": {
        "name": "Conference Paper",
        "sections": ["Abstract", "Introduction", "Methods", "Results", "Discussion", "Conclusion"],
        "description": "Full conference paper or proceedings manuscript",
    },
    "thesis-dissertation": {
        "name": "Thesis / Dissertation",
        "sections": [
            "Abstract",
            "Introduction",
            "Literature Review",
            "Methods",
            "Results",
            "Discussion",
            "Conclusion",
        ],
        "description": "Degree thesis or dissertation with chapter-level evidence and methods",
    },
    "arxiv-preprint": {
        "name": "arXiv / Repository Preprint",
        "sections": [
            "Abstract",
            "Introduction",
            "Methods",
            "Results",
            "Discussion",
            "Conclusion",
            "Data and Code Availability",
            "Version Notes",
        ],
        "description": "Versioned scholarly preprint prepared for a public repository",
    },
    "other": {
        "name": "Other",
        "sections": ["Varies"],
        "description": "Editorial, perspective, methodology paper, etc.",
    },
}

WORKFLOW_MODES = {
    "manuscript": {
        "name": "Manuscript Path",
        "description": "Concept -> draft -> review -> export",
    },
    "library-wiki": {
        "name": "Library Wiki Path",
        "description": "Ingest -> organize -> analyze -> synthesize -> query",
    },
}

DEFAULT_WORKFLOW_MODE = "manuscript"

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
PROJECT_DIRECTORIES = ["drafts", "references", "data", "results", "exports", ".audit", ".memory"]
LIBRARY_DIRECTORIES = [
    "inbox",
    "concepts",
    "projects",
    "review",
    "daily",
    "references",
    ".audit",
    ".memory",
]

# Citation styles
CITATION_STYLES = ["vancouver", "apa", "harvard", "nature", "ama", "nlm", "mdpi"]
