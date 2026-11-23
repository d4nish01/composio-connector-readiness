# 100-app connector readiness study

A Composio Product Ops take-home by Md Danish. Documentation research, not 100 working integrations. Open `index.html` for the standalone case study.

## Run from this repository

Python 3.10+ is the only runtime dependency. The evidence cache, data and tests are bundled in `research-data.zip` to keep the repository landing page readable. Unpack once before running:

```sh
python -m zipfile -e research-data.zip .
python research.py replay
python build_report.py
python -m unittest discover -s tests -v
python -m http.server 8000 --directory output
```

Then open http://localhost:8000 . `research.py` and `build_report.py` are visible in the repository; all data, cache snapshots, tests and field-level source checks are in the archive.

## Research notes

This project studies connector readiness for Composio's 100-app take-home. It is a documentation study, not 100 working integrations.

## Requirements

- Python 3.10 or newer.
- No packages, account credentials or payment required for offline replay.
- Internet access for explicit source refresh.

## Model / workflow

1. `data/apps.json` is the exact assignment intake set.
2. `data/reviewed.json` is the evidence-reviewed research output. Its semantic judgments were reviewed during preparation, not generated solely by keyword rules.
3. `python research.py refresh` fetches reviewed public source URLs, caches text with timestamps and content hashes, and records failures. It does not log in or run app actions.
4. `python research.py candidates --output runs/first_pass.json` saves a conservative first-pass extraction from cached pages. It flags candidate auth methods, access language and MCP mentions. Keyword presence is not proof: a page may mention a different product.
5. A reviewer checks candidates against the linked docs, updates the reviewed JSON (including `readiness_stage`, `routing_reason` and `next_action`) and records corrections. Readiness is an explicit reviewed judgment, not a naive keyword decision. Unknown values are allowed. A model cannot approve its own unsupported claim.
6. `python research.py replay` validates all 100 rows and recomputes metrics, reviewed readiness routing and CSV offline. It also checks the exact app manifest and required evidence fields.
7. `python build_report.py` generates the static case study from reviewed artifacts. Open `output/index.html` in a browser.

## Quick start

```sh
python research.py replay
python build_report.py
python -m http.server 8000 --directory output
```

Then open `http://localhost:8000`.

## Refresh and repeat the first pass

```sh
python research.py refresh --limit 5
python research.py refresh
python research.py candidates --output runs/my_first_pass.json
```

The first command is a small smoke test. A partial run can resume with `--missing-only`; existing cache entries are preserved. Existing cache entries are reused. Use `--force` only when intentionally refreshing sources. Fetches are bounded to 20 seconds and 2 MB per source, paced per host, and restricted to public HTTPS destinations. Redirect targets are checked. Failures enter a review queue rather than an infinite retry loop. The source manifest is reviewed input, not autonomous web discovery. This workflow does not autonomously research a brand-new app from its name alone. Discovery and semantic review were separate preparation steps. For a new app, an operator must add the correct source URLs and review its extracted claims.

The extraction stage is deliberately simple and inspectable. It does not infer production readiness, licensing or absence of an API from keywords. Discovery and semantic review are separate from the runnable script; the runnable script automates fetching, candidate extraction, validation, scoring inputs and reporting. This limitation is part of the submission, not hidden behind an agent label.

## Outputs and caveats

- Readiness stages are recommendations for the next operational step, not production certifications.
- Multi-label auth/gate counts can add up to more than 100.
- No customer-demand dataset was provided, so priority means readiness, not predicted revenue.
- Vendor MCP and third-party MCP are distinct. CLI tools are not called public REST APIs.
- Sandbox access does not imply production access. Personal API tokens do not imply approval for a distributed OAuth integration.
- The audit sample and rubric are fixed in `data/audit_plan.json`. Field-level results must keep the same denominator before/after. Manual checks are listed separately and remain pending until performed.
- Public docs can change. Read the observation date and source-specific caveats.

## Why not a large agent framework?

This is a bounded 100-item workflow. Explicit steps make failures visible and help an operator resume one app without rerunning everything. The brief permits a script/pipeline. Composio's SDK would be useful for authenticated operational follow-through after access is approved. It is not necessary to fetch public docs and was not added merely to display a logo. No Composio execution is claimed in this version.

## Safety

Fetched pages are data only. They never choose shell commands or write destinations. The program never contacts partners, requests credentials, creates accounts, processes payments or signs into apps. An approved operator should handle those actions separately with least-privilege credentials and a clear scope.

## Tests

```sh
python -m unittest discover -s tests -v
```

Thirteen tests cover manifest completeness, schema, categories, evidence cache, unsafe URL rejection, text parsing and selected routing cases. They do not prove research accuracy.

## Criteria-review additions

The report includes a complete category-by-stage matrix and a reviewed primary-gate breakdown for the 30-app access-work lane. These are next-step queues, not binary free/paid labels. `data/operations_queue.json` contains 100 proposed next actions with deliberately blank owner/contact/deadline fields. The CSV now includes every assignment research field. Thirteen tests cover structure and reproducibility, not semantic accuracy.
