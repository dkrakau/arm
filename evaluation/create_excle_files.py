import pandas as pd
from pathlib import Path


def export_excels(csv_folder="csv", output_folder="excel"):
    csv_dir = Path(csv_folder)
    out = Path(output_folder)
    out.mkdir(parents=True, exist_ok=True)

    files_by_field = {}
    for csv_file in sorted(csv_dir.glob("*.csv")):
        field, ptype = csv_file.stem.split(".", 1)
        files_by_field.setdefault(field, []).append((ptype, csv_file))

    for field, files in files_by_field.items():
        with pd.ExcelWriter(out / f"{field}.xlsx") as writer:
            for ptype, csv_file in files:
                df = pd.read_csv(csv_file, dtype=str)  # to keep values as "False"
                df.to_excel(writer, sheet_name=ptype[:31], index=False)


def main():
    export_excels()


if __name__ == "__main__":
    main()

# py create_excle_files.py
