# Prompt versions

The same evaluation cases will be run with each prompt. This keeps the input constant while comparing prompt techniques.

| Version | Techniques introduced | Expected effect |
| --- | --- | --- |
| v1 | Direct zero-shot instruction and role framing | Baseline response; citations and uncertainty are encouraged but not constrained |
| v2 | Evidence-first decomposition, constrained JSON schema, explicit certainty taxonomy | More consistent structure and auditable claims |
| v3 | Structured output example, untrusted-data boundary, injection/leakage rules | Better citation behavior and resistance to hostile repository content |

All versions receive the same retrieval and the same provider-level JSON schema and system instruction. Thus this comparison measures differences between prompt texts within that common framework, not the effect of adding RAG. The examples are format examples, not a demonstrated few-shot technique. Results are hypotheses until real model responses are evaluated.

