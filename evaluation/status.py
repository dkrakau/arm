import pandas as pd
from pathlib import Path

RESEARCH_FIELDS = [
    "Computer-Science",
    "Medicine",
    "Biology",
    "Geology",
    "Physics",
    "Chemistry",
    "Mathematics",
    "Geography",
    "Engineering",
    "Social-Sciences",
    "Economics",
    "Other",
]

PAPER_TYPES = [
    "Survey_Review",
    "System_Tool-Paper",
    "Benchmark_Evaluation-Paper",
    "Position_Vision-Paper",
    "Case-Study_Application-Paper",
    "Other",
]


def count_done(folder):
    rows = []
    for xlsx in sorted((Path(folder) / "excel").glob("*.xlsx")):
        if xlsx.stem not in RESEARCH_FIELDS:
            continue
        sheets = pd.read_excel(xlsx, sheet_name=None)
        for ptype, df in sheets.items():
            if ptype not in PAPER_TYPES:
                continue
            done = df["done"].astype(str).str.strip().str.lower().isin(["true", "wahr"])
            rows.append(
                {
                    "access": folder,
                    "research_field": xlsx.stem,
                    "paper_type": ptype,
                    "done": done.sum(),
                    "total": len(df),
                }
            )
    return rows


def print_overview(df, title):
    done = df.pivot_table(
        index="research_field",
        columns="paper_type",
        values="done",
        aggfunc="sum",
        fill_value=0,
    )
    total = df.pivot_table(
        index="research_field",
        columns="paper_type",
        values="total",
        aggfunc="sum",
        fill_value=0,
    )
    table = done.astype(str) + " / " + total.astype(str)
    gap = 4

    print(f"{title}: {df['done'].sum()} / {df['total'].sum()} done")
    print(table.to_string(col_space={c: len(c) + gap for c in table.columns}))
    print()


def main():
    df = pd.DataFrame(count_done("open_access") + count_done("not_open_access"))
    df["research_field"] = df["research_field"].str.replace("-", " ")
    df["paper_type"] = df["paper_type"].str.replace("-", " ").str.replace("_", "/")

    print_overview(df, "combined")
    print_overview(df[df["access"] == "open_access"], "open_access")
    print_overview(df[df["access"] == "not_open_access"], "not_open_access")


if __name__ == "__main__":
    main()

# py status.py
