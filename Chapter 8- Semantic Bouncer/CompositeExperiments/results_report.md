# Chapter 8 Lab — Benchmark Results

**Test suite:** 60 sentences (35 should block, 25 should pass)

## Summary

| Setup | Accuracy | Precision | Recall | F1 | False Neg | False Pos | Avg ms | p95 ms |
|---|---|---|---|---|---|---|---|---|
| Local Ollama (llama3.2:1b) | 41.7% | 0.0% | 0.0% | 0.0% | 35 | 0 | 378ms | 345ms |
| Groq + Rule-Based Keywords | 78.3% | 95.8% | 65.7% | 78.0% | 12 | 1 | 0ms | 0ms |
| Groq + Presidio + Keywords | 63.3% | 93.3% | 40.0% | 56.0% | 21 | 1 | 21ms | 64ms |
| Groq + Embeddings | 86.7% | 86.5% | 91.4% | 88.9% | 3 | 5 | 24ms | 38ms |
| Groq + Enterprise Pipeline | 75.0% | 81.2% | 74.3% | 77.6% | 9 | 6 | 109ms | 95ms |

## Notes

- **False Negative** = sensitive input incorrectly allowed through (security risk)
- **False Positive** = benign input incorrectly blocked (usability cost)
- **Recall** = fraction of actual threats caught — the critical security metric
- All bouncer/scrubber costs are $0.00 — they run locally or rule-based.
  Token costs only apply to the downstream LLM task on CLEAN inputs.

## Misses per Setup

### Local Ollama (llama3.2:1b)

