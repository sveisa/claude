#!/usr/bin/env python3
"""
Processes airport review xlsx files organised by year.

Input:  /Users/isakladegaard/airport_reviews_2018-2025.zip
        └── 2018/1.xlsx ... 10.xlsx
        └── 2019/1.xlsx ... 10.xlsx
        ...

For each year folder:
  - Cleans every xlsx (keeps Date, Views, Shares, Url, Content)
  - Extracts http URLs from Content into separate columns
  - Saves individual CSVs next to each xlsx
  - Saves a merged_{year}.csv for that year

Final output:
  - allyears.csv combining all years (with a Year column added)

All output goes into the unzipped folder next to the zip file.
"""
import os
import re
import glob
import sys
import zipfile
import pandas as pd

ZIP_PATH   = "/Users/isakladegaard/airport_reviews_2018-2025.zip"
URL_PATTERN = re.compile(r'https?://[^\s\u3000\u300a\u300b\uff08\uff09\u3001\u3002"\'<>」【】]+')


def extract_urls(text):
    if not isinstance(text, str):
        return []
    return URL_PATTERN.findall(text)


def process_file(path):
    """Clean one xlsx. Returns a DataFrame, or None on failure."""
    df = pd.read_excel(path, engine="openpyxl")

    col_map = {c.lower(): c for c in df.columns}
    missing = [name for name in ("date", "url", "content") if name not in col_map]
    if missing:
        print(f"    SKIP — missing columns: {missing}")
        return None

    date_col    = col_map["date"]
    views_col   = col_map.get("views")
    shares_col  = col_map.get("shares")
    url_col     = col_map["url"]
    content_col = col_map["content"]

    all_urls = df[content_col].apply(extract_urls)
    max_urls = all_urls.apply(len).max()

    out = pd.DataFrame()
    out["Date"]    = df[date_col]
    if views_col:
        out["Views"]  = df[views_col]
    if shares_col:
        out["Shares"] = df[shares_col]
    out["Url"]     = df[url_col]
    out["Content"] = df[content_col]

    for i in range(max_urls):
        out[f"Extracted URL {i + 1}"] = all_urls.apply(
            lambda urls, idx=i: urls[idx] if idx < len(urls) else ""
        )

    csv_path = path.replace(".xlsx", ".csv")
    out.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"    OK — {len(out)} rows, {max_urls} URL col(s) -> {os.path.basename(csv_path)}")
    return out


def process_year(year_dir, year):
    """Process all xlsx files in a year folder. Returns merged DataFrame for that year."""
    xlsx_files = sorted(
        f for f in glob.glob(os.path.join(year_dir, "*.xlsx"))
        if not os.path.basename(f).startswith("~$")
    )
    if not xlsx_files:
        print(f"  No xlsx files found in {year_dir}, skipping.")
        return None

    print(f"  {len(xlsx_files)} file(s) found")
    frames = []
    for path in xlsx_files:
        print(f"  {os.path.basename(path)}")
        df = process_file(path)
        if df is not None:
            frames.append(df)

    if not frames:
        return None

    # Merge all files for this year
    year_merged = pd.concat(frames, ignore_index=True)
    year_csv = os.path.join(year_dir, f"merged_{year}.csv")
    year_merged.to_csv(year_csv, index=False, encoding="utf-8-sig")
    print(f"  -> merged_{year}.csv ({len(year_merged)} rows total)\n")
    return year_merged


def main():
    if not os.path.exists(ZIP_PATH):
        print(f"Zip file not found: {ZIP_PATH}")
        sys.exit(1)

    # Unzip next to the zip file
    base_dir = os.path.dirname(ZIP_PATH)
    zip_name  = os.path.splitext(os.path.basename(ZIP_PATH))[0]
    extract_dir = os.path.join(base_dir, zip_name)

    print(f"Unzipping to {extract_dir} ...")
    with zipfile.ZipFile(ZIP_PATH, "r") as z:
        z.extractall(extract_dir)

    # Find year folders (numeric folder names)
    year_dirs = sorted(
        d for d in glob.glob(os.path.join(extract_dir, "*"))
        if os.path.isdir(d) and os.path.basename(d).isdigit()
    )
    if not year_dirs:
        print(f"No year folders found inside zip.")
        sys.exit(1)

    print(f"Found {len(year_dirs)} year folder(s): {[os.path.basename(d) for d in year_dirs]}\n")

    all_frames = []
    for year_dir in year_dirs:
        year = os.path.basename(year_dir)
        print(f"── {year} ──────────────────────────")
        df = process_year(year_dir, year)
        if df is not None:
            df.insert(0, "Year", year)
            all_frames.append(df)

    # Final combined file
    if all_frames:
        allyears = pd.concat(all_frames, ignore_index=True)
        allyears_path = os.path.join(extract_dir, "allyears.csv")
        allyears.to_csv(allyears_path, index=False, encoding="utf-8-sig")
        print(f"All years combined -> {allyears_path}")
        print(f"Total rows: {len(allyears)}")

    print("\nDone.")


if __name__ == "__main__":
    main()
