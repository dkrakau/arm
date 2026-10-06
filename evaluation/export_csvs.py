import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql+psycopg2://postgres:admin@localhost:5432/openalex"  # test
WORK_TABLE = "openalex.work"


def fetch_work_info(work_ids):
    """Return a DataFrame with work_id, title, cite and publication_date for the given work_ids."""
    engine = create_engine(DATABASE_URL)
    query = text(
        "SELECT id AS work_id, "
        "title, "
        "cited_by_count AS cite, "
        "(publication_date AT TIME ZONE 'UTC')::date AS publication_date "
        f"FROM {WORK_TABLE} "
        "WHERE id = ANY(:ids)"
    )
    with engine.connect() as conn:
        info = pd.read_sql(query, conn, params={"ids": work_ids})
    return info.drop_duplicates(subset="work_id")


def add_work_info(df):
    df["work_id"] = df["work_id"].astype(str)
    ids = df["work_id"].drop_duplicates().tolist()
    info = fetch_work_info(ids)
    df = df.merge(info, on="work_id", how="left", validate="many_to_one")
    df["cite"] = df["cite"].astype("Int64")

    missing = df["cite"].isna().sum()
    if missing:
        print(f"Warning: no cite found for {missing} of {len(df)} rows")
    return df


def export_csvs(df, output_folder="csv"):
    out = Path(output_folder)
    out.mkdir(parents=True, exist_ok=True)

    pdf_base = "C:\\Users\\Dominik\\Documents\\arm\\pdf\\"

    for (field, ptype), group in df.groupby(["research_field", "paper_type"]):
        work_ids = group["work_id"].astype(str)
        subfolder = group["open_access"].map(
            {True: "open_access", False: "not_open_access"}
        )
        result = pd.DataFrame(
            {
                "work_id": work_ids,
                "title": group["title"],
                "openalex_link": "https://openalex.org/works/" + work_ids,
                "pdf_link": pdf_base + subfolder + "\\" + work_ids + ".pdf",
                "open_access": group["open_access"],
                "cite": group["cite"],
                "publication_date": group["publication_date"],
                "done": False,
            }
        )
        result = result.sort_values("cite", ascending=False, na_position="last")
        filename = f"{field}.{ptype}.csv".replace(" ", "-").replace("/", "_")
        result.to_csv(out / filename, index=False)


def main():
    df_open_access = pd.read_csv("../llm/llm_open_access.csv")
    df_not_open_access = pd.read_csv("../llm/llm_not_open_access.csv")

    df_open_access["open_access"] = True
    df_not_open_access["open_access"] = False

    df = pd.concat([df_open_access, df_not_open_access], ignore_index=True)
    df = add_work_info(df)

    export_csvs(df)


if __name__ == "__main__":
    main()

# py export_csvs.py
