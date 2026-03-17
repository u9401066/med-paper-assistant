#!/usr/bin/env python3
"""Generate journal-profile YAML files for top 20 anesthesiology journals.

Each generated file follows the journal-profile.template.yaml schema
and can be directly copied to projects/{slug}/journal-profile.yaml.

Data sources:
- Official author instruction pages (URLs in each profile)
- RAPM: verified from https://rapm.bmj.com/pages/authors/ (2026-03)
- EJA: verified from http://edmgr.ovid.com/eja/accounts/ifauth.htm (2026-03)
- KJA: verified from https://ekja.org/authors/authors.php (2026-03)
- Others: compiled from known author guidelines (verify via guidelines_url)
"""

from datetime import date
from pathlib import Path

import yaml

# ─── Journal Data ───────────────────────────────────────────────────────

JOURNALS = [
    # ── 1. British Journal of Anaesthesia ──
    {
        "slug": "bja",
        "journal": {
            "name": "British Journal of Anaesthesia",
            "abbreviation": "Br J Anaesth",
            "issn_print": "0007-0912",
            "issn_online": "1471-6771",
            "publisher": "Oxford University Press / NIAA",
            "submission_url": "https://mc.manuscriptcentral.com/bja",
            "guidelines_url": "https://academic.oup.com/bja/pages/general-instructions",
        },
        "word_limits": {
            "total_manuscript": 3000,
            "abstract": 250,
            "title_characters": 150,
            "running_title_characters": 50,
        },
        "abstract_structured": True,
        "abstract_headings": "Background, Methods, Results, Conclusions",
        "assets": {
            "figures_max": 6,
            "tables_max": 6,
            "total_display_items_max": 8,
            "figure_formats": ["TIFF", "EPS", "PDF", "PNG"],
            "figure_dpi": 300,
        },
        "references": {
            "style": "vancouver",
            "max_references": 30,
            "max_authors_before_etal": 6,
            "doi_required": False,
            "pmid_preferred": True,
            "reference_limits": {
                "original-research": 30,
                "review-article": 80,
                "systematic-review": 80,
                "meta-analysis": 80,
                "case-report": 10,
                "letter": 5,
            },
            "minimum_reference_limits": {
                "original-research": 20,
                "review-article": 30,
                "case-report": 5,
                "letter": 0,
            },
        },
        "required_documents": {
            "cover_letter": True,
            "highlights": False,
            "graphical_abstract": False,
            "author_contributions": True,
            "conflict_of_interest": True,
            "funding_statement": True,
            "ethics_statement": True,
            "data_availability": True,
            "keywords": {"required": True, "count": "3-6"},
        },
        "reporting_guidelines": {
            "checklist": "required (CONSORT/STROBE/PRISMA as appropriate)",
            "registration_required": True,
        },
        "sections": [
            {"name": "Title Page", "required": True},
            {"name": "Abstract", "required": True, "structured": True, "word_limit": 250},
            {"name": "Introduction", "required": True},
            {"name": "Methods", "required": True},
            {"name": "Results", "required": True},
            {"name": "Discussion", "required": True},
            {"name": "Conclusions", "required": False},
        ],
        "other_article_types": {
            "case-report": {"word_limit": 1500, "abstract": 150, "references": 10},
            "review-article": {"word_limit": 4000, "abstract": 250, "references": 80},
            "letter": {"word_limit": 600, "abstract": 0, "references": 5},
            "editorial": {"word_limit": 1500, "abstract": 0, "references": 15},
        },
    },
    # ── 2. Anesthesiology ──
    {
        "slug": "anesthesiology",
        "journal": {
            "name": "Anesthesiology",
            "abbreviation": "Anesthesiology",
            "issn_print": "0003-3022",
            "issn_online": "1528-1175",
            "publisher": "Wolters Kluwer / American Society of Anesthesiologists",
            "submission_url": "https://www.editorialmanager.com/aln/",
            "guidelines_url": "https://pubs.asahq.org/anesthesiology/pages/instructions-for-authors",
        },
        "word_limits": {
            "total_manuscript": 4500,
            "abstract": 350,
            "title_characters": 150,
            "running_title_characters": 50,
        },
        "abstract_structured": True,
        "abstract_headings": "Background, Methods, Results, Conclusions",
        "assets": {
            "figures_max": 8,
            "tables_max": 8,
            "total_display_items_max": 8,
            "figure_formats": ["TIFF", "EPS", "PDF"],
            "figure_dpi": 300,
        },
        "references": {
            "style": "vancouver",
            "max_references": 50,
            "max_authors_before_etal": 6,
            "doi_required": False,
            "pmid_preferred": True,
            "reference_limits": {
                "original-research": 50,
                "review-article": 80,
                "systematic-review": 80,
                "meta-analysis": 80,
                "case-report": 15,
                "letter": 10,
            },
            "minimum_reference_limits": {
                "original-research": 25,
                "review-article": 40,
                "case-report": 5,
                "letter": 0,
            },
        },
        "required_documents": {
            "cover_letter": True,
            "highlights": False,
            "graphical_abstract": False,
            "author_contributions": True,
            "conflict_of_interest": True,
            "funding_statement": True,
            "ethics_statement": True,
            "data_availability": True,
            "keywords": {"required": True, "count": "4-6"},
        },
        "reporting_guidelines": {
            "checklist": "required (CONSORT/STROBE/PRISMA as appropriate)",
            "registration_required": True,
        },
        "sections": [
            {"name": "Title Page", "required": True},
            {"name": "Abstract", "required": True, "structured": True, "word_limit": 350},
            {"name": "Introduction", "required": True},
            {"name": "Methods", "required": True},
            {"name": "Results", "required": True},
            {"name": "Discussion", "required": True},
        ],
        "other_article_types": {
            "case-report": {"word_limit": 2000, "abstract": 200, "references": 15},
            "review-article": {"word_limit": 5000, "abstract": 350, "references": 80},
            "letter": {"word_limit": 750, "abstract": 0, "references": 10},
            "editorial": {"word_limit": 2000, "abstract": 0, "references": 20},
        },
    },
    # ── 3. Anaesthesia ──
    {
        "slug": "anaesthesia",
        "journal": {
            "name": "Anaesthesia",
            "abbreviation": "Anaesthesia",
            "issn_print": "0003-2409",
            "issn_online": "1365-2044",
            "publisher": "Wiley / Association of Anaesthetists",
            "submission_url": "https://mc.manuscriptcentral.com/anae",
            "guidelines_url": "https://anaesthesia.onlinelibrary.wiley.com/hub/journal/13652044/homepage/ForAuthors",
        },
        "word_limits": {
            "total_manuscript": 3000,
            "abstract": 200,
            "title_characters": 120,
            "running_title_characters": 50,
        },
        "abstract_structured": True,
        "abstract_headings": "Background, Methods, Results, Conclusions",
        "assets": {
            "figures_max": 5,
            "tables_max": 5,
            "total_display_items_max": 6,
            "figure_formats": ["TIFF", "EPS", "PDF", "PNG"],
            "figure_dpi": 300,
        },
        "references": {
            "style": "vancouver",
            "max_references": 30,
            "max_authors_before_etal": 6,
            "doi_required": False,
            "pmid_preferred": True,
            "reference_limits": {
                "original-research": 30,
                "review-article": 60,
                "systematic-review": 60,
                "meta-analysis": 60,
                "case-report": 10,
                "letter": 5,
            },
            "minimum_reference_limits": {
                "original-research": 15,
                "review-article": 30,
                "case-report": 5,
                "letter": 0,
            },
        },
        "required_documents": {
            "cover_letter": True,
            "highlights": False,
            "graphical_abstract": False,
            "author_contributions": True,
            "conflict_of_interest": True,
            "funding_statement": True,
            "ethics_statement": True,
            "data_availability": True,
            "keywords": {"required": True, "count": "3-5"},
        },
        "reporting_guidelines": {
            "checklist": "required (CONSORT/STROBE/PRISMA as appropriate)",
            "registration_required": True,
        },
        "sections": [
            {"name": "Title Page", "required": True},
            {"name": "Abstract", "required": True, "structured": True, "word_limit": 200},
            {"name": "Introduction", "required": True},
            {"name": "Methods", "required": True},
            {"name": "Results", "required": True},
            {"name": "Discussion", "required": True},
        ],
        "other_article_types": {
            "case-report": {"word_limit": 1500, "abstract": 100, "references": 10},
            "review-article": {"word_limit": 4000, "abstract": 200, "references": 60},
            "letter": {"word_limit": 500, "abstract": 0, "references": 5},
            "editorial": {"word_limit": 1500, "abstract": 0, "references": 10},
        },
    },
    # ── 4. Regional Anesthesia & Pain Medicine (RAPM) ── VERIFIED 2026-03
    {
        "slug": "rapm",
        "journal": {
            "name": "Regional Anesthesia & Pain Medicine",
            "abbreviation": "Reg Anesth Pain Med",
            "issn_print": "1098-7339",
            "issn_online": "1532-8651",
            "publisher": "BMJ Publishing Group / ASRA Pain Medicine",
            "submission_url": "https://mc.manuscriptcentral.com/rapm",
            "guidelines_url": "https://rapm.bmj.com/pages/authors/",
        },
        "word_limits": {
            "total_manuscript": 3000,
            "abstract": 250,
            "title_characters": 150,
            "running_title_characters": 50,
            "introduction_max": 500,
        },
        "abstract_structured": True,
        "abstract_headings": "Background, Methods, Results, Conclusions",
        "assets": {
            "figures_max": 5,
            "tables_max": 5,
            "total_display_items_max": 5,
            "figure_formats": ["TIFF", "PDF", "PNG"],
            "figure_dpi": 300,
        },
        "references": {
            "style": "vancouver",
            "max_references": 30,
            "max_authors_before_etal": 6,
            "doi_required": False,
            "pmid_preferred": True,
            "reference_limits": {
                "original-research": 30,
                "review-article": 75,
                "systematic-review": 75,
                "meta-analysis": 75,
                "case-report": 25,
                "letter": 6,
            },
            "minimum_reference_limits": {
                "original-research": 15,
                "review-article": 30,
                "case-report": 5,
                "letter": 0,
            },
        },
        "required_documents": {
            "cover_letter": True,
            "highlights": False,
            "graphical_abstract": False,
            "author_contributions": True,
            "conflict_of_interest": True,
            "funding_statement": True,
            "ethics_statement": True,
            "data_availability": True,
            "keywords": {"required": True, "count": "3-5"},
            "key_messages": True,
        },
        "reporting_guidelines": {
            "checklist": "required (EQUATOR network guidelines)",
            "registration_required": True,
            "protocol_registration": "PROSPERO (for systematic reviews)",
        },
        "sections": [
            {"name": "Title Page", "required": True},
            {"name": "Abstract", "required": True, "structured": True, "word_limit": 250},
            {"name": "Key Messages", "required": True},
            {"name": "Introduction", "required": True, "word_limit": 500},
            {"name": "Methods", "required": True},
            {"name": "Results", "required": True},
            {"name": "Discussion", "required": True},
        ],
        "other_article_types": {
            "case-report": {"word_limit": 2000, "abstract": 250, "references": 25},
            "review-article": {"word_limit": 3500, "abstract": 250, "references": 75},
            "letter": {"word_limit": 600, "abstract": 0, "references": 6},
            "editorial": {"word_limit": 1500, "abstract": 0, "references": 10},
            "brief-technical-report": {"word_limit": 2500, "abstract": 250, "references": 20},
            "research-letter": {"word_limit": 600, "abstract": 0, "references": 6},
            "education-article": {"word_limit": 4000, "abstract": 0, "references": 20},
        },
    },
    # ── 5. Anesthesia & Analgesia ──
    {
        "slug": "aanda",
        "journal": {
            "name": "Anesthesia & Analgesia",
            "abbreviation": "Anesth Analg",
            "issn_print": "0003-2999",
            "issn_online": "1526-7598",
            "publisher": "Wolters Kluwer / IARS",
            "submission_url": "https://www.editorialmanager.com/aa/",
            "guidelines_url": "https://journals.lww.com/anesthesia-analgesia/pages/informationforauthors.aspx",
        },
        "word_limits": {
            "total_manuscript": 3000,
            "abstract": 400,
            "title_characters": 120,
            "running_title_characters": 45,
        },
        "abstract_structured": True,
        "abstract_headings": "Background, Methods, Results, Conclusions",
        "assets": {
            "figures_max": 6,
            "tables_max": 6,
            "total_display_items_max": 6,
            "figure_formats": ["TIFF", "EPS", "PDF"],
            "figure_dpi": 300,
        },
        "references": {
            "style": "vancouver",
            "max_references": 50,
            "max_authors_before_etal": 6,
            "doi_required": False,
            "pmid_preferred": True,
            "reference_limits": {
                "original-research": 50,
                "review-article": 75,
                "systematic-review": 75,
                "meta-analysis": 75,
                "case-report": 10,
                "letter": 5,
            },
            "minimum_reference_limits": {
                "original-research": 20,
                "review-article": 30,
                "case-report": 5,
                "letter": 0,
            },
        },
        "required_documents": {
            "cover_letter": True,
            "highlights": True,
            "graphical_abstract": False,
            "author_contributions": True,
            "conflict_of_interest": True,
            "funding_statement": True,
            "ethics_statement": True,
            "data_availability": True,
            "keywords": {"required": True, "count": "3-6"},
        },
        "reporting_guidelines": {
            "checklist": "required (CONSORT/STROBE/PRISMA as appropriate)",
            "registration_required": True,
        },
        "sections": [
            {"name": "Title Page", "required": True},
            {"name": "Abstract", "required": True, "structured": True, "word_limit": 400},
            {"name": "Key Points", "required": True},
            {"name": "Introduction", "required": True},
            {"name": "Methods", "required": True},
            {"name": "Results", "required": True},
            {"name": "Discussion", "required": True},
        ],
        "other_article_types": {
            "case-report": {"word_limit": 1500, "abstract": 200, "references": 10},
            "review-article": {"word_limit": 5000, "abstract": 400, "references": 75},
            "letter": {"word_limit": 500, "abstract": 0, "references": 5},
            "editorial": {"word_limit": 1500, "abstract": 0, "references": 15},
        },
    },
    # ── 6. European Journal of Anaesthesiology (EJA) ── VERIFIED 2026-03
    {
        "slug": "eja",
        "journal": {
            "name": "European Journal of Anaesthesiology",
            "abbreviation": "Eur J Anaesthesiol",
            "issn_print": "0265-0215",
            "issn_online": "1365-2346",
            "publisher": "Wolters Kluwer / ESAIC",
            "submission_url": "https://www.editorialmanager.com/eja/",
            "guidelines_url": "http://edmgr.ovid.com/eja/accounts/ifauth.htm",
        },
        "word_limits": {
            "total_manuscript": 3500,
            "abstract": 300,
            "title_characters": 150,
            "running_title_characters": 50,
        },
        "abstract_structured": True,
        "abstract_headings": "Background, Objective(s), Design, Setting, Patients/Participants, Intervention(s), Main outcome measures, Results, Conclusions, Trial registration",
        "assets": {
            "figures_max": 6,
            "tables_max": 6,
            "total_display_items_max": 8,
            "figure_formats": ["TIFF", "EPS", "DOC", "PPT"],
            "figure_dpi": 300,
        },
        "references": {
            "style": "vancouver",
            "max_references": 40,
            "max_authors_before_etal": 3,
            "doi_required": False,
            "pmid_preferred": True,
            "reference_limits": {
                "original-research": 40,
                "review-article": 60,
                "systematic-review": 60,
                "meta-analysis": 60,
                "case-report": 7,
                "letter": 7,
            },
            "minimum_reference_limits": {
                "original-research": 20,
                "review-article": 30,
                "case-report": 3,
                "letter": 0,
            },
        },
        "required_documents": {
            "cover_letter": True,
            "highlights": False,
            "graphical_abstract": False,
            "author_contributions": True,
            "conflict_of_interest": True,
            "funding_statement": True,
            "ethics_statement": True,
            "data_availability": True,
            "keywords": {"required": True, "count": "3-5"},
            "key_points": True,
            "credit_taxonomy": True,
        },
        "reporting_guidelines": {
            "checklist": "required (CONSORT/STROBE/PRISMA/MOOSE/ARRIVE/STARD/CARE/SQUIRE)",
            "registration_required": True,
            "protocol_registration": "PROSPERO (mandatory for systematic reviews)",
        },
        "sections": [
            {"name": "Title Page", "required": True},
            {"name": "Abstract", "required": True, "structured": True, "word_limit": 300},
            {"name": "Key Points", "required": True},
            {"name": "Introduction", "required": True},
            {"name": "Methods", "required": True},
            {"name": "Results", "required": True},
            {"name": "Discussion", "required": True},
        ],
        "other_article_types": {
            "case-report": {"word_limit": 1000, "abstract": 0, "references": 7, "max_authors": 4},
            "review-article": {
                "word_limit": 3500,
                "abstract": 250,
                "references": 60,
                "note": "unstructured abstract for narrative reviews",
            },
            "letter": {"word_limit": 1000, "abstract": 0, "references": 7, "max_authors": 4},
            "editorial": {"word_limit": 1500, "abstract": 0, "references": 15},
            "short-scientific-report": {
                "word_limit": 1000,
                "abstract": 0,
                "references": 7,
                "max_authors": 4,
            },
            "pro-con-debate": {"word_limit": 2000, "abstract": 200, "references": 20},
        },
        "notes": "UK spelling preferred. 1.5 spacing. Visual abstracts for selected submissions.",
    },
    # ── 7. Canadian Journal of Anesthesia ──
    {
        "slug": "cja",
        "journal": {
            "name": "Canadian Journal of Anesthesia / Journal canadien d'anesthésie",
            "abbreviation": "Can J Anaesth",
            "issn_print": "0832-610X",
            "issn_online": "1496-8975",
            "publisher": "Springer / Canadian Anesthesiologists' Society",
            "submission_url": "https://www.editorialmanager.com/cja/",
            "guidelines_url": "https://www.springer.com/journal/12630/submission-guidelines",
        },
        "word_limits": {
            "total_manuscript": 3000,
            "abstract": 250,
            "title_characters": 150,
            "running_title_characters": 50,
        },
        "abstract_structured": True,
        "abstract_headings": "Purpose, Methods, Results, Conclusions",
        "assets": {
            "figures_max": 6,
            "tables_max": 6,
            "total_display_items_max": 6,
            "figure_formats": ["TIFF", "EPS", "PDF", "PNG"],
            "figure_dpi": 300,
        },
        "references": {
            "style": "vancouver",
            "max_references": 40,
            "max_authors_before_etal": 6,
            "doi_required": False,
            "pmid_preferred": True,
            "reference_limits": {
                "original-research": 40,
                "review-article": 60,
                "systematic-review": 60,
                "meta-analysis": 60,
                "case-report": 15,
                "letter": 5,
            },
            "minimum_reference_limits": {
                "original-research": 20,
                "review-article": 30,
                "case-report": 5,
                "letter": 0,
            },
        },
        "required_documents": {
            "cover_letter": True,
            "highlights": False,
            "graphical_abstract": False,
            "author_contributions": True,
            "conflict_of_interest": True,
            "funding_statement": True,
            "ethics_statement": True,
            "data_availability": True,
            "keywords": {"required": True, "count": "3-5"},
        },
        "reporting_guidelines": {
            "checklist": "required (CONSORT/STROBE/PRISMA as appropriate)",
            "registration_required": True,
        },
        "sections": [
            {"name": "Title Page", "required": True},
            {"name": "Abstract", "required": True, "structured": True, "word_limit": 250},
            {"name": "Introduction", "required": True},
            {"name": "Methods", "required": True},
            {"name": "Results", "required": True},
            {"name": "Discussion", "required": True},
        ],
        "other_article_types": {
            "case-report": {"word_limit": 1500, "abstract": 150, "references": 15},
            "review-article": {"word_limit": 4000, "abstract": 250, "references": 60},
            "letter": {"word_limit": 500, "abstract": 0, "references": 5},
            "editorial": {"word_limit": 1500, "abstract": 0, "references": 15},
        },
    },
    # ── 8. Journal of Clinical Anesthesia ──
    {
        "slug": "jca",
        "journal": {
            "name": "Journal of Clinical Anesthesia",
            "abbreviation": "J Clin Anesth",
            "issn_print": "0952-8180",
            "issn_online": "1873-4529",
            "publisher": "Elsevier",
            "submission_url": "https://www.editorialmanager.com/jclinane/",
            "guidelines_url": "https://www.sciencedirect.com/journal/journal-of-clinical-anesthesia/publish/guide-for-authors",
        },
        "word_limits": {
            "total_manuscript": 3000,
            "abstract": 250,
            "title_characters": 150,
            "running_title_characters": 50,
        },
        "abstract_structured": True,
        "abstract_headings": "Study Objective, Design, Setting, Patients, Interventions, Measurements, Main Results, Conclusions",
        "assets": {
            "figures_max": 6,
            "tables_max": 6,
            "total_display_items_max": 8,
            "figure_formats": ["TIFF", "EPS", "PDF", "JPEG", "PNG"],
            "figure_dpi": 300,
        },
        "references": {
            "style": "vancouver",
            "max_references": 40,
            "max_authors_before_etal": 6,
            "doi_required": False,
            "pmid_preferred": True,
            "reference_limits": {
                "original-research": 40,
                "review-article": 60,
                "systematic-review": 60,
                "meta-analysis": 60,
                "case-report": 15,
                "letter": 5,
            },
            "minimum_reference_limits": {
                "original-research": 15,
                "review-article": 25,
                "case-report": 5,
                "letter": 0,
            },
        },
        "required_documents": {
            "cover_letter": True,
            "highlights": True,
            "graphical_abstract": False,
            "author_contributions": True,
            "conflict_of_interest": True,
            "funding_statement": True,
            "ethics_statement": True,
            "data_availability": True,
            "keywords": {"required": True, "count": "3-6"},
        },
        "reporting_guidelines": {
            "checklist": "recommended (CONSORT/STROBE/PRISMA)",
            "registration_required": True,
        },
        "sections": [
            {"name": "Title Page", "required": True},
            {"name": "Abstract", "required": True, "structured": True, "word_limit": 250},
            {"name": "Introduction", "required": True},
            {"name": "Methods", "required": True},
            {"name": "Results", "required": True},
            {"name": "Discussion", "required": True},
        ],
        "other_article_types": {
            "case-report": {"word_limit": 1500, "abstract": 150, "references": 15},
            "review-article": {"word_limit": 4000, "abstract": 250, "references": 60},
            "letter": {"word_limit": 500, "abstract": 0, "references": 5},
        },
    },
    # ── 9. Current Opinion in Anaesthesiology ──
    {
        "slug": "current-opinion-anaesthesiology",
        "journal": {
            "name": "Current Opinion in Anaesthesiology",
            "abbreviation": "Curr Opin Anaesthesiol",
            "issn_print": "0952-7907",
            "issn_online": "1473-6500",
            "publisher": "Wolters Kluwer",
            "submission_url": "https://www.editorialmanager.com/coa/",
            "guidelines_url": "https://journals.lww.com/co-anesthesiology/pages/informationforauthors.aspx",
        },
        "word_limits": {
            "total_manuscript": 3500,
            "abstract": 200,
            "title_characters": 150,
            "running_title_characters": 50,
        },
        "abstract_structured": False,
        "abstract_headings": "Purpose of review, Recent findings, Summary",
        "assets": {
            "figures_max": 4,
            "tables_max": 4,
            "total_display_items_max": 6,
            "figure_formats": ["TIFF", "EPS", "PDF"],
            "figure_dpi": 300,
        },
        "references": {
            "style": "vancouver",
            "max_references": 50,
            "max_authors_before_etal": 6,
            "doi_required": False,
            "pmid_preferred": True,
            "reference_limits": {
                "review-article": 50,
            },
            "minimum_reference_limits": {
                "review-article": 20,
            },
        },
        "required_documents": {
            "cover_letter": True,
            "highlights": False,
            "graphical_abstract": False,
            "author_contributions": True,
            "conflict_of_interest": True,
            "funding_statement": True,
            "ethics_statement": False,
            "data_availability": False,
            "keywords": {"required": True, "count": "3-5"},
        },
        "reporting_guidelines": {
            "checklist": "PRISMA (for systematic reviews)",
            "registration_required": False,
        },
        "sections": [
            {"name": "Title Page", "required": True},
            {"name": "Abstract", "required": True, "structured": False, "word_limit": 200},
            {"name": "Introduction", "required": True},
            {"name": "Body", "required": True},
            {"name": "Conclusion", "required": True},
        ],
        "notes": "Review-only journal. Articles typically commissioned.",
        "default_paper_type": "review-article",
    },
    # ── 10. Minerva Anestesiologica ──
    {
        "slug": "minerva-anestesiologica",
        "journal": {
            "name": "Minerva Anestesiologica",
            "abbreviation": "Minerva Anestesiol",
            "issn_print": "0375-9393",
            "issn_online": "1827-1596",
            "publisher": "Edizioni Minerva Medica",
            "submission_url": "https://www.editorialmanager.com/minane/",
            "guidelines_url": "https://www.minervamedica.it/en/journals/minerva-anestesiologica/notice-to-authors.php",
        },
        "word_limits": {
            "total_manuscript": 4000,
            "abstract": 250,
            "title_characters": 150,
            "running_title_characters": 50,
        },
        "abstract_structured": True,
        "abstract_headings": "Background, Methods, Results, Conclusions",
        "assets": {
            "figures_max": 6,
            "tables_max": 6,
            "total_display_items_max": 8,
            "figure_formats": ["TIFF", "EPS", "JPEG"],
            "figure_dpi": 300,
        },
        "references": {
            "style": "vancouver",
            "max_references": 40,
            "max_authors_before_etal": 6,
            "doi_required": False,
            "pmid_preferred": True,
            "reference_limits": {
                "original-research": 40,
                "review-article": 60,
                "systematic-review": 60,
                "meta-analysis": 60,
                "case-report": 15,
                "letter": 5,
            },
            "minimum_reference_limits": {
                "original-research": 20,
                "review-article": 30,
                "case-report": 5,
                "letter": 0,
            },
        },
        "required_documents": {
            "cover_letter": True,
            "highlights": False,
            "graphical_abstract": False,
            "author_contributions": True,
            "conflict_of_interest": True,
            "funding_statement": True,
            "ethics_statement": True,
            "data_availability": True,
            "keywords": {"required": True, "count": "3-5"},
        },
        "reporting_guidelines": {
            "checklist": "recommended (CONSORT/STROBE/PRISMA)",
            "registration_required": True,
        },
        "sections": [
            {"name": "Title Page", "required": True},
            {"name": "Abstract", "required": True, "structured": True, "word_limit": 250},
            {"name": "Introduction", "required": True},
            {"name": "Methods", "required": True},
            {"name": "Results", "required": True},
            {"name": "Discussion", "required": True},
        ],
        "other_article_types": {
            "case-report": {"word_limit": 1500, "abstract": 150, "references": 15},
            "review-article": {"word_limit": 5000, "abstract": 250, "references": 60},
            "letter": {"word_limit": 600, "abstract": 0, "references": 5},
        },
    },
    # ── 11. Journal of Neurosurgical Anesthesiology ──
    {
        "slug": "jna",
        "journal": {
            "name": "Journal of Neurosurgical Anesthesiology",
            "abbreviation": "J Neurosurg Anesthesiol",
            "issn_print": "0898-4921",
            "issn_online": "1537-1921",
            "publisher": "Wolters Kluwer",
            "submission_url": "https://www.editorialmanager.com/jnsa/",
            "guidelines_url": "https://journals.lww.com/jnsa/pages/informationforauthors.aspx",
        },
        "word_limits": {
            "total_manuscript": 3000,
            "abstract": 250,
            "title_characters": 150,
            "running_title_characters": 50,
        },
        "abstract_structured": True,
        "abstract_headings": "Background, Methods, Results, Conclusions",
        "assets": {
            "figures_max": 5,
            "tables_max": 5,
            "total_display_items_max": 6,
            "figure_formats": ["TIFF", "EPS", "PDF"],
            "figure_dpi": 300,
        },
        "references": {
            "style": "vancouver",
            "max_references": 35,
            "max_authors_before_etal": 6,
            "doi_required": False,
            "pmid_preferred": True,
            "reference_limits": {
                "original-research": 35,
                "review-article": 60,
                "systematic-review": 60,
                "meta-analysis": 60,
                "case-report": 10,
                "letter": 5,
            },
            "minimum_reference_limits": {
                "original-research": 15,
                "review-article": 25,
                "case-report": 5,
                "letter": 0,
            },
        },
        "required_documents": {
            "cover_letter": True,
            "highlights": False,
            "graphical_abstract": False,
            "author_contributions": True,
            "conflict_of_interest": True,
            "funding_statement": True,
            "ethics_statement": True,
            "data_availability": True,
            "keywords": {"required": True, "count": "3-5"},
        },
        "reporting_guidelines": {
            "checklist": "recommended (CONSORT/STROBE/PRISMA)",
            "registration_required": True,
        },
        "sections": [
            {"name": "Title Page", "required": True},
            {"name": "Abstract", "required": True, "structured": True, "word_limit": 250},
            {"name": "Introduction", "required": True},
            {"name": "Methods", "required": True},
            {"name": "Results", "required": True},
            {"name": "Discussion", "required": True},
        ],
        "other_article_types": {
            "case-report": {"word_limit": 1500, "abstract": 150, "references": 10},
            "review-article": {"word_limit": 4000, "abstract": 250, "references": 60},
            "letter": {"word_limit": 500, "abstract": 0, "references": 5},
        },
    },
    # ── 12. Acta Anaesthesiologica Scandinavica ──
    {
        "slug": "acta-anaesthesiol-scand",
        "journal": {
            "name": "Acta Anaesthesiologica Scandinavica",
            "abbreviation": "Acta Anaesthesiol Scand",
            "issn_print": "0001-5172",
            "issn_online": "1399-6576",
            "publisher": "Wiley / Scandinavian Society of Anaesthesiology and Intensive Care Medicine",
            "submission_url": "https://mc.manuscriptcentral.com/aas",
            "guidelines_url": "https://onlinelibrary.wiley.com/page/journal/13996576/homepage/forauthors.html",
        },
        "word_limits": {
            "total_manuscript": 3000,
            "abstract": 250,
            "title_characters": 150,
            "running_title_characters": 50,
        },
        "abstract_structured": True,
        "abstract_headings": "Background, Methods, Results, Conclusions",
        "assets": {
            "figures_max": 5,
            "tables_max": 5,
            "total_display_items_max": 6,
            "figure_formats": ["TIFF", "EPS", "PDF", "PNG"],
            "figure_dpi": 300,
        },
        "references": {
            "style": "vancouver",
            "max_references": 30,
            "max_authors_before_etal": 6,
            "doi_required": False,
            "pmid_preferred": True,
            "reference_limits": {
                "original-research": 30,
                "review-article": 60,
                "systematic-review": 60,
                "meta-analysis": 60,
                "case-report": 10,
                "letter": 5,
            },
            "minimum_reference_limits": {
                "original-research": 15,
                "review-article": 25,
                "case-report": 5,
                "letter": 0,
            },
        },
        "required_documents": {
            "cover_letter": True,
            "highlights": False,
            "graphical_abstract": False,
            "author_contributions": True,
            "conflict_of_interest": True,
            "funding_statement": True,
            "ethics_statement": True,
            "data_availability": True,
            "keywords": {"required": True, "count": "3-5"},
        },
        "reporting_guidelines": {
            "checklist": "required (CONSORT/STROBE/PRISMA as appropriate)",
            "registration_required": True,
        },
        "sections": [
            {"name": "Title Page", "required": True},
            {"name": "Abstract", "required": True, "structured": True, "word_limit": 250},
            {"name": "Introduction", "required": True},
            {"name": "Methods", "required": True},
            {"name": "Results", "required": True},
            {"name": "Discussion", "required": True},
        ],
        "other_article_types": {
            "case-report": {"word_limit": 1500, "abstract": 150, "references": 10},
            "review-article": {"word_limit": 4000, "abstract": 250, "references": 60},
            "letter": {"word_limit": 500, "abstract": 0, "references": 5},
        },
    },
    # ── 13. Paediatric Anaesthesia ──
    {
        "slug": "paediatric-anaesthesia",
        "journal": {
            "name": "Paediatric Anaesthesia",
            "abbreviation": "Paediatr Anaesth",
            "issn_print": "1155-5645",
            "issn_online": "1460-9592",
            "publisher": "Wiley",
            "submission_url": "https://mc.manuscriptcentral.com/pan",
            "guidelines_url": "https://onlinelibrary.wiley.com/page/journal/14609592/homepage/forauthors.html",
        },
        "word_limits": {
            "total_manuscript": 3000,
            "abstract": 250,
            "title_characters": 150,
            "running_title_characters": 50,
        },
        "abstract_structured": True,
        "abstract_headings": "Background, Aims, Methods, Results, Conclusions",
        "assets": {
            "figures_max": 5,
            "tables_max": 5,
            "total_display_items_max": 6,
            "figure_formats": ["TIFF", "EPS", "PDF", "PNG"],
            "figure_dpi": 300,
        },
        "references": {
            "style": "vancouver",
            "max_references": 40,
            "max_authors_before_etal": 6,
            "doi_required": False,
            "pmid_preferred": True,
            "reference_limits": {
                "original-research": 40,
                "review-article": 60,
                "systematic-review": 60,
                "meta-analysis": 60,
                "case-report": 15,
                "letter": 5,
            },
            "minimum_reference_limits": {
                "original-research": 15,
                "review-article": 25,
                "case-report": 5,
                "letter": 0,
            },
        },
        "required_documents": {
            "cover_letter": True,
            "highlights": False,
            "graphical_abstract": False,
            "author_contributions": True,
            "conflict_of_interest": True,
            "funding_statement": True,
            "ethics_statement": True,
            "data_availability": True,
            "keywords": {"required": True, "count": "3-6"},
        },
        "reporting_guidelines": {
            "checklist": "required (CONSORT/STROBE/PRISMA as appropriate)",
            "registration_required": True,
        },
        "sections": [
            {"name": "Title Page", "required": True},
            {"name": "Abstract", "required": True, "structured": True, "word_limit": 250},
            {"name": "What is Already Known", "required": True},
            {"name": "What This Study Adds", "required": True},
            {"name": "Introduction", "required": True},
            {"name": "Methods", "required": True},
            {"name": "Results", "required": True},
            {"name": "Discussion", "required": True},
        ],
        "other_article_types": {
            "case-report": {"word_limit": 1500, "abstract": 150, "references": 15},
            "review-article": {"word_limit": 4000, "abstract": 250, "references": 60},
            "letter": {"word_limit": 500, "abstract": 0, "references": 5},
        },
    },
    # ── 14. Journal of Cardiothoracic and Vascular Anesthesia ──
    {
        "slug": "jcva",
        "journal": {
            "name": "Journal of Cardiothoracic and Vascular Anesthesia",
            "abbreviation": "J Cardiothorac Vasc Anesth",
            "issn_print": "1053-0770",
            "issn_online": "1532-8422",
            "publisher": "Elsevier / Society of Cardiovascular Anesthesiologists",
            "submission_url": "https://www.editorialmanager.com/jcva/",
            "guidelines_url": "https://www.sciencedirect.com/journal/journal-of-cardiothoracic-and-vascular-anesthesia/publish/guide-for-authors",
        },
        "word_limits": {
            "total_manuscript": 3000,
            "abstract": 250,
            "title_characters": 150,
            "running_title_characters": 50,
        },
        "abstract_structured": True,
        "abstract_headings": "Objective, Design, Setting, Participants, Interventions, Measurements and Main Results, Conclusions",
        "assets": {
            "figures_max": 6,
            "tables_max": 6,
            "total_display_items_max": 8,
            "figure_formats": ["TIFF", "EPS", "PDF", "JPEG"],
            "figure_dpi": 300,
        },
        "references": {
            "style": "vancouver",
            "max_references": 40,
            "max_authors_before_etal": 6,
            "doi_required": False,
            "pmid_preferred": True,
            "reference_limits": {
                "original-research": 40,
                "review-article": 60,
                "systematic-review": 60,
                "meta-analysis": 60,
                "case-report": 15,
                "letter": 5,
            },
            "minimum_reference_limits": {
                "original-research": 15,
                "review-article": 25,
                "case-report": 5,
                "letter": 0,
            },
        },
        "required_documents": {
            "cover_letter": True,
            "highlights": True,
            "graphical_abstract": False,
            "author_contributions": True,
            "conflict_of_interest": True,
            "funding_statement": True,
            "ethics_statement": True,
            "data_availability": True,
            "keywords": {"required": True, "count": "3-6"},
        },
        "reporting_guidelines": {
            "checklist": "recommended (CONSORT/STROBE/PRISMA)",
            "registration_required": True,
        },
        "sections": [
            {"name": "Title Page", "required": True},
            {"name": "Abstract", "required": True, "structured": True, "word_limit": 250},
            {"name": "Introduction", "required": True},
            {"name": "Methods", "required": True},
            {"name": "Results", "required": True},
            {"name": "Discussion", "required": True},
        ],
        "other_article_types": {
            "case-report": {"word_limit": 1500, "abstract": 150, "references": 15},
            "review-article": {"word_limit": 5000, "abstract": 250, "references": 60},
            "letter": {"word_limit": 500, "abstract": 0, "references": 5},
        },
    },
    # ── 15. International Journal of Obstetric Anesthesia ──
    {
        "slug": "ijoa",
        "journal": {
            "name": "International Journal of Obstetric Anesthesia",
            "abbreviation": "Int J Obstet Anesth",
            "issn_print": "0959-289X",
            "issn_online": "1532-3374",
            "publisher": "Elsevier / Obstetric Anaesthetists' Association",
            "submission_url": "https://www.editorialmanager.com/ijoa/",
            "guidelines_url": "https://www.sciencedirect.com/journal/international-journal-of-obstetric-anesthesia/publish/guide-for-authors",
        },
        "word_limits": {
            "total_manuscript": 3000,
            "abstract": 250,
            "title_characters": 150,
            "running_title_characters": 50,
        },
        "abstract_structured": True,
        "abstract_headings": "Background, Methods, Results, Conclusions",
        "assets": {
            "figures_max": 5,
            "tables_max": 5,
            "total_display_items_max": 6,
            "figure_formats": ["TIFF", "EPS", "PDF", "JPEG"],
            "figure_dpi": 300,
        },
        "references": {
            "style": "vancouver",
            "max_references": 30,
            "max_authors_before_etal": 6,
            "doi_required": False,
            "pmid_preferred": True,
            "reference_limits": {
                "original-research": 30,
                "review-article": 50,
                "systematic-review": 50,
                "meta-analysis": 50,
                "case-report": 15,
                "letter": 5,
            },
            "minimum_reference_limits": {
                "original-research": 15,
                "review-article": 20,
                "case-report": 5,
                "letter": 0,
            },
        },
        "required_documents": {
            "cover_letter": True,
            "highlights": True,
            "graphical_abstract": False,
            "author_contributions": True,
            "conflict_of_interest": True,
            "funding_statement": True,
            "ethics_statement": True,
            "data_availability": True,
            "keywords": {"required": True, "count": "3-6"},
        },
        "reporting_guidelines": {
            "checklist": "required (CONSORT/STROBE/PRISMA as appropriate)",
            "registration_required": True,
        },
        "sections": [
            {"name": "Title Page", "required": True},
            {"name": "Abstract", "required": True, "structured": True, "word_limit": 250},
            {"name": "Introduction", "required": True},
            {"name": "Methods", "required": True},
            {"name": "Results", "required": True},
            {"name": "Discussion", "required": True},
        ],
        "other_article_types": {
            "case-report": {"word_limit": 1500, "abstract": 150, "references": 15},
            "review-article": {"word_limit": 4000, "abstract": 250, "references": 50},
            "letter": {"word_limit": 500, "abstract": 0, "references": 5},
        },
    },
    # ── 16. BMC Anesthesiology ──
    {
        "slug": "bmc-anesthesiology",
        "journal": {
            "name": "BMC Anesthesiology",
            "abbreviation": "BMC Anesthesiol",
            "issn_print": "",
            "issn_online": "1471-2253",
            "publisher": "BioMed Central / Springer Nature",
            "submission_url": "https://www.editorialmanager.com/bean/",
            "guidelines_url": "https://bmcanesthesiol.biomedcentral.com/submission-guidelines",
        },
        "word_limits": {
            "total_manuscript": 5000,
            "abstract": 350,
            "title_characters": 150,
            "running_title_characters": 0,
        },
        "abstract_structured": True,
        "abstract_headings": "Background, Methods, Results, Conclusions",
        "assets": {
            "figures_max": 10,
            "tables_max": 10,
            "total_display_items_max": 15,
            "supplementary_allowed": True,
            "figure_formats": ["TIFF", "EPS", "PDF", "PNG", "JPEG"],
            "figure_dpi": 300,
        },
        "references": {
            "style": "vancouver",
            "max_references": 60,
            "max_authors_before_etal": 6,
            "doi_required": True,
            "pmid_preferred": True,
            "reference_limits": {
                "original-research": 60,
                "review-article": 80,
                "systematic-review": 80,
                "meta-analysis": 80,
                "case-report": 30,
                "letter": 10,
            },
            "minimum_reference_limits": {
                "original-research": 15,
                "review-article": 25,
                "case-report": 5,
                "letter": 0,
            },
        },
        "required_documents": {
            "cover_letter": False,
            "highlights": False,
            "graphical_abstract": False,
            "author_contributions": True,
            "conflict_of_interest": True,
            "funding_statement": True,
            "ethics_statement": True,
            "data_availability": True,
            "keywords": {"required": True, "count": "3-10"},
        },
        "reporting_guidelines": {
            "checklist": "required (CONSORT/STROBE/PRISMA as appropriate)",
            "registration_required": True,
        },
        "sections": [
            {"name": "Title Page", "required": True},
            {"name": "Abstract", "required": True, "structured": True, "word_limit": 350},
            {"name": "Background", "required": True},
            {"name": "Methods", "required": True},
            {"name": "Results", "required": True},
            {"name": "Discussion", "required": True},
            {"name": "Conclusions", "required": True},
        ],
        "notes": "Open access journal. No strict word limit for main text but 5000 recommended. APC applies.",
        "other_article_types": {
            "case-report": {"word_limit": 3000, "abstract": 350, "references": 30},
            "review-article": {"word_limit": 6000, "abstract": 350, "references": 80},
        },
    },
    # ── 17. Journal of Anesthesia ──
    {
        "slug": "journal-of-anesthesia",
        "journal": {
            "name": "Journal of Anesthesia",
            "abbreviation": "J Anesth",
            "issn_print": "0913-8668",
            "issn_online": "1438-8359",
            "publisher": "Springer / Japanese Society of Anesthesiologists",
            "submission_url": "https://www.editorialmanager.com/jana/",
            "guidelines_url": "https://www.springer.com/journal/540/submission-guidelines",
        },
        "word_limits": {
            "total_manuscript": 3000,
            "abstract": 250,
            "title_characters": 150,
            "running_title_characters": 50,
        },
        "abstract_structured": True,
        "abstract_headings": "Purpose, Methods, Results, Conclusions",
        "assets": {
            "figures_max": 6,
            "tables_max": 6,
            "total_display_items_max": 8,
            "figure_formats": ["TIFF", "EPS", "PDF", "PNG"],
            "figure_dpi": 300,
        },
        "references": {
            "style": "vancouver",
            "max_references": 30,
            "max_authors_before_etal": 6,
            "doi_required": False,
            "pmid_preferred": True,
            "reference_limits": {
                "original-research": 30,
                "review-article": 50,
                "systematic-review": 50,
                "meta-analysis": 50,
                "case-report": 15,
                "letter": 5,
            },
            "minimum_reference_limits": {
                "original-research": 15,
                "review-article": 25,
                "case-report": 5,
                "letter": 0,
            },
        },
        "required_documents": {
            "cover_letter": True,
            "highlights": False,
            "graphical_abstract": False,
            "author_contributions": True,
            "conflict_of_interest": True,
            "funding_statement": True,
            "ethics_statement": True,
            "data_availability": True,
            "keywords": {"required": True, "count": "3-5"},
        },
        "reporting_guidelines": {
            "checklist": "recommended (CONSORT/STROBE/PRISMA)",
            "registration_required": True,
        },
        "sections": [
            {"name": "Title Page", "required": True},
            {"name": "Abstract", "required": True, "structured": True, "word_limit": 250},
            {"name": "Introduction", "required": True},
            {"name": "Methods", "required": True},
            {"name": "Results", "required": True},
            {"name": "Discussion", "required": True},
        ],
        "other_article_types": {
            "case-report": {"word_limit": 1500, "abstract": 150, "references": 15},
            "review-article": {"word_limit": 5000, "abstract": 250, "references": 50},
            "letter": {"word_limit": 500, "abstract": 0, "references": 5},
        },
    },
    # ── 18. Anaesthesia and Intensive Care ──
    {
        "slug": "anaesthesia-intensive-care",
        "journal": {
            "name": "Anaesthesia and Intensive Care",
            "abbreviation": "Anaesth Intensive Care",
            "issn_print": "0310-057X",
            "issn_online": "1448-0271",
            "publisher": "SAGE / Australian Society of Anaesthetists",
            "submission_url": "https://mc.manuscriptcentral.com/aic",
            "guidelines_url": "https://journals.sagepub.com/author-instructions/AIC",
        },
        "word_limits": {
            "total_manuscript": 3000,
            "abstract": 200,
            "title_characters": 150,
            "running_title_characters": 50,
        },
        "abstract_structured": True,
        "abstract_headings": "Background, Methods, Results, Conclusions",
        "assets": {
            "figures_max": 5,
            "tables_max": 5,
            "total_display_items_max": 6,
            "figure_formats": ["TIFF", "EPS", "PDF", "JPEG"],
            "figure_dpi": 300,
        },
        "references": {
            "style": "vancouver",
            "max_references": 30,
            "max_authors_before_etal": 6,
            "doi_required": False,
            "pmid_preferred": True,
            "reference_limits": {
                "original-research": 30,
                "review-article": 50,
                "systematic-review": 50,
                "meta-analysis": 50,
                "case-report": 10,
                "letter": 5,
            },
            "minimum_reference_limits": {
                "original-research": 15,
                "review-article": 20,
                "case-report": 5,
                "letter": 0,
            },
        },
        "required_documents": {
            "cover_letter": True,
            "highlights": False,
            "graphical_abstract": False,
            "author_contributions": True,
            "conflict_of_interest": True,
            "funding_statement": True,
            "ethics_statement": True,
            "data_availability": True,
            "keywords": {"required": True, "count": "3-5"},
        },
        "reporting_guidelines": {
            "checklist": "required (CONSORT/STROBE/PRISMA as appropriate)",
            "registration_required": True,
        },
        "sections": [
            {"name": "Title Page", "required": True},
            {"name": "Abstract", "required": True, "structured": True, "word_limit": 200},
            {"name": "Introduction", "required": True},
            {"name": "Methods", "required": True},
            {"name": "Results", "required": True},
            {"name": "Discussion", "required": True},
        ],
        "other_article_types": {
            "case-report": {"word_limit": 1500, "abstract": 150, "references": 10},
            "review-article": {"word_limit": 4000, "abstract": 200, "references": 50},
            "letter": {"word_limit": 500, "abstract": 0, "references": 5},
        },
    },
    # ── 19. Korean Journal of Anesthesiology (KJA) ── VERIFIED 2026-03
    {
        "slug": "kja",
        "journal": {
            "name": "Korean Journal of Anesthesiology",
            "abbreviation": "Korean J Anesthesiol",
            "issn_print": "2005-6419",
            "issn_online": "2005-7563",
            "publisher": "Korean Society of Anesthesiologists",
            "submission_url": "https://www.editorialmanager.com/kja/",
            "guidelines_url": "https://ekja.org/authors/authors.php",
        },
        "word_limits": {
            "total_manuscript": 3000,
            "abstract": 250,
            "title_characters": 150,
            "running_title_characters": 50,
        },
        "abstract_structured": True,
        "abstract_headings": "Background, Methods, Results, Conclusions",
        "assets": {
            "figures_max": 6,
            "tables_max": 6,
            "total_display_items_max": 8,
            "figure_formats": ["TIFF", "EPS", "PDF", "PNG", "JPEG"],
            "figure_dpi": 300,
        },
        "references": {
            "style": "vancouver",
            "max_references": 30,
            "max_authors_before_etal": 6,
            "doi_required": False,
            "pmid_preferred": True,
            "reference_limits": {
                "original-research": 30,
                "review-article": 50,
                "systematic-review": 50,
                "meta-analysis": 50,
                "case-report": 15,
                "letter": 5,
            },
            "minimum_reference_limits": {
                "original-research": 15,
                "review-article": 25,
                "case-report": 5,
                "letter": 0,
            },
        },
        "required_documents": {
            "cover_letter": True,
            "highlights": False,
            "graphical_abstract": False,
            "author_contributions": True,
            "conflict_of_interest": True,
            "funding_statement": True,
            "ethics_statement": True,
            "data_availability": True,
            "keywords": {"required": True, "count": "3-5"},
        },
        "reporting_guidelines": {
            "checklist": "required (EQUATOR network + CONSORT/STROBE/PRISMA)",
            "registration_required": True,
        },
        "sections": [
            {"name": "Title Page", "required": True},
            {"name": "Abstract", "required": True, "structured": True, "word_limit": 250},
            {"name": "Introduction", "required": True},
            {"name": "Methods", "required": True},
            {"name": "Results", "required": True},
            {"name": "Discussion", "required": True},
        ],
        "notes": "Open access journal. Publication fee waived for non-Korean affiliations. American English spelling.",
        "other_article_types": {
            "case-report": {"word_limit": 1500, "abstract": 150, "references": 15},
            "review-article": {"word_limit": 5000, "abstract": 250, "references": 50},
            "letter": {"word_limit": 500, "abstract": 0, "references": 5},
        },
    },
    # ── 20. Brazilian Journal of Anesthesiology ──
    {
        "slug": "bja-br",
        "journal": {
            "name": "Brazilian Journal of Anesthesiology",
            "abbreviation": "Braz J Anesthesiol",
            "issn_print": "0104-0014",
            "issn_online": "1806-907X",
            "publisher": "Elsevier / Brazilian Society of Anesthesiology",
            "submission_url": "https://www.editorialmanager.com/bjane/",
            "guidelines_url": "https://www.sciencedirect.com/journal/brazilian-journal-of-anesthesiology/publish/guide-for-authors",
        },
        "word_limits": {
            "total_manuscript": 3000,
            "abstract": 250,
            "title_characters": 150,
            "running_title_characters": 50,
        },
        "abstract_structured": True,
        "abstract_headings": "Background and Objectives, Methods, Results, Conclusions",
        "assets": {
            "figures_max": 5,
            "tables_max": 5,
            "total_display_items_max": 6,
            "figure_formats": ["TIFF", "EPS", "PDF", "JPEG"],
            "figure_dpi": 300,
        },
        "references": {
            "style": "vancouver",
            "max_references": 30,
            "max_authors_before_etal": 6,
            "doi_required": False,
            "pmid_preferred": True,
            "reference_limits": {
                "original-research": 30,
                "review-article": 50,
                "systematic-review": 50,
                "meta-analysis": 50,
                "case-report": 15,
                "letter": 5,
            },
            "minimum_reference_limits": {
                "original-research": 15,
                "review-article": 25,
                "case-report": 5,
                "letter": 0,
            },
        },
        "required_documents": {
            "cover_letter": True,
            "highlights": True,
            "graphical_abstract": False,
            "author_contributions": True,
            "conflict_of_interest": True,
            "funding_statement": True,
            "ethics_statement": True,
            "data_availability": True,
            "keywords": {"required": True, "count": "3-6"},
        },
        "reporting_guidelines": {
            "checklist": "required (CONSORT/STROBE/PRISMA as appropriate)",
            "registration_required": True,
        },
        "sections": [
            {"name": "Title Page", "required": True},
            {"name": "Abstract", "required": True, "structured": True, "word_limit": 250},
            {"name": "Introduction", "required": True},
            {"name": "Methods", "required": True},
            {"name": "Results", "required": True},
            {"name": "Discussion", "required": True},
        ],
        "other_article_types": {
            "case-report": {"word_limit": 1500, "abstract": 150, "references": 15},
            "review-article": {"word_limit": 4000, "abstract": 250, "references": 50},
            "letter": {"word_limit": 500, "abstract": 0, "references": 5},
        },
    },
]


