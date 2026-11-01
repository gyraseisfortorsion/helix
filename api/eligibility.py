"""Explain whether a measured call can enter the supported molecular comparison."""

import re


def coordinate_identity(call: dict) -> str | None:
    ref = call.get("ref")
    alternatives = {call.get("allele1"), call.get("allele2")} - {ref}
    if (
        call.get("build") != "GRCh38"
        or not re.fullmatch(r"(?:[1-9]|1[0-9]|2[0-2]|X|Y)", str(call.get("chrom", "")))
        or not isinstance(call.get("pos"), int)
        or call["pos"] < 1
        or ref not in {"A", "C", "G", "T"}
        or len(alternatives) != 1
    ):
        return None
    alt = next(iter(alternatives))
    if alt not in {"A", "C", "G", "T"}:
        return None
    return f"GRCh38:{call['chrom']}:{call['pos']}:{ref}:{alt}"


def investigation_identity(call: dict) -> str | None:
    return call.get("rsid") or coordinate_identity(call)


def investigation_eligibility(call: dict) -> dict:
    def result(status, label, reason, eligible=False):
        return {"status": status, "label": label, "reason": reason, "eligible": eligible}

    a, b = call.get("allele1"), call.get("allele2")
    if a is None or b is None:
        return result(
            "missing",
            "Missing genotype",
            "No complete genotype was measured here. Choose a called variant; missing data cannot be compared.",
        )
    if any(len(v) != 1 or v not in "ACGT" for v in (a, b)):
        return result(
            "unsupported",
            "SNVs only",
            "This comparison currently supports single DNA-letter substitutions; this call needs a different analysis.",
        )
    ref = call.get("ref")
    if not ref:
        if not call.get("rsid"):
            return result(
                "reference_missing",
                "Reference needed",
                "This call has neither a reference allele nor an rsID. Upload a VCF with reference alleles before comparing sequences.",
            )
        return result(
            "reference_check",
            "Check reference",
            "The reference allele will be checked before any model runs.",
            True,
        )
    if len(ref) != 1 or ref not in "ACGT":
        return result(
            "unsupported",
            "SNVs only",
            "This call has a non-SNV reference allele, which is not supported by this comparison.",
        )
    alternatives = {a, b} - {ref}
    if not alternatives:
        return result(
            "reference_only",
            "Reference only",
            f"Your measured call is {a}/{b}, matching the reference {ref}. No alternative allele was observed, so there is no reference-versus-alternative comparison to run. Choose a measured variant with an alternative allele.",
        )
    if len(alternatives) > 1:
        return result(
            "multiple_alternatives",
            "Two alternatives",
            f"The {a}/{b} call contains two different alternatives to reference {ref}. This workflow needs one unambiguous alternative; choose a biallelic call.",
        )
    if not call.get("rsid") and not coordinate_identity(call):
        return result(
            "coordinate_unsupported",
            "Mapping needed",
            "Without an rsID, this workflow requires an explicit GRCh38 chromosome 1–22, X or Y position and a single-letter reference allele. Other assemblies need a validated mapping first.",
        )
    return result(
        "ready",
        "Ready to compare",
        f"Compare reference {ref} with measured alternative {next(iter(alternatives))} from the {a}/{b} call.",
        True,
    )
