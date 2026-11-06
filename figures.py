"""Generate the two Assignment 4 charts as standalone SVG files."""

import argparse
import csv
from pathlib import Path
from xml.sax.saxutils import escape


def read_rows(folder, name):
    with (folder / f"{name}.csv").open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def text(x, y, value, size=16, anchor="start", bold=False):
    weight = "700" if bold else "400"
    return (f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{size}" '
            f'font-weight="{weight}">{escape(str(value))}</text>')


def rect(x, y, w, h, fill):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" rx="2"/>'


def chart_svg(title, width, height, content):
    header = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
              f'width="{width}" height="{height}" role="img"><title>{escape(title)}</title>')
    background = f'<rect width="{width}" height="{height}" fill="white"/>'
    content = [text(32, 38, title, 23, bold=True), *content]
    return "\n".join((header, background, '<g font-family="Arial, sans-serif" fill="#192b40">',
                      *content, "</g>", "</svg>", ""))


def accuracy_chart(results):
    established = [row for row in results if row["group"] == "established"
                   and row["condition"] != "All conditions"]
    recent = {row["condition"]: row for row in results if row["group"] == "recent"}
    colors = ("#244e78", "#057b72")
    plot = [text(32, 68, "Percent fully correct. Each bar represents 20 answers.", 14)]
    for i, label in enumerate(("Established", "Recent")):
        x = 515 + 115 * i
        plot += [rect(x, 78, 16, 16, colors[i]), text(x + 23, 91, label, 14)]
    bottom, scale = 345, 2.2
    for value in range(0, 101, 20):
        y = bottom - value * scale
        plot += [f'<path d="M 80 {y} H 745" stroke="#d9e1e9"/>',
                 text(69, y + 4, f"{value}%", 13, "end")]
    for i, first in enumerate(established):
        condition = first["condition"]
        center = 185 + i * 220
        for j, row in enumerate((first, recent[condition])):
            value = float(row["strict_percent"])
            x = center - 62 + j * 64
            y = bottom - value * scale
            plot += [rect(x, y, 60, value * scale, colors[j]),
                     text(x + 30, y - 8, f"{value:g}%", 14, "middle", True)]
        plot.append(text(center, bottom + 28, condition, 15, "middle", True))
    return chart_svg("Fully correct answers by topic group", 780, 402, plot)


def errors_chart(results):
    total = sum(int(row["count"]) for row in results)
    plot = [text(32, 68, f"One primary category per partial answer (n = {total}).", 14)]
    for i, row in enumerate(results):
        y = 94 + 43 * i
        count = int(row["count"])
        plot += [text(32, y + 19, row["category"], 15),
                 rect(283, y, count * 49, 26, "#244e78"),
                 text(294 + count * 49, y + 19, count, 15, bold=True)]
    return chart_svg("Primary error categories", 780, 330, plot)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path("results"))
    parser.add_argument("--out", type=Path, default=Path("figures"))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    charts = {
        "accuracy_by_topic.svg": accuracy_chart(read_rows(args.results, "main_results")),
        "error_categories.svg": errors_chart(read_rows(args.results, "error_summary")),
    }
    for filename, chart in charts.items():
        (args.out / filename).write_text(chart, encoding="utf-8")
    print(f"Two SVG charts written to {args.out}")


if __name__ == "__main__":
    main()