# ─── YAML Generator ────────────────────────────────────────────────────


def build_profile(j: dict) -> dict:
    """Convert journal data dict into journal-profile.template.yaml schema."""
    paper_type = j.get("default_paper_type", "original-research")

    profile = {
        "journal": {
            "name": j["journal"]["name"],
            "abbreviation": j["journal"]["abbreviation"],
            "issn": j["journal"].get("issn_print", ""),
            "issn_online": j["journal"].get("issn_online", ""),
            "publisher": j["journal"].get("publisher", ""),
            "submission_url": j["journal"].get("submission_url", ""),
            "guidelines_url": j["journal"].get("guidelines_url", ""),
        },
        "authors": [],
        "paper": {
            "type": paper_type,
            "sections": j.get("sections", []),
        },
        "word_limits": {
            "total_manuscript": j["word_limits"]["total_manuscript"],
            "abstract": j["word_limits"]["abstract"],
            "title_characters": j["word_limits"].get("title_characters", 150),
            "running_title_characters": j["word_limits"].get("running_title_characters", 50),
        },
        "assets": {
            "figures_max": j["assets"]["figures_max"],
            "tables_max": j["assets"]["tables_max"],
            "total_display_items_max": j["assets"].get("total_display_items_max", 8),
            "supplementary_allowed": j["assets"].get("supplementary_allowed", True),
            "figure_formats": j["assets"]["figure_formats"],
            "figure_dpi": j["assets"]["figure_dpi"],
            "table_format": "editable",
        },
        "references": {
            "style": j["references"]["style"],
            "csl": "",
            "max_references": j["references"]["max_references"],
            "max_authors_before_etal": j["references"]["max_authors_before_etal"],
            "doi_required": j["references"]["doi_required"],
            "pmid_preferred": j["references"]["pmid_preferred"],
            "reference_limits": j["references"]["reference_limits"],
            "minimum_reference_limits": j["references"]["minimum_reference_limits"],
        },
        "required_documents": j["required_documents"],
        "reporting_guidelines": j["reporting_guidelines"],
        "pipeline": {
            "hook_a_max_rounds": 3,
            "hook_b_max_rounds": 2,
            "hook_c_max_rounds": 3,
            "review_max_rounds": 3,
            "autonomous_review": {
                "enabled": True,
                "reviewer_perspectives": [
                    "methodology_expert",
                    "domain_specialist",
                    "statistician",
                    "editor",
                ],
                "quality_threshold": 7,
            },
            "tolerance": {
                "word_percent": 20,
                "citation_density_strict": True,
            },
            "section_brief": {
                "enabled": True,
                "paragraph_level": True,
                "enforce_must_cite": True,
            },
            "changelog": [],
            "writing": {
                "language": "en",
                "tone": "formal-academic",
                "anti_ai_strictness": "high",
                "citation_density": {
                    "introduction": 100,
                    "methods": 0,
                    "results": 0,
                    "discussion": 150,
                },
            },
            "assets": {
                "auto_generate_table_one": True,
                "auto_generate_plots": True,
                "flow_diagram_tool": "drawio",
                "fallback_to_description": True,
                "agent_initiated": {
                    "enabled": True,
                    "allowed_types": [
                        "literature_summary_table",
                        "comparison_table",
                        "timeline_figure",
                        "concept_diagram",
                    ],
                    "must_respect_limits": True,
                },
            },
        },
    }

    # Add introduction word limit if specified
    if "introduction_max" in j["word_limits"]:
        profile["word_limits"]["introduction_max"] = j["word_limits"]["introduction_max"]

    # Add abstract format info
    profile["abstract"] = {
        "structured": j.get("abstract_structured", True),
        "headings": j.get("abstract_headings", "Background, Methods, Results, Conclusions"),
    }

    # Add other article types as reference
    if "other_article_types" in j:
        profile["other_article_types"] = j["other_article_types"]

    # Add notes
    if "notes" in j:
        profile["notes"] = j["notes"]

    return profile


