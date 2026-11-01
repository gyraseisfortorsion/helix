import gzip

import pytest

from api.analysis import family_comparison, wearable_summary
from api.datasets import import_dataset, records
from api.demo import seed_demo


def profile(store):
    return store.create_profile(
        "workspace", {"name": "Test", "timezone": "America/New_York", "provenance": "uploaded"}
    )


def upload(store, tmp_path, text, filename="calls.vcf", kind="genetics", metadata=None):
    person = profile(store)
    source = tmp_path / filename
    if filename.endswith(".gz"):
        with gzip.open(source, "wt") as stream:
            stream.write(text)
    else:
        source.write_text(text)
    result = import_dataset(
        store, "workspace", person["id"], source, kind, metadata or {"build": "GRCh38"}, filename
    )
    return person, result


HEADER = "##fileformat=VCFv4.2\n##reference=GRCh38\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE\n"


def test_vcf_no_calls_and_multiallelic_genotypes(store, tmp_path):
    text = (
        HEADER
        + "7\t117587806\trs75527207\tG\tA,T\t99\tPASS\t.\tGT\t1/2\n"
        + "15\t72350518\trs121907954\tC\tT\t.\tPASS\t.\tGT\t./.\n"
    )
    person, result = upload(store, tmp_path, text, "calls.vcf.gz")
    calls = records(store, "workspace", person["id"], "genetics")
    assert result["accepted"] == 2
    assert result["missing"] == 1
    by_id = {call["rsid"]: call for call in calls}
    assert by_id["rs75527207"]["allele1"] == "A" and by_id["rs75527207"]["allele2"] == "T"
    assert by_id["rs121907954"]["allele1"] is None


def test_assembly_mismatch_rejected(store, tmp_path):
    with pytest.raises(ValueError, match="assembly conflicts"):
        upload(
            store, tmp_path, HEADER + "1\t10\trs1\tA\tG\t.\tPASS\t.\tGT\t0/1\n", metadata={"build": "GRCh37"}
        )


@pytest.mark.parametrize("genotype", ["--", "00", "NN"])
def test_array_missing_calls_remain_unknown(store, tmp_path, genotype):
    person, result = upload(store, tmp_path, f"rs75527207\t7\t117587806\t{genotype}\n", "23andme.txt")
    assert result["missing"] == 1
    assert records(store, "workspace", person["id"], "genetics")[0]["allele1"] is None


def test_invalid_methylation_is_atomic(store, tmp_path):
    with pytest.raises(ValueError, match="between 0 and 1"):
        upload(
            store,
            tmp_path,
            "cpg_id,beta\ncg1,1.2\n",
            "beta.csv",
            "methylation",
            {"build": "GRCh38", "tissue": "blood", "assay": "EPIC", "collected_at": "2026-10-30"},
        )
    assert not list(tmp_path.rglob("*.parquet"))


def test_methylation_metadata_required(store, tmp_path):
    with pytest.raises(ValueError, match="tissue"):
        upload(store, tmp_path, "cpg_id,beta\ncg1,0.5\n", "beta.csv", "methylation")


def test_methylation_probe_values_preserved(store, tmp_path):
    person, result = upload(
        store,
        tmp_path,
        "cpg_id,beta\ncg1,0.5\ncg2,0.0\n",
        "beta.csv",
        "methylation",
        {"build": "GRCh38", "tissue": "blood", "assay": "EPIC", "collected_at": "2026-10-30"},
    )
    assert result["accepted"] == 2
    assert records(store, "workspace", person["id"], "methylation")[0]["beta"] == 0.5


def test_family_probability_and_incomplete_coverage(store):
    a, b = seed_demo(store, "workspace")
    result = family_comparison(store, "workspace", a["id"], b["id"])
    assert result["conditions"][0]["affected_genotype_probability"] == 0.25
    assert result["conditions"][1]["affected_genotype_probability"] is None
    assert result["conditions"][2]["affected_genotype_probability"] is None


