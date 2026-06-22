# Precog — Pre-Production Test Suite for AI Agents

Agnost tells you what's broken AFTER users get hurt. Precog predicts what WILL break before deploy.

---

## The Problem

AI agents go live untested. No test suite. No QA. No regression. You only find out something is broken when users churn or leave bad reviews.

Agnost solves the detection problem — it reads conversations and surfaces what's breaking. But by the time Agnost knows, users are already frustrated.

Precog fills the pre-production gap: a structured test suite, built from real user complaints, delivered before your agent ever talks to a real customer.

---

## How It Works

```
COMPANY URL (e.g., groww.in, corgi.insure)
         │
         ▼
╔══════════════════════════════════════════╗
║  1. UNDERSTAND                           ║
║  ─────────────────────────               ║
║  Scrape website → build company profile  ║
║  • Business type, personas, intents     ║
║  • Known issues from help center/docs    ║
║  • Domain terminology, error scenarios   ║
╚══════════════════════════════════════════╝
         │
         ▼
╔══════════════════════════════════════════╗
║  2. MATCH                                ║
║  ──────────────────────                  ║
║  Detect sector → load pre-built library  ║
║  of REAL user complaints from competitor ║
║  apps (600+ reviews per sector)          ║
║  • fintech → Groww, Paytm, PhonePe      ║
║  • insurtech → PolicyBazaar, Digit      ║
║  • edtech, e-commerce, healthtech...    ║
╚══════════════════════════════════════════╝
         │
         ▼
╔══════════════════════════════════════════╗
║  3. CLASSIFY                             ║
║  ─────────────────────                   ║
║  LLM reads each real review → assigns:   ║
║  • granular intent (15+ per sector)     ║
║  • atomic failure mode                  ║
║  • severity (mild/medium/high/rage)     ║
║  • current_bad_response (what bad agent  ║
║    currently says)                       ║
║  • expected_agent_behavior (tool-calls)  ║
║  • verification_scenarios (how to test   ║
║    the fix)                              ║
║  Positives → separate category           ║
║  Gibberish → filtered out                ║
╚══════════════════════════════════════════╝
         │
         ▼
╔══════════════════════════════════════════╗
║  4. TEST SUITE                           ║
║  ──────────────────────                  ║
║  Structured JSON → Agnost's pipeline     ║
║  • Coverage: 60-80% granular intents    ║
║  • Gaps: untested intents listed         ║
║  • Severity distribution                 ║
║  • Each case is auto-fix ready           ║
╚══════════════════════════════════════════╝
```

---

## Real Output Sample

This is an actual test case from `output/groww_test_suite.json` — a real user complaint from Groww's Google Play reviews, classified and auto-fix-ready:

```json
{
  "review_text": "Unable to track external Stock Portfolios of Zerodha, Mstock, ICICI Direct in the App. On trying to track it always showing as in Progress for the last several week's. I have uninstalled the app and cleared the cache. I suppose there is some Glitch kindly do the needful at the earliest.",
  "source_company": "Groww",
  "intent_match_id": "chart_data_staleness",
  "failure_mode": "intraday_charts_not_updating_in_real_time",
  "severity": "medium",
  "current_bad_response": "Please try again later.",
  "expected_agent_behavior": [
    "query_chart_data_status(app_id) → check if last_updated < 1h → if yes, trigger_chart_update()"
  ],
  "tests_capability": "data:chart_update",
  "verification_scenarios": [
    "chart_data_stale_1h",
    "chart_data_stale_24h",
    "chart_data_stale_1week"
  ]
}
```

### What's Inside Each Test Case

| Field | What it means for auto-fix |
|---|---|
| `review_text` | The real human complaint — raw, authentic, not generated |
| `source_company` | Which app the review came from (competitor intelligence) |
| `intent_match_id` | Which granular capability this tests (15+ per sector) |
| `failure_mode` | The specific thing that went wrong (machine-actionable) |
| `severity` | Emotional intensity — prioritizes what to fix first |
| `current_bad_response` | What a bad agent would say to this user (the **before** state) |
| `expected_agent_behavior` | Tool-calls and logic the agent should execute (the **after** state) |
| `tests_capability` | Atomic tag for the fix system to route this case |
| `verification_scenarios` | Concrete tests to confirm the fix works (close the loop) |

### Coverage Report (from the same run)

```json
{
  "granular_intents": "60% covered (9/15)",
  "failure_modes": "13 unique tested",
  "total_cases": "35 (30 failures + 5 positive)",
  "severity": { "mild": 4, "medium": 4, "high": 13, "rage": 9 },
  "gaps": ["kyc_verification_status", "margin_shortfall_warning",
           "ipo_allotment_status", "mutual_fund_switch_or_redemption",
           "pledged_stock_unavailability", "tax_report_generation"]
}
```

---

## What Makes It Different

| Other approaches | Precog |
|---|---|---|
| Generate fake conversations with LLM | **Real complaints** from competitor apps' Google Play reviews |
| 3 vague intents | **15 granular intents** with atomic failure modes per sector |
| "This tests technical issues" | `order_execution:slippage_acknowledgment` — machine-actionable |
| No bad response baseline | **current_bad_response** — what the agent does wrong right now |
| "explain the issue to user" | `call_withdrawal_api(txn_id) → check_age → trigger_nodal_escalation()` |
| No way to verify a fix | **verification_scenarios** — concrete tests to confirm resolution |
| Positive reviews pollute failure data | Separated into `test_cases_positive` vs `test_cases_negative` |
| Synthetic gibberish in output | **Gibberish filter** removes noise before classification |
| One-size-fits-all intents | **Sector-specific taxonomy** — fintech, insurtech, more |

---

## Features

- **Zero generated conversations** — 100% real user complaints from public app reviews
- **Sector library** — pre-built banks of 400-600+ real reviews each
- **Auto-fix ready** — each case carries: failure mode, bad response, expected behavior, verification test
- **Coverage gaps** — explicit list of untested intents per sector
- **Positive sentiment separated** — praise is not mislabeled as failure
- **Gibberish filter** — synthetic sludge removed before classification
- **Any company URL** — scrape → profile → match → classify → suite in one command
- **Competitor intelligence** — sourced from real complaints against competitor apps

---

## Use Cases

- **Pre-deployment** — test any company's agent before it goes live
- **Sprint regression** — re-test after prompt/tool/rag changes
- **Competitor benchmarking** — see what frustrates users of similar products
- **Coverage audit** — know exactly which intents your agent has no test data for
- **Auto-fix training** — seed your fix system with structured before/after pairs

---

## Pre-Built Sectors

| Sector | Source Apps | Real Reviews |
|---|---|---|
| Fintech | Groww, Paytm, PhonePe | 600 |
| Insurtech | PolicyBazaar, Digit Insurance | 400 |

Run `python build_sector_banks.py <sector_name>` to add more.

---

## Project Structure

```
synthgen/
├── run.py                 # Pipeline orchestrator
├── scraper.py             # Website scraper (company understanding)
├── profiler.py            # Company profile builder (LLM)
├── sectors.py             # Sector matching + cache loaders
├── taxonomy.py            # 15+ granular intents per sector
├── classifier.py          # LLM classifier with auto-fix fields
├── scraper_reviews.py     # Review source scraper
├── build_sector_banks.py  # Build sector data from app stores
├── data/sectors/          # Pre-built libraries (600+ reviews each)
├── output/                # Generated test suites
```

---

## What This Is Not

- Not a conversation generator — no fake multi-turn data
- Not an agent — you feed the output into Agnost
- Not production-ready data for training — this is a **test suite** for pre-production QA
