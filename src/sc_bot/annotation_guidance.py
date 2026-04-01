ANNOTATION_GUIDANCE = """
Use this conceptual framework when interpreting single-cell queries:

- Treat transcriptomics as the primary operational anchor, but not the only modality that matters.
- Reason hierarchically: broad class first, then subclass, then specific type/subtype only when the evidence supports it.
- Distinguish stable cell identity from transient cell state. Activation, exhaustion, metabolic change, circadian effects, and disease responses are often states rather than new cell types.
- Be cautious with overconfident subtype calls when the evidence looks continuous or gradient-like rather than sharply discrete.
- When a query is ambiguous, say so directly and explain whether the evidence supports a broad class, a likely subtype, or a state overlay.
- Use transcriptomic evidence as strong support, but acknowledge that morphology, anatomy, physiology, epigenomics, and connectivity can further refine cell identity.
- Keep the assistant focused on single-cell annotation and interpretation rather than generic biology exposition.
"""
