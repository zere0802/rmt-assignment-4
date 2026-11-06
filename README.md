# Assignment 4 · Accuracy of LLM answers on established and recent CS topics

This repository reproduces the written report's results from the frozen RMT-CS-v2 evidence. The study evaluated 40 applied questions in three recorded model conditions (120 archived answers). It compares established concepts with recent software features. The analysis uses the archived checkpoint judgments and Appendix B error codes.

## Reproduce the results

From this repository's root, use Python 3.12 or newer. Both scripts use only the Python standard library.

```bash
python3 -m venv .venv
source .venv/bin/activate
python reproduce.py --verify
python figures.py --results reproduced --out reproduced/figures
diff -r figures reproduced/figures
```

The first script validates the SHA-256 of the original data export, checks the complete answer grid and paired question design, and regenerates five CSVs. Verification compares them against the committed outputs. The figure script creates two SVGs. A successful final diff prints no differences. No API keys, model requests, random seeds, or network access are required after obtaining the repository.

## Find a result

| Report evidence | File |
| --- | --- |
| Table 2, including GPT's 15 of 20 on recent questions | `results/main_results.csv` |
| Table 3, exact one-sided McNemar, Holm correction and paired bootstrap intervals | `results/paired_topic_comparisons.csv` |
| Table 4, strict scoring versus checkpoint-only scoring | `results/sensitivity.csv` |
| Appendix B, counts and case-level audit | `results/error_summary.csv` and `results/error_audit.csv` |
| Figures 1 and 2, regenerated from the CSVs | `figures/` |
| Raw answers, question pairs, checkpoints and source references | `data/Assignment3_Main_Experiment_Data.json` |
| Error coding decisions transcribed from Appendix B | `data/error_codes.csv` |

For the pick-a-number check, open the main results CSV and find the `GPT-6 Luna,recent` row. The fields `fully_correct=15` and `n=20` give 75.0%. The corresponding answer records have `condition_id=chatgpt` and `group=recent`.

## Source and scope

The JSON is an unchanged export from the [RMT-CS-v2 evidence archive](https://elaborate-starship-e9c848.netlify.app/), identified by SHA-256 `7ff20f027235b6d4c840b2ee82b0add6bb620b9374ada004779035bd2e34fe1d`. The figures and CSV formatting are regenerated in this implementation. The procedure checks the analysis of stored responses. New model queries would constitute a new collection. The local check is recorded in `verification_log.txt`. The separate independent reproduction is recorded in the report by the person who performs it.

The license applies to the analysis code. Original question, answer, and reference content retains its original attribution.
