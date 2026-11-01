import { test, expect } from "@playwright/test";

test("combined demo answers in a persona's context while preserving original public samples", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByText("Combined demo. A fictional person", { exact: false }),
  ).toBeVisible();
  await expect(page.getByLabel("Active profile")).toHaveValue(
    await page
      .getByRole("option", { name: "Alex Morgan · combined demo" })
      .getAttribute("value"),
  );
  await expect(page.getByText("22 calls", { exact: true })).toBeVisible();
  await page.locator(".profile-source-note summary").click();
  await expect(
    page.getByRole("link", { name: /Wearables: PMData p01/ }),
  ).toBeVisible();
  await page.locator(".profile-source-note summary").click();
  await page
    .locator(".prompt-grid")
    .getByRole("button", { name: /Could my knee pain be genetic/ })
    .click();
  await expect(page.locator(".answer-card")).toContainText(
    "Your data includes a call",
  );
  await expect(page.locator(".answer-card")).not.toContainText("In Alex");
  await expect(page.locator(".answer-card")).toContainText("steps");
  await expect(page.locator(".answer-card")).toContainText("2020-03-31");
  await page
    .getByRole("button", { name: "Health trends", exact: true })
    .click();
  await expect(page.locator(".js-plotly-plot")).toHaveCount(3);
  await page
    .getByLabel("Active profile")
    .selectOption({ label: "Sam Chen · combined demo" });
  await expect(page.locator(".js-plotly-plot")).toHaveCount(3);
  await page
    .getByLabel("Active profile")
    .selectOption({ label: "HG002 · GIAB son" });
  await expect(page.locator(".js-plotly-plot")).toHaveCount(0);
  await page
    .getByRole("button", { name: "Methylation Optional", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "DNA is enough to start." }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: /Explore HG002 public methylation/ })
    .click();
  await expect(page.getByText("407 sites", { exact: false })).toBeVisible();
  await expect(
    page.getByText("PUBLIC MEASUREMENT", { exact: true }),
  ).toBeVisible();
  await page
    .getByLabel("Active profile")
    .selectOption({ label: "PMData · participant p01" });
  await page
    .getByRole("button", { name: "Health trends", exact: true })
    .click();
  await expect(page.locator(".js-plotly-plot")).toHaveCount(3);
  await page
    .getByRole("button", { name: "Genetic findings", exact: true })
    .click();
  await expect(page.getByRole("row")).toHaveCount(1);
});

test("coordinate variants are named clearly and Investigate brings controls into view", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("button", { name: "Genetic findings", exact: true })
    .click();
  await expect(page.getByText("Unnamed variant", { exact: true })).toHaveCount(
    0,
  );
  const row = page.getByRole("row").filter({ hasText: "35,430,145" });
  await expect(row).toContainText("C>G");
  await expect(row).toContainText("No rsID supplied in this file");
  await row
    .getByRole("button", { name: "Investigate chr20:35430145", exact: true })
    .click();
  const panel = page.getByRole("region", {
    name: "chr20:35,430,145 C>G",
    exact: true,
  });
  await expect(panel).toBeInViewport();
  await expect(panel).toBeFocused();
  await expect(panel).toContainText("reference checked before prediction");
  await page
    .getByRole("row")
    .filter({ hasText: "rs143383" })
    .getByRole("button")
    .click();
  await expect(
    page.getByRole("region", { name: "rs143383", exact: true }),
  ).toBeInViewport();
});

test("public blood report calculates a sourced estimate, exports it and explains it in chat", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("button", { name: "Methylation Optional", exact: true })
    .click();
  await page
    .getByRole("button", { name: /Explore a public blood report/ })
    .click();
  const report = page.getByRole("region", { name: "Methylation age report" });
  await expect(report).toContainText("25.8");
  await expect(report).toContainText("21");
  await expect(report).toContainText("71 / 71 model sites");
  await expect(report).toContainText("not a good/bad health rating");
  await expect(report).toContainText("raw control probes");
  await expect(page.getByLabel("Active profile")).toHaveValue(
    await page
      .getByRole("option", { name: "GSM1009666 · public blood sample" })
      .getAttribute("value"),
  );
  await expect(
    page.getByRole("region", { name: "Repeat methylation tests" }),
  ).toContainText("Unknown dates and unmatched samples");
  await report
    .getByRole("button", { name: "Export report" })
    .scrollIntoViewIfNeeded();
  const download = page.waitForEvent("download");
  await report.getByRole("button", { name: "Export report" }).click();
  expect((await download).suggestedFilename()).toMatch(
    /^strand-methylation-.*\.json$/,
  );
  await expect(page.locator(".js-plotly-plot")).toHaveCount(1);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: "/tmp/strand-blood-report-desktop.png",
    fullPage: true,
  });
  await report.getByRole("button", { name: "Discuss this report" }).click();
  await expect(page.locator(".answer-card")).toContainText("25.8 years");
  await expect(page.locator(".answer-card")).toContainText(
    "not a health rating",
  );
});

