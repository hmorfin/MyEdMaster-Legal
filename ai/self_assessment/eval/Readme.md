# Eval Pipeline — Legal KB Generation System

Tests each LLM stage independently with scored test cases.

## Structure

```
eval/
  eval_pipeline.py       # Core eval logic 
  test_eval_pipeline.py  # pytest integration
```

## Running

**All stages (CLI):**
```bash
python -m eval.eval_pipeline
```

**Specific stages:**
```bash
python -m eval.eval_pipeline --stage llm1,llm2,priority
```

**With pytest (skips LLM calls by default):**
```bash
pytest eval/test_eval_pipeline.py -v                    # unit tests only
SKIP_LLM_STAGES=0 pytest eval/test_eval_pipeline.py -v  # all including LLM
```

**Save results:**
```bash
python -m eval.eval_pipeline --output results/run_$(date +%Y%m%d).json
```

---

## Stages & what's checked

| Stage | Eval function | Key checks |
|---|---|---|
| LLM1 Classifier | `eval_llm1_classifier` | `legal_domain`, `branch`, `baseline_familiarity`, `primary_intent`, `confidence` in range, expected domain matches |
| LLM2 KB Generator | `eval_llm2_kb_generator` | Schema keys present, `rag_snippets` ≥ 3 and are strings, `few_shot_examples` has all 4 dimensions with `input`/`analysis` keys |
| LLM3 Audit | `eval_llm3_audit` | Valid `status` value, `issues` list, `recommendation` text, correct status for known-good and empty KB |
| LLM4 Example Gen | `eval_llm4_example_generator` | `example_text` ≥ 100 chars, `empty_template` and `fspr` present, situation not reused verbatim |
| Dim Evaluators | `eval_dimension_evaluators` | `dimension` matches input, `aspects` non-empty, all labels from valid set, `most_critical_gap` present |
| Priority Computation | `eval_priority_computation` | **No LLM** — unit tests `compute_full_priority_from_report` with known inputs and expected `top_dimension`/`top_label` |

---

## Scoring

Each check contributes equally. `score = checks_passed / total_checks`.

| Score | Status |
|---|---|
| ≥ 0.80 | PASS |
| 0.50 – 0.79 | WARN |
| < 0.50 | FAIL |

pytest thresholds: `MIN_PASS_RATE = 0.70`, `MIN_AVG_SCORE = 0.75`.

---

## Latency budgets

| Stage | Budget |
|---|---|
| LLM1 | 5 s |
| LLM2 | 30 s |
| LLM3 | 5 s |
| LLM4 | 10 s |
| Dim Evaluators | 10 s each |

---

## Adding test cases

All fixtures live in `eval_pipeline.py` as module-level lists:
- `CLASSIFIER_CASES` — add `input` + `expected` dict
- `KB_CASES` — add `input` only (schema validated)
- `AUDIT_CASES` — add `input` KB + `expected_status`
- `EXAMPLE_CASES` — add `input` only
- `DIM_EVAL_CASES` — add `input` with full KB content

Priority unit tests live inline in `eval_priority_computation`.