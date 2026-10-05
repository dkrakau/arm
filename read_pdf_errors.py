from pathlib import Path
import pandas as pd

ERROR_LOG_DIR = Path("pdf/open_access/error_log")
ERROR_LOG_DIR.mkdir(exist_ok=True)


# Just for debugging pdf downloads
def main():

    df = pd.read_csv(ERROR_LOG_DIR / "errors.log")
    print(f"Total entries: {len(df)}")

    start = 121
    end = 122

    for i in range(start, end):
        row = df.iloc[i]
        id = row["id"]
        doi = row["error_message"]
        print(f"{i}   {id}   https://openalex.org/works/{id}   {doi}")


if __name__ == "__main__":
    main()
