import pandas as pd


def filter_papers(df, field=None, ptype=None):
    mask = pd.Series(True, index=df.index)
    if field is not None:
        mask &= df["research_field"] == field
    if ptype is not None:
        mask &= df["paper_type"] == ptype
    return df[mask]


def main():
    df_open_access = pd.read_csv("llm_open_access.csv")
    df_not_open_access = pd.read_csv("llm_not_open_access.csv")

    df_open_access["open_access"] = True
    df_not_open_access["open_access"] = False

    df = pd.concat([df_open_access, df_not_open_access], ignore_index=True)

    print(
        f"#----------------------------------------------------------- COMBNINED ------------------------------------------------------------------------"
    )
    print(f"Total entries (combined): {len(df)}")

    field_counts = df["research_field"].value_counts(dropna=False)
    print("Entries for research_field (combined):")
    print(field_counts)
    print()

    crosstab = pd.crosstab(df["research_field"], df["paper_type"], dropna=False)
    print("Distribution of paper_types by research_field (combined):")
    print(crosstab)
    print()

    print(
        f"#---------------------------------------------------------- OPEN ACCESS -----------------------------------------------------------------------"
    )
    print(f"Total entries (open_access): {len(df_open_access)}")

    field_counts = df_open_access["research_field"].value_counts(dropna=False)
    print("Entries for research_field (open_access):")
    print(field_counts)
    print()

    crosstab = pd.crosstab(
        df_open_access["research_field"], df_open_access["paper_type"], dropna=False
    )
    print("Distribution of paper_types by research_field (open_access):")
    print(crosstab)
    print()

    print(
        f"#-------------------------------------------------------- NOT OPEN ACCESS ---------------------------------------------------------------------"
    )
    print(f"Total entries (not_open_access): {len(df_not_open_access)}")

    field_counts = df_not_open_access["research_field"].value_counts(dropna=False)
    print("Entries for research_field (not_open_access):")
    print(field_counts)
    print()

    crosstab = pd.crosstab(
        df_not_open_access["research_field"],
        df_not_open_access["paper_type"],
        dropna=False,
    )
    print("Distribution of paper_types by research_field (not_open_access):")
    print(crosstab)
    print()

    print(
        f"#------------------------------------------------------------- LIST --------------------------------------------------------------------------"
    )
    df_result = filter_papers(df, field="Computer Science", ptype="Survey/Review")
    for row in df_result.itertuples():
        print(f"https://openalex.org/works/{row.work_id}, {row.research_focus}")


if __name__ == "__main__":
    main()

# py llm_results.py
