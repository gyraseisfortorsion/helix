import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page, request }) => {
  const response = await request.post("/api/session", {
    data: { demo: true, demo_source: "synthetic" },
  });
  const session = await response.json();
  await page.addInitScript(
    (value) =>
      sessionStorage.setItem("helix.session.v1", JSON.stringify(value)),
    session,
  );
});

test("DNA-only workspace opens with explicitly synthetic data and optional methylation", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "A clearer picture of your biology." }),
  ).toBeVisible();
  await expect(page.getByText("No extra test needed to start")).toBeVisible();
  await expect(page.getByText("4 calls")).toBeVisible();
  await expect(
    page.getByText("You’re exploring synthetic demo data.", { exact: false }),
  ).toBeVisible();
  expect(errors).toEqual([]);
});

test("a question traverses browser, API, worker, evidence and response", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("button", { name: /Could my knee pain be genetic/ })
    .click();
  await expect(
    page.getByRole("heading", {
      name: "Genetic context for your joint question",
    }),
  ).toBeVisible();
  await expect(page.getByText("Evidence-library answer")).toBeVisible();
  await expect(
    page.getByText(
      "Your cartilage methylation and gene expression have not been measured.",
    ),
  ).toBeVisible();
  await page
    .locator(".evidence-list")
    .getByRole("button", { name: /GDF5 regulation and cartilage methylation/ })
    .click();
  await expect(
    page.getByRole("link", {
      name: /GDF5 regulation and cartilage methylation/,
    }),
  ).toBeVisible();
});

test("wearable charts render actual imported summaries", async ({ page }) => {
  await page.goto("/");
  await page
    .getByRole("button", { name: "Health trends", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Your patterns over time" }),
  ).toBeVisible();
  await expect(page.locator(".js-plotly-plot")).toHaveCount(3);
  await expect(
    page.getByText("Historical median 80.5 · 28 days"),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Open evidence drawer", exact: true })
    .click();
  await expect(
    page.getByRole("dialog").locator(".evidence-card"),
  ).toContainText("Measurements in this wearable profile");
  await expect(
    page.getByRole("dialog").locator(".evidence-card"),
  ).toContainText("80.5");
  await page
    .getByRole("button", { name: "Close evidence drawer", exact: true })
    .click();
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({
    path: "/tmp/strand-wearables-desktop.png",
    fullPage: true,
  });
});

test("family comparison displays conditional inheritance and limited coverage", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("button", { name: "Family planning", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Cystic fibrosis", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("25% two assessed alleles", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Three explicitly supported alleles", { exact: false }),
  ).toBeVisible();
  await page.screenshot({
    path: "/tmp/strand-family-desktop.png",
    fullPage: true,
  });
});

test("methylation starts empty and an optional synthetic sample is labeled", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: /Methylation Optional/ }).click();
  await expect(
    page.getByRole("heading", { name: "DNA is enough to start." }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: /Explore a synthetic sample/ })
    .click();
  await expect(
    page.getByRole("heading", { name: "Synthetic blood sample" }),
  ).toBeVisible();
  await expect(page.getByText("24 probes", { exact: false })).toBeVisible();
  await expect(page.locator(".js-plotly-plot")).toHaveCount(1);
  await expect(page.locator(".methylation-meaning")).toContainText(
    "not automatically healthy or unhealthy",
  );
  await page.screenshot({
    path: "/tmp/strand-methylation-desktop.png",
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Explain this sample", exact: true })
    .click();
  await expect(page.locator(".answer-card")).toContainText(
    "DNA alone supports sequence-based regulatory predictions",
  );
  await expect(page.locator(".user-question")).toContainText(
    "what additional data is needed",
  );
});

test("private profile and real file upload work with no methylation", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Use my data", exact: true }).click();
  await page.getByRole("button", { name: /Create private workspace/ }).click();
  await page
    .getByRole("textbox", { name: "Name", exact: true })
    .fill("Upload Test");
  await page
    .getByRole("button", { name: "Create profile", exact: true })
    .click();
  await expect(
    page.getByRole("option", { name: "Upload Test" }),
  ).toBeAttached();
  await page.getByRole("button", { name: "Add data", exact: true }).click();
  await page.locator("input[type=file]").setInputFiles({
    name: "sample.vcf",
    mimeType: "text/plain",
    buffer: Buffer.from(
      "##fileformat=VCFv4.2\n##reference=GRCh38\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE\n7\t117587806\trs75527207\tG\tA\t99\tPASS\t.\tGT\t0/1\n",
    ),
  });
  await page
    .getByRole("button", { name: "Import into this profile", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page
    .getByRole("button", { name: "Genetic findings", exact: true })
    .click();
  await expect(page.getByText("rs75527207", { exact: true })).toBeVisible();
  await expect(page.getByText("G/A", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: /Methylation Optional/ }).click();
  await expect(
    page.getByRole("heading", { name: "DNA is enough to start." }),
  ).toBeVisible();
});

test("mobile navigation stays usable without horizontal overflow", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "A clearer picture of your biology." }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});