def yaml_representer_str(dumper, data):
    """Use block style for long strings."""
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


def generate_profiles(output_dir: Path):
    """Generate all journal profile YAML files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    yaml.add_representer(str, yaml_representer_str)

    generated = []
    for j in JOURNALS:
        profile = build_profile(j)
        filename = f"{j['slug']}.yaml"
        filepath = output_dir / filename

        # Add header comment
        header = (
            f"# ═══════════════════════════════════════════════════════════════\n"
            f"# Journal Profile: {j['journal']['name']}\n"
            f"# ═══════════════════════════════════════════════════════════════\n"
            f"# Generated: {date.today().isoformat()}\n"
            f"# Source: {j['journal']['guidelines_url']}\n"
            f"#\n"
            f"# Usage: cp templates/journal-profiles/{filename} \\\n"
            f"#           projects/{{slug}}/journal-profile.yaml\n"
            f"#\n"
            f"# ⚠️  Always verify against the latest author guidelines URL above.\n"
            f"#     Journal requirements may change without notice.\n"
            f"# ═══════════════════════════════════════════════════════════════\n\n"
        )

        content = yaml.dump(
            profile,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            width=100,
        )

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(header)
            f.write(content)

        generated.append((filename, j["journal"]["name"]))
        print(f"  ✓ {filename:<40s} {j['journal']['name']}")

    # Generate index
    generate_index(output_dir, generated)
    generate_readme(output_dir)

    print(f"\n  Total: {len(generated)} journal profiles generated in {output_dir}")


def generate_index(output_dir: Path, generated: list):
    """Generate _index.yaml catalog."""
    index = {
        "specialty": "Anesthesiology",
        "total_journals": len(generated),
        "generated_date": date.today().isoformat(),
        "verified_journals": ["rapm", "eja", "kja"],
        "journals": [],
    }

    for j in JOURNALS:
        entry = {
            "slug": j["slug"],
            "name": j["journal"]["name"],
            "abbreviation": j["journal"]["abbreviation"],
            "publisher": j["journal"].get("publisher", ""),
            "issn": j["journal"].get("issn_online") or j["journal"].get("issn_print", ""),
            "guidelines_url": j["journal"]["guidelines_url"],
            "word_limit_original": j["word_limits"]["total_manuscript"],
            "abstract_limit": j["word_limits"]["abstract"],
            "max_references": j["references"]["max_references"],
            "reference_style": j["references"]["style"],
        }
        index["journals"].append(entry)

    filepath = output_dir / "_index.yaml"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("# Anesthesiology Top 20 Journal Profiles — Quick Index\n")
        f.write(f"# Generated: {date.today().isoformat()}\n\n")
        yaml.dump(index, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    print(f"  ✓ {'_index.yaml':<40s} Quick reference index")


def generate_readme(output_dir: Path):
    """Generate README.md."""
    readme = f"""# Anesthesiology Journal Profiles (Top 20)

