#!/usr/bin/env python3
"""
Restructures xlsx files in prepped_airports/:
- Keeps Date, Views, Shares, Url, Content columns (in that order)
- Extracts all http URLs from Content into separate columns
- Saves as UTF-8 CSV alongside the originals (xlsx untouched)
"""
import re
import glob
import sys
import pandas as pd

FOLDER = "/Users/isakladegaard/prepped_airports"
URL_PATTERN = re.compile(r'https?://[^\s\u3000\u300a\u300b\uff08\uff09\u3001\u3002"\'<>」【】]+')


def extract_urls(text):
    if not isinstance(text, str):
        return []
    return URL_PATTERN.findall(text)


def process_file(path):
    df = pd.read_excel(path, engine="openpyxl")

    col_map = {c.lower(): c for c in df.columns}
    required = ("date", "url", "content")
    missing = [name for name in required if name not in col_map]
    if missing:
        print(f"  SKIP — missing columns: {missing}")
        return

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

    # utf-8-sig adds a BOM so Excel opens Chinese text correctly
    csv_path = path.replace(".xlsx", ".csv")
    out.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"  OK — {len(out)} rows, {max_urls} extracted URL col(s) -> {csv_path}")


def main():
    files = sorted(glob.glob(f"{FOLDER}/*.xlsx"))
    if not files:
        print(f"No xlsx files found in {FOLDER}/")
        sys.exit(1)

    print(f"Found {len(files)} file(s) in {FOLDER}/\n")
    for path in files:
        print(f"{path}")
        process_file(path)

    # Merge all CSVs into one
    csv_files = sorted(glob.glob(f"{FOLDER}/*.csv"))
    if csv_files:
        merged = pd.concat(
            [pd.read_csv(f, encoding="utf-8-sig") for f in csv_files],
            ignore_index=True
        )
        merged_path = f"{FOLDER}/merged.csv"
        merged.to_csv(merged_path, index=False, encoding="utf-8-sig")
        print(f"\nMerged {len(csv_files)} files -> {merged_path} ({len(merged)} rows total)")

    print("\nDone.")


if __name__ == "__main__":
    main()
