import { test, expect } from "@playwright/test";

// Explicit model-output fixture for interface behavior; not scientific validation.
test("molecular result explains readouts and context before the plots", async ({
  page,
}) => {
  await page.route("**/api/health", (route) =>
    route.fulfill({
      json: {
        providers: { chat: false, alphagenome: true, evo2: false },
        methylation_required: false,
      },
    }),
  );
  await page.route("**/api/scientific-contexts", (route) =>
    route.fulfill({
      json: {
        configured: true,
        contexts: [{ id: "EFO:0001187", name: "HepG2", outputs: ["ATAC"] }],
      },
    }),
  );
  await page.route("**/api/investigations", (route) =>
    route.fulfill({ json: { job_id: "ui-fixture" } }),
  );
  await page.route("**/api/jobs/ui-fixture/events", (route) =>
    route.fulfill({
      contentType: "text/event-stream",
      body: 'data: {"id":1,"agent":"Workspace","kind":"completed","message":"Ready"}\n\n',
    }),
  );
  await page.route("**/api/jobs/ui-fixture", (route) =>
    route.fulfill({
      json: {
        status: "completed",
        result: {
          provider: "alphagenome",
          execution: "test fixture",
          elapsed_seconds: 1,
          context_name: "HepG2",
          limitations: ["Test fixture only"],
          variant: { rsid: "rs143383", pos: 35438203, ref: "G", alt: "A" },
          tracks: [
            {
              name: "test ATAC",
              modality: "ATAC",
              x: [35438000, 35438203, 35438400],
              reference: [0.1, 0.5, 0.1],
              alternate: [0.1, 0.6, 0.1],
              units: "Model-normalized assay signal",
            },
          ],
          explanation: {
            headline: "What this DNA change does in the model",
            summary:
              "The plots show where the model's outputs differ; peaks alone do not show a mutation effect.",
            context_note:
              "HepG2 is not a cartilage context; this run cannot explain knee pain.",
            published_context:
              "GDF5 regulation has experimental evidence in cartilage.",
            published_url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC4099533/",
            takeaway: "Use this to investigate a molecular hypothesis.",
            next_steps: ["Review measured genotype and experimental evidence."],
            metric_scope:
              "Descriptive binned-track difference, without a calibrated significance threshold.",
            findings: [
              {
                modality: "ATAC",
                meaning: "Predicted DNA accessibility",
                largest_absolute_difference: 0.1,
                largest_difference_position: 35438203,
                units: "Model-normalized assay signal",
              },
            ],
          },
        },
      },
    }),
  );
  await page.goto("/");
  await page
    .getByRole("button", { name: "Genetic findings", exact: true })
    .click();
  await page
    .getByRole("row")
    .filter({ hasText: "rs143383" })
    .getByRole("button")
    .click();
  await expect(
    page.getByText("Why investigate GDF5?", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Run molecular investigation", exact: true })
    .click();
  const explanation = page.getByRole("region", {
    name: "What your molecular result means",
  });
  await expect(explanation).toContainText("cannot explain knee pain");
  await expect(explanation).toContainText("DNA accessibility");
  await expect(page.locator(".js-plotly-plot")).toHaveCount(1);
  await explanation.scrollIntoViewIfNeeded();
  await page.screenshot({
    path: "/tmp/strand-molecular-explained-desktop.png",
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(explanation).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth + 2,
    ),
  ).toBe(true);
});
