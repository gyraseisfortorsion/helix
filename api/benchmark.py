"""Reproducible retrospective MPRA evaluation; labels stay outside model requests."""

import argparse
import csv
import gzip
import hashlib
import importlib.metadata
import json
import random
from pathlib import Path
from statistics import median

import httpx

from .config import settings

SOURCE = "https://raw.githubusercontent.com/kircherlab/MPRA_SaturationMutagenesis/master/data/elements.tsv.gz"
CITATION = "Kircher et al. 2019, doi:10.1038/s41467-019-11526-w"
SOURCE_SHA256 = "fec2eed91fe27af3aae07ebce2eca65e9bad4bb6abba5d8c27f478887dd7b134"


def write_csv(path: Path, rows: list[dict]):
    if not rows:
        raise ValueError("No eligible benchmark rows.")
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def prepare(folder: Path, size: int = 30) -> dict:
    folder.mkdir(parents=True, exist_ok=True)
    source = folder / "elements.tsv.gz"
    if not source.exists():
        with httpx.Client(timeout=60, follow_redirects=True) as client:
            response = client.get(SOURCE)
            response.raise_for_status()
        source.write_bytes(response.content)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest != SOURCE_SHA256:
        raise ValueError("Benchmark source hash changed. Review the source before updating the pinned hash.")
    with gzip.open(source, "rt") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    manifest = {
        "source": SOURCE,
        "source_sha256": digest,
        "citation": CITATION,
        "seed": 42,
        "minimum_barcodes": 10,
        "variants_per_element": size,
        "development": ["LDLR"],
        "test": ["F9", "SORT1"],
        "limitations": [
            "Retrospective reporter-assay evaluation; not a clinical endpoint.",
            "This does not establish that the foundation models never encountered these data.",
        ],
    }
    development, inputs, labels = [], [], []
    rng = random.Random(42)
    for element in ["LDLR", "F9", "SORT1"]:
        eligible = [
            r
            for r in rows
            if r["Element"] == element
            and r["Release"] == "GRCh38"
            and len(r["Ref"]) == len(r["Alt"]) == 1
            and set(r["Ref"] + r["Alt"]) <= set("ACGT")
            and int(r["Barcodes"]) >= 10
        ]
        eligible.sort(key=lambda row: (int(row["Pos"]), row["Alt"]))
        chosen = rng.sample(eligible, min(size, len(eligible)))
        for row in chosen:
            variant = {
                "variant_id": f"{element}:{row['Chrom']}:{row['Pos']}:{row['Ref']}:{row['Alt']}",
                "element": element,
                "chrom": row["Chrom"],
                "pos": int(row["Pos"]),
                "ref": row["Ref"],
                "alt": row["Alt"],
            }
            label = {
                "variant_id": variant["variant_id"],
                "measured_log2_effect": float(row["Coefficient"]),
                "p_value": float(row["pValue"]),
                "barcodes": int(row["Barcodes"]),
            }
            if element == "LDLR":
                development.append({**variant, **label})
            else:
                inputs.append(variant)
                labels.append(label)
    write_csv(folder / "development.csv", development)
    write_csv(folder / "test-inputs.csv", inputs)
    write_csv(folder / "test-labels.csv", labels)
    manifest["counts"] = {"development": len(development), "test": len(inputs)}
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def predict(inputs: Path, output: Path):
    if not settings.alphagenome_api_key:
        raise ValueError("ALPHAGENOME_API_KEY is required. No benchmark predictions were generated.")
    from alphagenome.data import genome
    from alphagenome.models.v1 import dna_client, dna_model, variant_scorers

    client = dna_client.create(
        settings.alphagenome_api_key, model_version=dna_model.ModelVersion.ALL_FOLDS, timeout=90
    )
    records = list(csv.DictReader(inputs.open()))
    results = []
    # Only test-inputs are read here. The labels file is never opened during prediction.
    for row in records:
        v = genome.Variant(
            chromosome="chr" + row["chrom"],
            position=int(row["pos"]),
            reference_bases=row["ref"],
            alternate_bases=row["alt"],
        )
        scored = client.score_variant(
            interval=v.reference_interval.resize(1048576),
            variant=v,
            variant_scorers=[variant_scorers.RECOMMENDED_VARIANT_SCORERS["RNA_SEQ"]],
        )
        frame = variant_scorers.tidy_scores(scored)
        matched = frame[(frame["gene_name"] == row["element"]) & (frame["ontology_curie"] == "EFO:0001187")]
        if matched.empty:
            raise ValueError(
                f"No matching HepG2 gene-expression score for {row['variant_id']}. No tissue substitution made."
            )
        results.append(
            {
                "variant_id": row["variant_id"],
                "predicted_effect": median(matched["raw_score"].tolist()),
                "score_kind": "expression_log_fold_change",
            }
        )
        print(json.dumps({"completed": len(results), "total": len(records), "variant_id": row["variant_id"]}))
    output.parent.mkdir(parents=True, exist_ok=True)
    write_csv(output, results)
    output.with_suffix(".metadata.json").write_text(
        json.dumps(
            {
                "model": "AlphaGenome",
                "model_version": "ALL_FOLDS",
                "sdk_version": importlib.metadata.version("alphagenome"),
                "context": "EFO:0001187 (HepG2)",
                "aggregation": "Median RNA_SEQ GeneMaskLFCScorer score across matching HepG2 tracks",
                "inputs_sha256": hashlib.sha256(inputs.read_bytes()).hexdigest(),
            },
            indent=2,
        )
        + "\n"
    )