test("regional cell-line sample shows exact missing report inputs without inventing age", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("button", { name: "Methylation Optional", exact: true })
    .click();
  await page
    .getByRole("button", { name: /Explore HG002 public methylation/ })
    .click();
  const report = page.getByRole("region", { name: "Methylation age report" });
  await expect(report).toContainText("0 / 71 model sites");
  await expect(report).toContainText("needs more information");
  await expect(report).toContainText(
    "cell lines, saliva and other tissues are outside scope",
  );
  await report
    .getByText("Missing model CpG identifiers", { exact: true })
    .click();
  await expect(report).toContainText("cg20822990");
  await expect(
    report.getByText("METHYLATION AGE ESTIMATE", { exact: true }),
  ).toHaveCount(0);
});

test("heart-rate questions perform a genotype lookup and answer directly about coverage", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("textbox", { name: "Ask a question about your data" })
    .fill("why is my resting heart rate so low, is it connected to genes?");
  await page.getByRole("button", { name: "Send question" }).click();
  const answer = page.locator(".answer-card");
  await expect(answer).toContainText(
    "I checked 9 published heart rate association markers against your 22 uploaded calls",
  );
  await expect(answer).toContainText("4 have an observed genotype");
  await expect(answer).toContainText("Your observed association loci include");
  await expect(answer).not.toContainText("this app");
  await expect(answer).not.toContainText("In Alex");
  await expect(
    page.locator(".activity-chip").filter({ hasText: "Genomics" }),
  ).toContainText("Checked 9 heart rate loci");
});

test("covered public family example shows actual PAH genotypes and excludes wearable-only partners", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("button", { name: "Family planning", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Use measured carrier example", exact: false })
    .click();
  await expect(page.getByLabel("Active profile")).toHaveValue(
    await page
      .getByRole("option", { name: "NA12043 · PAH inheritance example" })
      .getAttribute("value"),
  );
  await expect(page.getByLabel("Partner profile")).toHaveValue(
    await page
      .getByLabel("Partner profile")
      .getByRole("option", { name: "NA20332 · PAH inheritance example" })
      .getAttribute("value"),
  );
  const panel = page
    .locator(".family-card")
    .filter({ hasText: "Phenylketonuria" });
  await expect(panel).toContainText("G/A");
  await expect(panel).toContainText("25% two assessed alleles");
  await expect(
    page
      .getByLabel("Partner profile")
      .getByRole("option", { name: /PMData.*no DNA/ }),
  ).toBeDisabled();
  await expect(
    page.getByText("2 conditions are not covered by these files", {
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Cystic fibrosis", exact: true }),
  ).toHaveCount(0);
  await page.screenshot({
    path: "/tmp/strand-covered-family-demo.png",
    fullPage: true,
  });
});

test("same-person public methylation follow-up retains real collection years and no invented age difference", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByText("Explore covered demo examples", { exact: true })
    .click();
  await page.getByRole("button", { name: /Repeat methylation/ }).click();
  const reports = page.getByRole("region", { name: "Methylation age report" });
  await expect(reports).toHaveCount(2);
  await expect(reports.first()).toContainText("71 / 71 model sites");
  await expect(reports.first()).toContainText(
    "Individual age not reported; no difference calculated",
  );
  const timeline = page.getByRole("region", {
    name: "Repeat methylation tests",
  });
  await expect(timeline).toContainText("1997 → 2007");
  await expect(timeline).toContainText("10.00 calendar years");
  await expect(timeline).toContainText("exact days and months are unknown");
  await expect(page.locator(".js-plotly-plot")).toHaveCount(3);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: "/tmp/strand-repeat-methylation-demo.png",
    fullPage: true,
  });
});
