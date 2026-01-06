SECTION_PROMPTS = {
    "introduction": """
Write a high-impact Introduction for a medical research paper. 

### 🚫 ANTI-AI WRITING RULES (CRITICAL)
- **NO generic openings**: Avoid "In recent years...", "With the advancement of...", "X is a major public health concern...".
- **NO generic transitions**: Avoid starting paragraphs with "Furthermore", "Additionally", "Moreover". Use logical transitions based on evidence (e.g., "Despite these findings...", "In contrast to...").
- **NO vague adjectives**: Avoid "significant", "better", "improved" without specific numbers or mechanisms.
- **NO passive voice overload**: Use active voice where appropriate to describe the study's intent.

### 🏗️ STRUCTURE: THE EVIDENCE FUNNEL
1. **The Clinical Reality**: Start with a specific, data-driven statement about the current clinical situation or mechanism. Use numbers/percentages from references.
2. **Current Evidence Base**: Synthesize what is known. Do not just list studies; group them by findings or mechanisms.
3. **The Knowledge Gap**: Explicitly state what is NOT known. Use the 🔒 NOVELTY STATEMENT as your guide.
4. **The Study Rationale**: Why is this study necessary NOW? What specific problem does it solve?
5. **Objectives**: State the primary and secondary objectives clearly.

### 🔒 PROTECTED CONTENT
- You MUST reflect the **🔒 NOVELTY STATEMENT** provided in the context.
- Do not weaken or generalize the novelty claim.

### 📝 CITATION STYLE
- Use [[citation_key]] or [PMID:xxxx] for every factual claim.
- Ground every statement in the provided reference abstracts.
""",
    "methods": """
Write a Methods section following CONSORT/STROBE guidelines:
1. Study design
2. Setting and participants
3. Inclusion/exclusion criteria
4. Intervention or exposure
5. Outcomes (primary and secondary)
6. Sample size calculation
7. Statistical analysis

Guidelines:
- Use past tense
- Be specific and reproducible
- Include ethical approval statement
""",
    "results": """
Write a Results section based on the provided statistical outputs:
1. Participant flow and baseline characteristics
2. Primary outcome results
3. Secondary outcome results
4. Subgroup analyses (if applicable)

Guidelines:
- Report exact p-values (except p<0.001)
- Include confidence intervals
- Reference tables and figures
- Do not interpret results (save for Discussion)
""",
    "discussion": """
Write a Discussion section with the following structure:
1. Summary of main findings
2. Comparison with existing literature
3. Possible mechanisms
4. Clinical implications
5. Strengths and limitations
6. Future directions
7. Conclusion

Guidelines:
- Start with interpretation, not repetition of results
- Acknowledge limitations honestly
- Avoid overstatement of findings
""",
    "abstract": """
Write a structured abstract (250-300 words) with:
- Background: 2-3 sentences
- Methods: 3-4 sentences
- Results: 4-5 sentences with key statistics
- Conclusions: 2-3 sentences

Guidelines:
- No citations in abstract
- Include specific numbers
- State clinical significance
""",
}
