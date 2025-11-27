SECTION_PROMPTS = {
    "introduction": """
Write an Introduction section for a medical research paper with the following structure:
1. Opening statement about the clinical problem/significance
2. Current state of knowledge (cite provided references)
3. Knowledge gap or controversy
4. Study rationale and hypothesis
5. Study objectives

Guidelines:
- Use formal academic tone
- Each claim should have a citation
- Avoid first person (use "this study" instead of "we")
- Target length: 400-600 words
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
"""
}
