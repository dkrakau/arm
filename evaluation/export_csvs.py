import pandas as pd
from pathlib import Path


def filter_papers(df, field=None, ptype=None):
    mask = pd.Series(True, index=df.index)
    if field is not None:
        mask &= df["research_field"] == field
    if ptype is not None:
        mask &= df["paper_type"] == ptype
    return df[mask]


def export_csvs(df, output_folder):
    out = Path(output_folder) / "csv"
    out.mkdir(parents=True, exist_ok=True)

    pdf_base = "C:\\Users\\Dominik\\Documents\\arm\\pdf\\"

    for (field, ptype), group in df.groupby(["research_field", "paper_type"]):
        work_ids = group["work_id"].astype(str)
        result = pd.DataFrame(
            {
                "work_id": work_ids,
                "openalex_link": "https://openalex.org/works/" + work_ids,
                "pdf_link": pdf_base + output_folder + "\\" + work_ids + ".pdf",
                "done": False,
            }
        )
        filename = f"{field}.{ptype}.csv".replace(" ", "-").replace("/", "_")
        result.to_csv(out / filename, index=False)


def main():
    df_open_access = pd.read_csv("../llm/llm_open_access.csv")
    df_not_open_access = pd.read_csv("../llm/llm_not_open_access.csv")

    export_csvs(df_open_access, "open_access")
    export_csvs(df_not_open_access, "not_open_access")


if __name__ == "__main__":
    main()

# py export_csvs.py