def evaluate(labels: Path, predictions: Path) -> dict:
    from scipy.stats import spearmanr

    truth = {r["variant_id"]: float(r["measured_log2_effect"]) for r in csv.DictReader(labels.open())}
    rows = list(csv.DictReader(predictions.open()))
    predicted = {r["variant_id"]: r for r in rows}
    if len(predicted) != len(rows):
        raise ValueError("Duplicate predicted variant IDs.")
    if set(predicted) - set(truth):
        raise ValueError("Predictions include unexpected variants.")
    ids = sorted(set(truth) & set(predicted))
    if len(ids) < 3:
        raise ValueError("At least three matching predictions are required.")
    if any(r["score_kind"] != "expression_log_fold_change" for r in predicted.values()):
        raise ValueError("Expression direction cannot be evaluated using sequence-likelihood scores.")
    import math

    x = [float(predicted[key]["predicted_effect"]) for key in ids]
    y = [truth[key] for key in ids]
    if not all(math.isfinite(v) for v in [*x, *y]):
        raise ValueError("Scores must be finite.")
    correlation = float(spearmanr(x, y).statistic)
    return {
        "matched": len(ids),
        "expected": len(truth),
        "coverage": len(ids) / len(truth),
        "spearman": correlation if math.isfinite(correlation) else None,
        "direction_agreement": sum((a > 0) == (b > 0) for a, b in zip(x, y, strict=True)) / len(ids),
        "limitations": "Direction agreement includes small/noisy assay effects; no clinical accuracy or agent superiority is established.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--folder", type=Path, default=Path("data/benchmark"))
    p.add_argument("--size", type=int, default=30)
    p = sub.add_parser("predict")
    p.add_argument("--inputs", type=Path, default=Path("data/benchmark/test-inputs.csv"))
    p.add_argument("--output", type=Path, default=Path("data/benchmark/predictions.csv"))
    p = sub.add_parser("evaluate")
    p.add_argument("--labels", type=Path, default=Path("data/benchmark/test-labels.csv"))
    p.add_argument("--predictions", type=Path, default=Path("data/benchmark/predictions.csv"))
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            print(json.dumps(prepare(args.folder, args.size), indent=2))
        elif args.command == "predict":
            predict(args.inputs, args.output)
        else:
            print(json.dumps(evaluate(args.labels, args.predictions), indent=2))
    except ValueError as error:
        parser.exit(2, str(error) + "\n")


if __name__ == "__main__":
    main()
