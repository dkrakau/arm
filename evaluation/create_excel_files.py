import io
import pandas as pd
from pathlib import Path


def export_excels(
    csv_folder="csv", output_folder="excel", vba="excel_modules/vbaProject.bin"
):
    csv_dir = Path(csv_folder)
    out = Path(output_folder)
    out.mkdir(parents=True, exist_ok=True)

    files_by_field = {}
    for csv_file in sorted(csv_dir.glob("*.csv")):
        field, ptype = csv_file.stem.split(".", 1)
        files_by_field.setdefault(field, []).append((ptype, csv_file))

    for field, files in files_by_field.items():
        puffer = io.BytesIO()
        with pd.ExcelWriter(puffer, engine="xlsxwriter") as writer:
            writer.book.add_vba_project(vba)
            writer.book.set_vba_name("DieseArbeitsmappe")
            for ptype, csv_file in files:
                df = pd.read_csv(csv_file, dtype=str)  # to keep values as "False"
                df["cite"] = pd.to_numeric(df["cite"])  # to keep cite as number
                df.to_excel(writer, sheet_name=ptype[:31], index=False)
        (out / f"{field}.xlsm").write_bytes(puffer.getvalue())


def main():
    export_excels()


if __name__ == "__main__":
    main()

# py create_excel_files.py
