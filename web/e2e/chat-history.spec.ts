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

async function send(page: import("@playwright/test").Page, question: string) {
  await page
    .getByRole("textbox", { name: "Ask a question about your data" })
    .fill(question);
  await page
    .getByRole("button", { name: "Send question", exact: true })
    .click();
  await expect(page.locator(".working")).toHaveCount(0);
}

test("separate saved chats restore their own messages after reload and suggested prompts append a turn", async ({
  page,
}) => {
  await page.goto("/");
  await send(page, "Could my knee pain be genetic?");
  await expect(
    page.getByRole("heading", {
      name: "Genetic context for your joint question",
    }),
  ).toBeVisible();
  await page.getByRole("button", { name: "New chat", exact: true }).click();
  await expect(page.locator(".conversation .turn")).toHaveCount(0);
  await send(page, "Explain methylation");
  await expect(
    page.getByRole("heading", {
      name: "Methylation is an optional measurement",
    }),
  ).toBeVisible();
  await page
    .locator(".sidebar")
    .getByRole("button", {
      name: "Open chat: Could my knee pain be genetic?",
      exact: true,
    })
    .click();
  await expect(page.locator(".user-question")).toHaveText(
    "YOUCould my knee pain be genetic?",
  );
  await page.reload();
  await expect(
    page.getByRole("heading", {
      name: "Genetic context for your joint question",
    }),
  ).toBeVisible();
  await expect(page.locator(".conversation .turn")).toHaveCount(1);
  await page
    .locator(".suggested-prompts")
    .getByRole("button", {
      name: "What data would help answer this?",
      exact: true,
    })
    .click();
  await expect(page.locator(".conversation .answer-card")).toHaveCount(2);
  await page.getByRole("button", { name: "New chat", exact: true }).click();
  await expect(page.locator(".conversation .turn")).toHaveCount(0);
  await expect(page.locator(".sidebar .chat-list-item")).toHaveCount(3);
});

test("reference-only call is explained and cannot queue a molecular run", async ({
  page,
}) => {
  let runs = 0;
  page.on("request", (request) => {
    if (
      request.url().endsWith("/api/investigations") &&
      request.method() === "POST"
    )
      runs++;
  });
  await page.goto("/");
  await page
    .getByRole("button", { name: "Genetic findings", exact: true })
    .click();
  await page
    .getByRole("row")
    .filter({ hasText: "rs5030858" })
    .getByRole("button")
    .click();
  await expect(page.locator(".eligibility-notice")).toContainText(
    "G/G, matching the reference G",
  );
  await expect(
    page.getByRole("button", {
      name: "Run molecular investigation",
      exact: true,
    }),
  ).toBeDisabled();
  expect(runs).toBe(0);
  await page
    .getByRole("row")
    .filter({ hasText: "rs143383" })
    .getByRole("button")
    .click();
  await expect(page.locator(".eligibility-notice")).toHaveCount(0);
  await page.screenshot({
    path: "/tmp/strand-investigate-desktop.png",
    fullPage: true,
  });
});

test("answer citations select their source and the evidence drawer works on mobile", async ({
  page,
}) => {
  await page.goto("/");
  await send(page, "Could my knee pain be genetic?");
  const citation = page.locator(".answer-sources .citation-ref").first();
  const title = await citation.getAttribute("title");
  await citation.click();
  await expect(
    page.locator(".workspace-columns > .evidence-panel h3"),
  ).toHaveText(title!);
  await expect(
    page.locator(".workspace-columns > .evidence-panel .evidence-limitation"),
  ).toBeVisible();
  await page.locator(".conversation").evaluate((e) => (e.scrollTop = 0));
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: "/tmp/strand-chat-desktop.png" });
  await page.setViewportSize({ width: 390, height: 844 });
  await citation.click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(
    page.getByRole("dialog").locator(".evidence-card h3"),
  ).toHaveText(title!);
  await expect(
    page
      .getByRole("dialog")
      .getByRole("link", { name: /Read original source/ }),
  ).toHaveAttribute("href", /^https:\/\//);
  await page
    .getByRole("button", { name: "Close evidence drawer", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(page.locator(".conversation .turn")).toHaveCount(1);
  await page.locator(".conversation").evaluate((e) => (e.scrollTop = 0));
  await page.screenshot({ path: "/tmp/strand-chat-mobile.png" });
});

test("saved failed answer can be retried without duplicating the question", async ({
  page,
  request,
}) => {
  await page.goto("/");
  const session = await page.evaluate(() =>
    JSON.parse(sessionStorage.getItem("helix.session.v1")!),
  );
  const headers = { Authorization: "Bearer " + session.token };
  const posted = await request.post("/api/messages", {
    headers,
    data: {
      profile_id: session.profiles[0].id,
      question: "Could my knee pain be genetic?",
    },
  });
  const result = await posted.json();
  await expect
    .poll(
      async () =>
        (
          await (
            await request.get(`/api/jobs/${result.job_id}`, { headers })
          ).json()
        ).status,
    )
    .toBe("completed");
  let injectFailure = true;
  await page.route("**/api/conversations/*", async (route) => {
    const response = await route.fetch();
    const data = await response.json();
    if (injectFailure && data.messages?.length) {
      injectFailure = false;
      data.messages[0] = {
        ...data.messages[0],
        status: "failed",
        answer: null,
        error: "UsageLimitExceeded: test transport fixture",
      };
    }
    await route.fulfill({ response, json: data });
  });
  await page.reload();
  await expect(page.locator(".conversation .error")).toContainText(
    "analysis reached its budget",
  );
  await page.getByRole("button", { name: "Retry answer", exact: true }).click();
  await expect(
    page.getByRole("heading", {
      name: "Genetic context for your joint question",
    }),
  ).toBeVisible();
  await expect(page.locator(".conversation .turn")).toHaveCount(1);
  const history = await (
    await request.get(`/api/conversations/${result.conversation_id}`, {
      headers,
    })
  ).json();
  expect(history.messages).toHaveLength(1);
});

test("mobile chat history stays accessible and conversations remain profile-specific", async ({
  page,
}) => {
  await page.goto("/");
  await send(page, "Could my knee pain be genetic?");
  await expect(page.locator(".answer-card")).toHaveCount(1);
  await page.getByLabel("Active profile").selectOption({ label: "Sam Chen" });
  await expect(page.locator(".conversation .turn")).toHaveCount(0);
  await page
    .getByLabel("Active profile")
    .selectOption({ label: "Alex Morgan" });
  await expect(page.locator(".answer-card")).toHaveCount(1);
  await page.setViewportSize({ width: 390, height: 844 });
  await page
    .getByRole("button", { name: "Open chat history", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page
    .getByRole("dialog")
    .getByRole("button", {
      name: "Open chat: Could my knee pain be genetic?",
      exact: true,
    })
    .click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});
