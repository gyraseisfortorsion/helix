import { useState } from "react";
import type { FormEvent } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { UserRoundPlus, X } from "lucide-react";
import { request } from "../api";
import type { Profile } from "../types";
import { Button } from "./Button";

export function ProfileDialog({
  token,
  onCreated,
  open,
  onOpenChange,
}: {
  token: string;
  onCreated: (profile: Profile) => void;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const fields = new FormData(event.currentTarget);
    setBusy(true);
    setError("");
    try {
      const profile = await request<Profile>("/api/profiles", token, {
        method: "POST",
        body: JSON.stringify({
          name: fields.get("name"),
          age: fields.get("age") ? Number(fields.get("age")) : null,
          goals: fields.get("goals"),
          history: fields.get("history"),
          dietary_constraints: fields.get("dietary_constraints"),
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
          external_analysis_consent: fields.get("consent") === "on",
        }),
      });
      onCreated(profile);
      onOpenChange(false);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="dialog-overlay" />
        <Dialog.Content className="dialog-content">
          <div className="dialog-heading">
            <div className="icon-tile">
              <UserRoundPlus size={21} />
            </div>
            <Dialog.Close
              className="icon-button"
              aria-label="Close profile dialog"
            >
              <X size={20} />
            </Dialog.Close>
          </div>
          <Dialog.Title>Create a profile</Dialog.Title>
          <Dialog.Description>
            Keep your data and your partner’s data in separate profiles.
          </Dialog.Description>
          <form onSubmit={submit}>
            <div className="form-grid">
              <label>
                Name
                <input
                  name="name"
                  required
                  maxLength={80}
                  placeholder="Your name"
                />
              </label>
              <label>
                Age · optional
                <input name="age" type="number" min="0" max="120" />
              </label>
            </div>
            <label>
              Your goals
              <input
                name="goals"
                placeholder="What would you like to understand?"
                maxLength={2000}
              />
            </label>
            <label>
              Relevant history · optional
              <textarea name="history" rows={2} maxLength={4000} />
            </label>
            <label>
              Dietary constraints · optional
              <input name="dietary_constraints" maxLength={2000} />
            </label>
            <label className="checkbox-row">
              <input type="checkbox" name="consent" />
              <span>
                Allow selected variants, relevant health summaries and questions
                to be sent to the configured AI and scientific providers. Full
                DNA files stay on the backend.
              </span>
            </label>
            {error && (
              <p className="error" role="alert">
                {error}
              </p>
            )}
            <Button disabled={busy} className="full-width">
              {busy ? "Creating…" : "Create profile"}
            </Button>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
