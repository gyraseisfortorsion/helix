"""Descriptive explanations of actual model outputs; no clinical effect thresholds."""

import math


def explain_prediction(result: dict) -> dict:
    variant = result.get("variant", {})
    is_gdf5 = variant.get("rsid") == "rs143383"
    context = result.get("context_name") or "the selected reference cells"
    summaries = []
    for track in result.get("tracks", []):
        points = [
            (x, float(a), float(b))
            for x, a, b in zip(track["x"], track["reference"], track["alternate"], strict=True)
            if math.isfinite(a) and math.isfinite(b)
        ]
        if not points:
            continue
        x, ref, alt = max(points, key=lambda p: abs(p[2] - p[1]))
        modality = track["modality"]
        summaries.append(
            {
                "modality": modality,
                "track_name": track["name"],
                "meaning": "Predicted DNA accessibility: how open this region may be to cellular machinery."
                if modality in {"DNASE", "ATAC"}
                else "Predicted RNA signal along this region; this is not a gene-specific expression effect score.",
                "mean_absolute_difference": math.fsum(abs(b - a) for _, a, b in points) / len(points),
                "largest_absolute_difference": abs(alt - ref),
                "largest_difference_position": x,
                "reference_at_largest_difference": ref,
                "alternative_at_largest_difference": alt,
                "units": track["units"],
            }
        )
    tissue_note = f"These predictions use {context}, not a sample of your current cells."
    if is_gdf5 and not any(s in context.lower() for s in ["cartilage", "chondrocyte"]):
        tissue_note += " This is not a cartilage context, so this run cannot explain knee pain or test the published cartilage mechanism."
    sequence_only = result.get("provider") == "evo2"
    return {
        "headline": "A sequence comparison, not a health verdict"
        if sequence_only
        else "What this DNA change does in the model",
        "summary": "Evo 2 compared how likely the reference and alternative DNA sequences are under its learned sequence patterns. The difference has no validated personal disease-risk threshold here."
        if sequence_only
        else f"We changed {variant.get('ref', '?')} to {variant.get('alt', '?')} in the same DNA region and compared predicted signals in {context}. The plots show where the model's outputs differ; peaks alone do not show a mutation effect.",
        "context_note": "This sequence-likelihood model does not select a tissue or measure methylation."
        if sequence_only
        else tissue_note,
        "findings": summaries,
        "published_context": "Published experiments link rs143383 to GDF5 regulation in cartilage. This is a research mechanism, not proof of the cause of a person's symptoms."
        if is_gdf5
        else "This run has not established a clinical interpretation for this variant. An identifier or model effect alone does not show whether it causes disease.",
        "published_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC4099533/" if is_gdf5 else None,
        "takeaway": "This result does not identify a treatment, exercise or diet for you. Use it to investigate a molecular hypothesis and decide what evidence is still needed.",
        "next_steps": [
            "Review the measured genotype and relevant published evidence together.",
            "For a symptom question, add timing, injury history and changes in activity; these predictions cannot diagnose the cause.",
            "For research, confirm a relevant cell context and compare with experimental measurements before drawing a functional conclusion.",
        ],
        "metric_scope": "Differences are descriptive values from the displayed, binned tracks. No statistical significance, pathogenicity threshold or calibrated effect size is inferred.",
    }
