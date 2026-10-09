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

RELEVANCE_TYPES = ["low", "middle", "high"]
RELEVANCE_COLUMN = "relevance"
RELEVANCE_ALIASES = {"mid": "middle", "medium": "middle"}
UNSET = "unset"


def is_true(series):
    return series.astype(str).str.strip().str.lower().isin(["true", "wahr"])


def get_relevance(df):
    """Normalised relevance per row; anything not in RELEVANCE_TYPES becomes 'unset'."""
    if RELEVANCE_COLUMN not in df.columns:
        return pd.Series(UNSET, index=df.index)
    rel = df[RELEVANCE_COLUMN].astype(str).str.strip().str.lower()
    rel = rel.replace(RELEVANCE_ALIASES)
    return rel.where(rel.isin(RELEVANCE_TYPES), UNSET)


def count_done(folder="excel"):
    rows = []
    for xlsx in sorted(Path(folder).glob("*.xlsm")):
        if xlsx.stem not in RESEARCH_FIELDS:
            continue
        sheets = pd.read_excel(xlsx, sheet_name=None)
        for ptype, df in sheets.items():
            if ptype not in PAPER_TYPES:
                continue
            done = is_true(df["done"])
            open_access = is_true(df["open_access"])
            relevance = get_relevance(df)
            for access, access_mask in [
                ("open_access", open_access),
                ("not_open_access", ~open_access),
            ]:
                for rel in RELEVANCE_TYPES + [UNSET]:
                    mask = access_mask & (relevance == rel)
                    rows.append(
                        {
                            "access": access,
                            "relevance": rel,
                            "research_field": xlsx.stem,
                            "paper_type": ptype,
                            "done": (done & mask).sum(),
                            "total": mask.sum(),
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


def print_headline(text, width=80):
    print("=" * width)
    print(text)
    print("=" * width)
    print()


def main():
    df = pd.DataFrame(count_done())
    df["research_field"] = df["research_field"].str.replace("-", " ")
    df["paper_type"] = df["paper_type"].str.replace("-", " ").str.replace("_", "/")

    print_headline("ACCESS")
    print_overview(df[df["access"] == "not_open_access"], "not_open_access")
    print_overview(df[df["access"] == "open_access"], "open_access")
    print_overview(df, "combined")

    print_headline("RELEVANCE")
    for rel in RELEVANCE_TYPES:
        print_overview(df[df["relevance"] == rel], f"relevance {rel}")

    unset = df[df["relevance"] == UNSET]
    if unset["total"].sum() > 0:
        print_overview(unset, "relevance unset")


if __name__ == "__main__":
    main()

# py status.py
