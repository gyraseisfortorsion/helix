# Figma Make design integration

The local `figma mockup/` export is the visual source. No Figma browser access is required to maintain the implementation.

- `src/index.css` supplies the paper/card/ink palette, evidence colors, Fraunces/Inter/JetBrains Mono typography and 22px dotted background.
- `src/App.tsx` supplies the original helix logo component, Strand branding, numbered navigation, profile cards and evidence legend.
- The five source views supply chat presentation, source selection, molecular plot colors, wearable cards, conditional inheritance diagrams and the methylation lollipop chart/table.

The working application stays in `web/`. The mockup is retained as a reference. Existing data imports, conversations, agents, provider requests, profile isolation and optional methylation continue to use the real backend. Mockup example results, medical recommendations, scores and agent counters are not copied into the application.

Evidence tags map actual record categories to inherited genotype observations, measured data, publications and model predictions. Citations and the selectable evidence drawer use the answer's actual evidence IDs; older answers retain their own source catalogue. Mobile uses a modal drawer. Other views retain a source drawer through the Evidence button.

The source mockup has a fixed desktop sidebar. The implementation adds a compact mobile navigation, accessible profile picker and source drawer. Existing chat history, retries and upload controls remain available.

## Assets

The helix mark is copied from the provided React source, not recreated from a screenshot. The favicon is copied from the provided public folder.

Fonts are served locally from `web/public/fonts/`, with the original SIL Open Font License files included. The families and weights match the mockup's Google Fonts import:

- Fraunces 400/500/600
- Inter 400/500/600
- JetBrains Mono 400/500

The browser does not need to contact Google Fonts to render the interface.

## Verification

`npm run build` type-checks and bundles the application. `npm run test:e2e` checks the working journeys, including source selection in desktop and mobile chat, saved conversations, retry, original/public combined profile data, imports, charts, conditional inheritance, optional methylation and reference-only molecular calls.
