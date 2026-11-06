"""Recompute Assignment 4 results from the archived answers and rating decisions."""

import argparse
from collections import Counter
import csv
from fractions import Fraction
import hashlib
import json
from math import comb
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
ARCHIVE = DATA / "Assignment3_Main_Experiment_Data.json"
ARCHIVE_SHA = "7ff20f027235b6d4c840b2ee82b0add6bb620b9374ada004779035bd2e34fe1d"
GROUPS = ("established", "recent")
ERROR_TYPES = {
    "API": "API or configuration detail",
    "REL": "Release or platform boundary",
    "ADD": "Added claim error",
    "OMIT": "Required detail omitted",
    "TYPE": "Type precision",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fully_correct(answer):
    return answer["points"] == 3 and not answer["material_additional_error"]


def percentage(count, total):
    return f"{100 * count / total:.1f}"


def read_archive():
    raw = ARCHIVE.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == ARCHIVE_SHA, "Unexpected archive checksum")
    archive = json.loads(raw)
    questions = {question["display_id"]: question for question in archive["questions"]}
    conditions = {row["condition_id"]: row["model_label"] for row in archive["model_conditions"]}
    answers = {(row["condition_id"], row["question_id"]): row for row in archive["responses"]}
    require(len(questions) == 40 and len(conditions) == 3, "Unexpected study design")
    require(len(archive["responses"]) == len(answers) == 120, "Duplicate or missing answers")
    require(set(answers) == {(c, q) for c in conditions for q in questions}, "Incomplete answer grid")
    for (_, question_id), row in answers.items():
        question = questions[question_id]
        require(all(row[key] == question[key] for key in ("group", "pair_id", "ecosystem", "block")),
                f"Question metadata mismatch for {question_id}")
        checkpoints = row["checkpoint_points"]
        require(len(checkpoints) == 3 and set(checkpoints) <= {0, 1}, "Invalid checkpoint scores")
        require(sum(checkpoints) == row["points"], "Checkpoint total mismatch")
        require(fully_correct(row) == (row["category"] == "correct"), "Rating category mismatch")
    pairs = {}
    for question_id, row in questions.items():
        pair = pairs.setdefault(row["pair_id"], {})
        require(row["group"] not in pair, "Duplicate group within a matched pair")
        pair[row["group"]] = question_id
    require(len(pairs) == 20 and all(set(pair) == set(GROUPS) for pair in pairs.values()),
            "Incomplete matched pairs")
    return conditions, answers, pairs


def table_metrics(conditions, answers):
    main = []
    sensitivity = []
    for condition in [*conditions, "all"]:
        label = conditions.get(condition, "All conditions")
        rows = [row for (c, _), row in answers.items() if c == condition or condition == "all"]
        scores = {}
        for group in (*GROUPS, "overall"):
            selected = [row for row in rows if row["group"] == group or group == "overall"]
            n = len(selected)
            counts = Counter(row["category"] for row in selected)
            correct = sum(fully_correct(row) for row in selected)
            checkpoint_only = sum(row["points"] == 3 for row in selected)
            points = sum(row["points"] for row in selected)
            scores[group] = (Fraction(correct, n), Fraction(checkpoint_only, n))
            main.append((label, group, n, correct, counts["partial"], counts["incorrect"],
                         counts["abstain"], counts["missing"], percentage(correct, n), points,
                         n * 3, percentage(points, n * 3)))
            sensitivity.append((label, group, n, correct, checkpoint_only, percentage(correct, n),
                                percentage(checkpoint_only, n)))
        established, recent = (scores[group] for group in GROUPS)
        sensitivity.append((label, "established-minus-recent (pp)", "", "", "",
                            percentage(established[0] - recent[0], 1),
                            percentage(established[1] - recent[1], 1)))
    return main, sensitivity


def paired_interval(differences):
    """Calculate percentiles of the exact empirical paired bootstrap distribution."""
    n = len(differences)
    counts = Counter(differences)
    distribution = Counter({0: 1})
    for _ in range(n):
        next_distribution = Counter()
        for total, weight in distribution.items():
            for difference, frequency in counts.items():
                next_distribution[total + difference] += weight * frequency
        distribution = next_distribution

    def quantile(probability):
        cumulative = 0
        threshold = probability * n ** n
        for total, weight in sorted(distribution.items()):
            cumulative += weight
            if cumulative >= threshold:
                return Fraction(100 * total, n)
        raise ValueError("Invalid bootstrap quantile")

    return quantile(Fraction(1, 40)), quantile(Fraction(39, 40))


