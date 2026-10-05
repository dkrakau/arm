import pandas as pd
from pathlib import Path


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
                "done": False,
            }
        )
        filename = f"{field}.{ptype}.csv".replace(" ", "-").replace("/", "_")
        result.to_csv(out / filename, index=False)


def main():
    df_open_access = pd.read_csv("../llm/llm_open_access.csv")
    df_not_open_access = pd.read_csv("../llm/llm_not_open_access.csv")

    df_open_access["open_access"] = True
    df_not_open_access["open_access"] = False

    df = pd.concat([df_open_access, df_not_open_access], ignore_index=True)

    export_csvs(df)


if __name__ == "__main__":
    main()

# py export_csvs.py