> 自動生成於 {date.today().isoformat()}。使用前請務必對照各期刊最新投稿指南 URL 驗證。

## 使用方式

```bash
# 複製 profile 到專案
cp templates/journal-profiles/bja.yaml projects/my-project/journal-profile.yaml

# 或用 MCP tool (Phase 0)
# setup_project_interactive 會引導選擇期刊
```

## 期刊列表

| # | 期刊 | 縮寫 | 全文字數 | 摘要字數 | 參考文獻上限 | 驗證狀態 |
|---|------|------|----------|----------|-------------|---------|
"""
    for i, j in enumerate(JOURNALS, 1):
        verified = "✅" if j["slug"] in ("rapm", "eja", "kja") else "📋"
        readme += (
            f"| {i} | [{j['journal']['name']}]({j['journal']['guidelines_url']}) "
            f"| {j['journal']['abbreviation']} "
            f"| {j['word_limits']['total_manuscript']} "
            f"| {j['word_limits']['abstract']} "
            f"| {j['references']['max_references']} "
            f"| {verified} |\n"
        )

    readme += """
## 驗證狀態

- ✅ = 已從官方投稿指南網頁驗證 (2026-03)
- 📋 = 基於已知投稿指南編譯，建議使用前驗證

## 資料欄位說明

每個 `.yaml` 檔案包含以下結構（與 `journal-profile.template.yaml` 相容）：

- `journal` — 期刊基本資訊（名稱、ISSN、投稿系統 URL、指南 URL）
- `authors` — 空白（專案特定）
- `paper` — 論文類型和章節結構
- `word_limits` — 字數限制
- `abstract` — 摘要格式（結構化/非結構化、標題）
- `assets` — 圖表限制和格式要求
- `references` — 引用格式和數量限制（含各論文類型）
- `required_documents` — 必要附件
- `reporting_guidelines` — 報告指引要求
- `other_article_types` — 其他文章類型的限制
- `pipeline` — MedPaper 系統預設設定

## 貢獻

如果某期刊的指南有更新，請修改對應的 `.yaml` 檔案或更新 `scripts/generate_journal_profiles.py` 中的資料源。
"""

    filepath = output_dir / "README.md"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(readme)
    print(f"  ✓ {'README.md':<40s} Documentation")


if __name__ == "__main__":
    workspace = Path(__file__).resolve().parent.parent
    output = workspace / "templates" / "journal-profiles"
    print(f"Generating journal profiles to: {output}\n")
    generate_profiles(output)