def test_absent_variants_are_not_negative_carrier_results(store, tmp_path):
    a, _ = upload(store, tmp_path, HEADER + "1\t100\trs100\tG\tA\t99\tPASS\t.\tGT\t0/1\n")
    b, _ = upload(store, tmp_path, HEADER + "1\t101\trs101\tG\tA\t99\tPASS\t.\tGT\t0/1\n")
    result = family_comparison(store, "workspace", a["id"], b["id"])
    assert all(c["parent_a"]["status"] == "unknown" for c in result["conditions"])
    assert all(c["affected_genotype_probability"] is None for c in result["conditions"])


def test_multiallelic_rsid_does_not_imply_curated_pathogenic_allele(store, tmp_path):
    a, _ = upload(store, tmp_path, HEADER + "7\t117587806\trs75527207\tG\tT\t99\tPASS\t.\tGT\t0/1\n")
    b, _ = upload(
        store, tmp_path, HEADER + "7\t117587806\trs75527207\tG\tA\t99\tPASS\t.\tGT\t0/1\n", "other.vcf"
    )
    result = family_comparison(store, "workspace", a["id"], b["id"])
    assert result["conditions"][0]["affected_genotype_probability"] is None


def test_baseline_excludes_latest_day_and_separates_activity(store, tmp_path):
    rows = ["timestamp,metric,value,unit,source,context"]
    rows += [
        f"2026-10-{i:02}T08:00:00-04:00,resting_heart_rate,{70 if i < 9 else 100},bpm,watch,resting"
        for i in range(1, 10)
    ]
    rows += ["2026-10-09T09:00:00-04:00,heart_rate,170,bpm,watch,exercise"]
    person, _ = upload(store, tmp_path, "\n".join(rows), "wearables.csv", "wearables")
    result = wearable_summary(store, "workspace", person["id"])
    assert result["metrics"]["resting_heart_rate"]["baseline"] == 70
    assert result["metrics"]["resting_heart_rate"]["latest"] == 100
    assert result["metrics"]["heart_rate"]["latest"] == 170


def test_reference_validation_and_indel_normalization(store, tmp_path):
    import pysam

    reference = tmp_path / "reference.fa"
    reference.write_text(">1\nCAAAAAGGGG\n")
    pysam.faidx(str(reference))
    store.config.dna_reference_grch38 = str(reference)
    text = HEADER.replace(
        "#CHROM",
        '##contig=<ID=1,length=10>\n##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">\n#CHROM',
    )
    person, result = upload(store, tmp_path, text + "1\t4\trs1\tAA\tA\t99\tPASS\t.\tGT\t0/1\n")
    assert result["reference_normalized"] is True
    call = records(store, "workspace", person["id"], "genetics")[0]
    assert call["pos"] == 1
    assert call["ref"] == "CA" and call["alt"] == "C"


def test_cumulative_wearable_totals_and_devices_are_not_added(store, tmp_path):
    text = "\n".join(
        [
            "timestamp,metric,value,unit,source,context",
            "2026-10-09T08:00:00-04:00,steps,3000,count,watch,daily_total",
            "2026-10-09T20:00:00-04:00,steps,8000,count,watch,daily_total",
            "2026-10-09T09:00:00-04:00,steps,1000,count,watch,interval",
            "2026-10-09T20:00:00-04:00,steps,8000,count,phone,daily_total",
            "2026-10-09T08:00:00-04:00,resting_heart_rate,70,bpm,watch,resting",
            "2026-10-09T08:00:00-04:00,resting_heart_rate,90,bpm,watch,resting",
        ]
    )
    person, _ = upload(store, tmp_path, text, "wearables.csv", "wearables")
    result = wearable_summary(store, "workspace", person["id"])
    assert result["metrics"]["steps"]["latest"] == 8000
    assert "resting_heart_rate" not in result["metrics"]
    assert "Conflicting observations excluded: 1." in result["limitations"]
