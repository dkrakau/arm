import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql+psycopg2://postgres:admin@localhost:5432/openalex"  # test
WORK_TABLE = "openalex.work"

SCHEMA = {
    "research_field": "str",  # fachliche Disziplin, siehe RESEARCH_FIELDS
    "paper_type": "str",  # Art des Papers, siehe PAPER_TYPES
    "relevance": "str",  # Relevanz des Papers: high, middle, low
    "relevance_reason": "str",  # 1-2 Saetze Begruendung der Relevanz-Einstufung
    "research_focus": "str",  # zentrales Thema/Problem/Fragestellung des Papers
    "method": "str",  # Ansatz/Methode, mit der das Problem geloest wurde
    "mentioned_systems": "list",
    "indexing_methods": "list",
    "application_domain": "str",  # Anwendungsbereich INNERHALB des Papers, z.B. NLP, Bildsuche
    "results_summary": "str",  # 3-5 Saetze: wie wurde das Problem geloest, was kam raus
    "limitations": "list",  # einzelne genannte Limitationen als Liste
    "research_gaps": "list",  # einzelne offene Fragen/Future Work als Liste
}


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

    exclude = {"research_field", "paper_type"}
    schema_cols = [c for c in SCHEMA if c in df.columns and c not in exclude]
    missing_cols = [c for c in SCHEMA if c not in df.columns]
    if missing_cols:
        print(f"Warning: schema columns not in input: {missing_cols}")

    for (field, ptype), group in df.groupby(["research_field", "paper_type"]):
        work_ids = group["work_id"].astype(str)
        subfolder = group["open_access"].map(
            {True: "open_access", False: "not_open_access"}
        )
        meta = pd.DataFrame(
            {
                "work_id": work_ids,
                "title": group["title"],
                "openalex_link": "https://openalex.org/works/" + work_ids,
                "pdf_link": pdf_base + subfolder + "\\" + work_ids + ".pdf",
                "open_access": group["open_access"],
                "cite": group["cite"],
                "publication_date": group["publication_date"],
            }
        )
        result = pd.concat([meta, group[schema_cols]], axis=1)
        if "relevance" in result.columns:
            cols = [c for c in result.columns if c != "title"]
            cols.insert(cols.index("relevance") + 1, "title")
            result = result[cols]
        result["done"] = False
        result = result.sort_values("cite", ascending=False, na_position="last")
        filename = f"{field}.{ptype}.csv".replace(" ", "-").replace("/", "_")
        result.to_csv(out / filename, index=False)


def main():
    # df_open_access = pd.read_csv("../llm/llm_open_access.csv")
    # df_not_open_access = pd.read_csv("../llm/llm_not_open_access.csv")
    df_open_access = pd.read_csv("../llm/llm_open_access_with_relevance.csv")
    df_not_open_access = pd.read_csv("../llm/llm_not_open_access_with_relevance.csv")

    df_open_access["open_access"] = True
    df_not_open_access["open_access"] = False

    df = pd.concat([df_open_access, df_not_open_access], ignore_index=True)
    df = add_work_info(df)

    export_csvs(df)


if __name__ == "__main__":
    main()

# py export_csvs.py
