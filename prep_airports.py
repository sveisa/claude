#!/usr/bin/env python3
"""
Restructures xlsx files in prepped_airports/:
- Keeps only Date, Url, Content columns (in that order)
- Extracts all http URLs from Content into separate columns
- Overwrites each file in place
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

    # Case-insensitive column lookup
    col_map = {c.lower(): c for c in df.columns}
    missing = [name for name in ("date", "url", "content") if name not in col_map]
    if missing:
        print(f"  SKIP — missing columns: {missing}")
        return

    date_col    = col_map["date"]
    url_col     = col_map["url"]
    content_col = col_map["content"]

    # Extract URLs from Content
    all_urls = df[content_col].apply(extract_urls)
    max_urls = all_urls.apply(len).max()

    # Build output dataframe
    out = pd.DataFrame()
    out["Date"]    = df[date_col]
    out["Url"]     = df[url_col]
    out["Content"] = df[content_col]

    for i in range(max_urls):
        out[f"Extracted URL {i + 1}"] = all_urls.apply(
            lambda urls, idx=i: urls[idx] if idx < len(urls) else ""
        )

    out.to_excel(path, index=False, engine="openpyxl")
    print(f"  OK — {len(out)} rows, {max_urls} extracted URL column(s)")


def main():
    files = sorted(glob.glob(f"{FOLDER}/*.xlsx"))
    if not files:
        print(f"No xlsx files found in {FOLDER}/")
        sys.exit(1)

    print(f"Found {len(files)} file(s) in {FOLDER}/\n")
    for path in files:
        print(f"{path}")
        process_file(path)

    print("\nDone.")


if __name__ == "__main__":
    main()
