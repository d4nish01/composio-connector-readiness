# Source review checklist

Five apps have a source cross-check: 20 fields, 16 supported, none wrong and 4 unresolved. All unresolved fields are Paygent Connect, whose vendor identity is not established. Do not treat NMI background as Paygent evidence.

The planned sample is 20 apps across all ten categories, with four fields per app. The five-app check is preliminary, not an accuracy estimate for all 100 apps. It does not complete the assignment's requested manual sample review. No manual review by the candidate is claimed.

## Check the sources yourself

- Grain: https://support.grain.com/en/articles/15507288-grain-api . Compare free personal access with paid/admin workspace tokens.
- Higgsfield: https://higgsfield.ai/creator-hub/help-center/integrations/how-do-i-connect-higgsfield-to-ai-agent . MCP needs a paid subscription, browser authorization and account credits.
- Plaid: https://plaid.com/docs/sandbox/ . Sandbox is test data; eligible US/Canada teams created from 15 April 2026 can use a limited Trial with real data.
- Paygent Connect: exact vendor identity remains open. Ask for the vendor domain before scoring upstream NMI facts.
- Mermaid CLI: https://github.com/mermaid-js/mermaid-cli . Local renderer, not a hosted REST API.

## Record what was actually checked

Use data/source_review_scorecard.csv for the full sample. Record supported, wrong or unresolved, the exact URL, reason and date. Keep unresolved fields in the denominator. Preserve the old value before changing data/reviewed.json.

The separate data/auth_before_after_scorecard.csv holds saved keyword candidates beside reviewed methods for the same 20 apps. Score both with the same rubric. It can support an auth-family diagnostic only. Do not invent missing first-pass answers for access, API surface or MCP. Findings and scores belong on the page only after those checks are performed.
