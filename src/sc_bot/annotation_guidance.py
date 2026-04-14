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


DEG_DEBUGGING_GUIDANCE = """
Use this DEG-focused reasoning framework when the user asks what a differentially expressed gene list represents:

## I. Foundational Reasoning Framework

### 1. Distinguish types, states, and continuums
- Cell type: a robust phenotype identifiable by characteristic markers and tied to distinct biological function.
- Cell state: a transient or responsive condition such as activation, exhaustion, interferon response, or metabolic
  shift.
- Cell continuum: a transition where one population differentiates into another, so hard boundaries may be
  subjective.

### 2. Identify technical noise
- Mitochondrial genes such as `MT-` genes can indicate low-quality cells or stress.
- Immediate early genes such as `FOS` or `JUN` often reflect dissociation or stress responses rather than stable
  identity.
- Ambient RNA or nuclear-skewed signals such as `MALAT1` can reflect contamination or library-preparation bias.

## II. Example Mixed DEG Pattern

### 1. Broad lineage: B-cell identity
- Canonical B-cell markers include `MS4A1`, `CD79A`, `CD79B`, `CD74`, `BANK1`, `CD37`, and `LTB`.
- `MS4A1` supports mature B-cell identity, while `CD79B` and `VPREB3` can also appear in earlier lymphoid or
  B-cell progenitor contexts.

### 2. Sub-lineage or state: plasma cells and plasmablasts
- `PRDM1`, `XBP1`, `MZB1`, `SDC1`, `JCHAIN`, `IGKC`, `IGHG1`, and `SLAMF7` indicate transition toward a secretory
  plasma-cell-like phenotype.
- `PRDM1` and `XBP1` are strong regulators of plasma cell differentiation.

### 3. Identity intruders: plasmacytoid dendritic cell markers
- `LILRA4`, `CLEC4C`, `TCF4`, `GZMB`, `IRF7`, `PACSIN1`, and `PTGDS` support plasmacytoid dendritic cells.
- Seeing these alongside strong B-cell markers suggests under-clustering or a mixed population.

### 4. Quality and state indicators
- `MT-CO1`, `MT-CO2`, and `MT-ATP6` suggest mitochondrial stress.
- `RPS18` and `RPL13` indicate ribosomal load, which can be biologically expected in plasma cells because of high
  protein synthesis.
- `MALAT1`, `FOS`, and `JUN` can indicate nuclear bias or stress.

## III. Agent Debugging Thinking Process
- Step 1: Identify lineage dominance. Look for the strongest primary lineage signal first.
- Step 2: Detect intruder markers. Flag genes from biologically distinct lineages that suggest mixing or
  under-clustering.
- Step 3: Evaluate differentiation status. Check whether the list mixes progenitor, mature, and terminally
  differentiated programs.
- Step 4: Assess noise levels. Estimate whether mitochondrial, ribosomal, or stress genes dominate the top list.
- Step 5: Formulate refinement guidance. Recommend practical follow-up analysis steps rather than forcing an
  overconfident label.

## IV. Refinement and Annotation Strategies
- If distinct lineage markers are mixed, suggest increasing clustering resolution to separate merged populations.
- If mature lineage markers and terminal differentiation markers coexist, consider a developmental continuum,
  plasmablast transition, or under-clustering.
- Prefer effect size such as log fold-change over p-values alone when ranking the most informative markers.
- Suggest cross-checking with external reference mapping tools when uncertainty remains high or the cluster appears
  transitional.
- If mitochondrial and stress genes dominate, recommend revisiting QC filters before making a strong annotation.

## V. Assist-Mode Interpretation Style
- Start with the dominant lineage, then explain subtype, state, or continuum overlays.
- Call out mixed-lineage evidence explicitly instead of hiding it.
- Separate biological identity markers from stress or quality-control markers.
- If the cluster looks under-clustered, say so directly and suggest how to refine the analysis.
- Prefer an honest broad label with rationale over an overconfident fine-grained subtype call.
"""
