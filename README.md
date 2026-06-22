# SynthGen — Pre-Production Test Suite for AI Agents

Agnost tells you what's broken AFTER users get hurt. SynthGen predicts what WILL break before deploy.

## Data Flow

```
Company URL
    │
    ▼
[UNDERSTAND]   Scrape website → profile personas, intents, issues
    │
    ▼
[MATCH]        Detect sector → load pre-built library of REAL user complaints
               (600 fintech reviews, 400 insurtech reviews, ...)
    │
    ▼
[CLASSIFY]     LLM reads each review → assigns:
               • granular intent (15+ per sector)
               • atomic failure mode
               • severity (mild/medium/high/rage)
               • current_bad_response (what bad agent says)
               • expected_agent_behavior (tool-calls, not platitudes)
               • verification_scenarios (how to confirm fix)
    │
    ▼
[TEST SUITE]   Structured JSON → Agnost's auto-fix pipeline
               Coverage report: what's tested, what's missing
               Gaps: which intents have zero test cases
```

## What Makes It Different

| Other tools | SynthGen |
|---|---|
| Generate fake conversations with LLM | **Real complaints** from competitor apps' Google Play reviews |
| 3 vague intents | **15 granular intents** with atomic failure modes |
| "This tests technical issues" | `order_execution:slippage_acknowledgment` — machine-actionable tags |
| No bad response baseline | **current_bad_response** — what the agent does wrong now |
| "explain the issue to user" | `call_withdrawal_api(txn_id) → check_age → trigger_nodal_escalation()` |
| No way to verify | **verification_scenarios** — concrete tests per fix |
| Positive reviews mixed in | Separated into `test_cases_positive` vs `test_cases_negative` |
| Gibberish pollutes dataset | **Gibberish filter** — removes LLM sludge before classification |

## Features

- **Zero generated conversations** — 100% real user complaints from public app reviews
- **Sector library** — pre-built banks: fintech (600), insurtech (400), more on request
- **Auto-fix ready** — each case has: failure mode, bad response, expected fix, verification test
- **Coverage gaps** — explicit report of untested intents
- **Positive sentiment separation** — praise is not tagged as failure
- **Gibberish filter** — synthetic noise removed before classification
- **Any company URL** — scrape → profile → match → classify → suite

## Output Schema

```json
{
  "target_company": "Corgi Insurance",
  "coverage": {
    "granular_intents": { "covered": 10, "total": 15, "missing": ["..."] },
    "failure_modes": { "unique_tested": 15 },
    "severity": { "mild": 6, "medium": 11, "high": 12, "rage": 7 }
  },
  "test_cases_negative": [
    {
      "review_text": "...",
      "source_company": "PolicyBazaar",
      "intent_match_id": "withdrawal_failure",
      "failure_mode": "withdrawal_stuck_24hr",
      "severity": "high",
      "current_bad_response": "Please check your internet and try again.",
      "expected_agent_behavior": [
        "call_withdrawal_api(transaction_id)",
        "if age > 24h: trigger_nodal_escalation()",
        "send_sms_update(escalation_ref)"
      ],
      "tests_capability": "withdrawal:bank_credit_timeline",
      "verification_scenarios": [
        "withdrawal_stuck_3d_SBI",
        "withdrawal_stuck_1d_within_TAT"
      ]
    }
  ],
  "test_cases_positive": [...],
  "gaps": { "untested_intents": ["margin_shortfall_warning", "..."] }
}
```

## Use Cases

- **Pre-deployment** — test any company's agent before it goes live
- **Sprint regression** — re-test after prompt/tool changes
- **Competitor intelligence** — see what frustrates users of similar products
- **Coverage audit** — know exactly which intents your agent isn't tested against

## What You Need

```
Python 3.11+
Groq API key (free tier: ~1 full run/day, dev tier: unlimited)
```

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env
# Add your GROQ_API_KEY
python run.py
# Enter any company URL → get test suite in output/
```

## Project Structure

```
synthgen/
├── run.py                 # Pipeline orchestrator
├── scraper.py             # Website scraper (company understanding)
├── profiler.py            # Company profile builder
├── sectors.py             # Sector matching utilities
├── taxonomy.py            # 15+ granular intents per sector
├── classifier.py          # LLM classifier with auto-fix fields
├── scraper_reviews.py     # Review source scraper + language bank
├── build_sector_banks.py  # Pre-build sector data from app reviews
├── data/sectors/          # Pre-built sector libraries (600+ reviews each)
```

## Pre-Built Sectors

| Sector | Source Apps | Reviews |
|---|---|---|
| Fintech | Groww, Paytm, PhonePe | 600 |
| Insurtech | PolicyBazaar, Acko, Digit | 400 |

Run `python build_sector_banks.py <sector_name>` to add more.