def paired_results(conditions, answers, pairs):
    rows = []
    for condition, label in conditions.items():
        differences = [
            int(fully_correct(answers[condition, pair["established"]]))
            - int(fully_correct(answers[condition, pair["recent"]]))
            for pair in pairs.values()
        ]
        established_only, recent_only = differences.count(1), differences.count(-1)
        discordant = established_only + recent_only
        p = Fraction(sum(comb(discordant, k) for k in range(established_only, discordant + 1)),
                     2 ** discordant)
        lower, upper = paired_interval(differences)
        rows.append((label, len(pairs), established_only, recent_only,
                     Fraction(100 * sum(differences), len(pairs)), lower, upper, p))

    adjusted = {}
    largest = Fraction(0)
    for index, row in enumerate(sorted(rows, key=lambda row: row[-1])):
        label, p = row[0], row[-1]
        largest = min(Fraction(1), max(largest, (len(rows) - index) * p))
        adjusted[label] = largest
    return [
        (label, n, established, recent, float(gap), float(low), float(high),
         f"{p:.4f}", f"{adjusted[label]:.4f}")
        for label, n, established, recent, gap, low, high, p in rows
    ]


def error_results(conditions, answers):
    with (DATA / "error_codes.csv").open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    coded = {(row["condition_id"], row["question_id"]): row for row in rows}
    require(len(coded) == len(rows), "Duplicate error code for an answer")
    require(set(coded) == {key for key, row in answers.items() if not fully_correct(row)},
            "Error codes must cover every answer below full correctness")
    counts = Counter(row["code"] for row in rows)
    require(set(counts) <= set(ERROR_TYPES), "Unknown error code")
    summary = [(code, label, counts[code], percentage(counts[code], len(rows)))
               for code, label in ERROR_TYPES.items()]
    audit = []
    for key, row in coded.items():
        answer = answers[key]
        audit.append((key[1], conditions[key[0]], answer["group"], answer["points"],
                      answer["material_additional_error"], row["code"], row["observation"]))
    return summary, audit


def write_csv(out, name, fields, rows):
    with (out / f"{name}.csv").open("w", encoding="utf-8", newline="") as target:
        writer = csv.writer(target, lineterminator="\n")
        writer.writerow(fields.split())
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "reproduced")
    parser.add_argument("--verify", action="store_true", help="compare with the reference CSVs")
    args = parser.parse_args()
    conditions, answers, pairs = read_archive()
    main_rows, sensitivity = table_metrics(conditions, answers)
    paired = paired_results(conditions, answers, pairs)
    error_summary, error_audit = error_results(conditions, answers)
    args.out.mkdir(parents=True, exist_ok=True)
    write_csv(args.out, "main_results",
              "condition group n fully_correct partial incorrect abstain missing strict_percent "
              "checkpoint_points checkpoint_max checkpoint_percent", main_rows)
    write_csv(args.out, "paired_topic_comparisons",
              "condition pairs established_only recent_only gap_pp ci_low_pp ci_high_pp raw_p holm_p",
              paired)
    write_csv(args.out, "sensitivity",
              "condition group n strict_correct checkpoint_only_correct strict_percent checkpoint_only_percent",
              sensitivity)
    write_csv(args.out, "error_summary", "code category count percent", error_summary)
    write_csv(args.out, "error_audit", "question_id condition group points added_error code observation",
              error_audit)
    if args.verify:
        reference = ROOT / "results"
        for file in sorted(reference.glob("*.csv")):
            require(file.read_bytes() == (args.out / file.name).read_bytes(), f"Mismatch: {file.name}")
        require(len(list(reference.glob("*.csv"))) == 5, "Expected five reference CSVs")
    overall = next(row for row in main_rows if row[:2] == ("All conditions", "overall"))
    print(f"{overall[3]}/{overall[2]} fully correct; {overall[9]}/{overall[10]} checkpoint points")
    print("Five CSV tables verified." if args.verify else f"Five CSV tables written to {args.out}")


if __name__ == "__main__":
    main()
