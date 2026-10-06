import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql+psycopg2://postgres:admin@localhost:5432/openalex"  # test
CITE_TABLE = "openalex.work"
CITE_ID_COLUMN = "id"
CITE_COLUMN = "cited_by_count"


def fetch_cites(work_ids):
    """Return a DataFrame with work_id and cite for the given work_ids."""
    engine = create_engine(DATABASE_URL)
    query = text(
        f"SELECT {CITE_ID_COLUMN} AS work_id, {CITE_COLUMN} AS cite "
        f"FROM {CITE_TABLE} "
        f"WHERE {CITE_ID_COLUMN} = ANY(:ids)"
    )
    with engine.connect() as conn:
        cites = pd.read_sql(query, conn, params={"ids": work_ids})
    return cites.drop_duplicates(subset="work_id")


def add_cites(df):
    df["work_id"] = df["work_id"].astype(str)
    ids = df["work_id"].drop_duplicates().tolist()
    cites = fetch_cites(ids)
    df = df.merge(cites, on="work_id", how="left", validate="many_to_one")
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
                "openalex_link": "https://openalex.org/works/" + work_ids,
                "pdf_link": pdf_base + subfolder + "\\" + work_ids + ".pdf",
                "open_access": group["open_access"],
                "cite": group["cite"],
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
    df = add_cites(df)

    export_csvs(df)


if __name__ == "__main__":
    main()

# py export_csvs.py
