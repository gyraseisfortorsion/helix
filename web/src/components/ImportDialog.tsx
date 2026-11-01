import { useState } from "react";
import type { FormEvent } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { Download, FileUp, LoaderCircle, X } from "lucide-react";
import { API_BASE, followJob, request } from "../api";
import { Button } from "./Button";

export function ImportDialog({
  profileId,
  token,
  onImported,
  open,
  onOpenChange,
}: {
  profileId: string;
  token: string;
  onImported: () => void;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [kind, setKind] = useState("genetics"),
    [build, setBuild] = useState("GRCh38");
  const [file, setFile] = useState<File | null>(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) return;
    const fields = new FormData(event.currentTarget);
    const metadata = {
      build,
      tissue: fields.get("tissue"),
      assay: fields.get("assay"),
      collected_at: fields.get("collected_at"),
      age_at_collection: fields.get("age_at_collection") || undefined,
      subject_id: fields.get("subject_id") || undefined,
      preprocessing: fields.get("preprocessing") || undefined,
      qc_status: fields.get("qc_status") || undefined,
      qc_reference: fields.get("qc_reference") || undefined,
      comparability_group: fields.get("comparability_group") || undefined,
    };
    const body = new FormData();
    body.set("file", file);
    body.set("kind", kind);
    body.set("metadata", JSON.stringify(metadata));
    setBusy(true);
    setError("");
    try {
      const job = await request<{ job_id: string }>(
        `/api/profiles/${profileId}/datasets`,
        token,
        { method: "POST", body },
      );
      await followJob(job.job_id, token, () => {});
      onImported();
      onOpenChange(false);
      setFile(null);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Dialog.Root
      open={open}
      onOpenChange={(value) => {
        if (!busy) onOpenChange(value);
      }}
    >
      <Dialog.Portal>
        <Dialog.Overlay className="dialog-overlay" />
        <Dialog.Content className="dialog-content">
          <div className="dialog-heading">
            <div className="icon-tile">
              <FileUp size={21} />
            </div>
            <Dialog.Close className="icon-button" aria-label="Close upload">
              <X size={20} />
            </Dialog.Close>
          </div>
          <Dialog.Title>Add your data</Dialog.Title>
          <Dialog.Description>
            Start with DNA. Wearables and methylation are entirely optional.
          </Dialog.Description>
          <form onSubmit={submit}>
            <label>
              Data type
              <select
                value={kind}
                onChange={(e) => {
                  setKind(e.target.value);
                  setFile(null);
                }}
              >
                <option value="genetics">Genetic data</option>
                <option value="wearables">
                  Wearable measurements · optional
                </option>
                <option value="methylation">
                  Measured methylation · optional
                </option>
              </select>
            </label>
            {kind !== "wearables" && (
              <label>
                Reference assembly
                <select
                  value={build}
                  onChange={(e) => setBuild(e.target.value)}
                >
                  <option>GRCh38</option>
                  <option>GRCh37</option>
                </select>
                <span className="field-hint">
                  Use the assembly stated by your provider. We never guess.
                </span>
              </label>
            )}
            {kind === "methylation" && (
              <div className="form-grid">
                <label>
                  Tissue
                  <input
                    name="tissue"
                    placeholder="e.g. whole blood"
                    required
                  />
                </label>
                <label>
                  Assay
                  <input
                    name="assay"
                    placeholder="e.g. Illumina 450K"
                    required
                  />
                </label>
                <label>
                  Collection date
                  <input name="collected_at" type="date" required />
                </label>
                <label>
                  Age at collection
                  <input
                    name="age_at_collection"
                    type="number"
                    min="0"
                    max="120"
                    step="0.01"
                  />
                </label>
                <label>
                  Subject ID
                  <input
                    name="subject_id"
                    placeholder="Same ID on repeat samples"
                    maxLength={100}
                  />
                </label>
                <label>
                  Preprocessing method
                  <input
                    name="preprocessing"
                    placeholder="Copy from your laboratory report"
                    maxLength={500}
                  />
                </label>
                <label>
                  Laboratory QC status
                  <select name="qc_status">
                    <option value="unknown">Not supplied</option>
                    <option value="lab_reported_pass">
                      Lab report states QC passed
                    </option>
                    <option value="failed">QC failed</option>
                  </select>
                </label>
                <label>
                  QC report reference
                  <input
                    name="qc_reference"
                    placeholder="Lab report ID or reference"
                    maxLength={500}
                  />
                </label>
                <label>
                  Repeat-test comparability group
                  <input
                    name="comparability_group"
                    placeholder="Lab-confirmed comparable batch group"
                    maxLength={200}
                  />
                </label>
                <p className="field-hint">
                  The age report currently supports adult whole blood on
                  Illumina 450K, with all 71 Hannum sites and documented
                  processing/QC. Other samples can still be explored. We do not
                  process raw IDAT files or verify laboratory QC. Repeat tests
                  need matching subject and protocol metadata.
                </p>
              </div>
            )}
            <label className="file-zone">
              <FileUp size={24} />
              <strong>{file?.name || "Choose a file"}</strong>
              <span>
                {kind === "genetics"
                  ? "Single-sample VCF, VCF.gz, 23andMe or Ancestry text"
                  : kind === "wearables"
                    ? "CSV: timestamp, metric, value, unit, source, context"
                    : "CSV: cpg_id, beta; optional chrom and position"}
              </span>
              <input
                key={kind}
                type="file"
                accept={kind === "genetics" ? ".vcf,.gz,.txt,.tsv" : ".csv"}
                required
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
            </label>
            <a
              className="text-link"
              href={`${API_BASE}/api/templates/${kind}`}
              download
            >
              <Download size={14} /> Download a synthetic format example
            </a>
            {error && (
              <p role="alert" className="error">
                {error}
              </p>
            )}
            <Button className="full-width" disabled={busy || !file}>
              {busy ? (
                <LoaderCircle className="spin" size={16} />
              ) : (
                <FileUp size={16} />
              )}
              {busy ? "Validating and importing…" : "Import into this profile"}
            </Button>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
