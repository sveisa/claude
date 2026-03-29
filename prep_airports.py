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
URL_PATTERN    = re.compile(r'https?://[^\s\u3000\u300a\u300b\uff08\uff09\u3001\u3002"\'<>」【】]+')
TRAILING_JUNK  = re.compile(r'[\])\[,;。，、！？!?]+$')


def extract_urls(text):
    if not isinstance(text, str):
        return []
    raw_matches = URL_PATTERN.findall(text)
    seen = []
    for match in raw_matches:
        # Split markdown-style links: "https://a.com/](https://b.com/)" -> two URLs
        parts = re.split(r'\]\(', match)
        for part in parts:
            clean = TRAILING_JUNK.sub('', part)
            if clean.startswith("http") and clean not in seen:
                seen.append(clean)
    return seen


def process_file(path):
    """Clean one xlsx. Returns (DataFrame, raw_row_count), or (None, raw_row_count) on failure."""
    df = pd.read_excel(path, engine="openpyxl")
    raw_rows = len(df)

    col_map = {c.lower(): c for c in df.columns}
    missing = [name for name in ("date", "url", "content") if name not in col_map]
    if missing:
        print(f"    SKIP — missing columns: {missing}")
        return None, raw_rows

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
    return out, raw_rows


def process_year(year_dir, year):
    """Process all xlsx files in a year folder. Returns (merged DataFrame, audit dict)."""
    xlsx_files = sorted(
        f for f in glob.glob(os.path.join(year_dir, "*.xlsx"))
        if not os.path.basename(f).startswith("~$")
    )
    if not xlsx_files:
        print(f"  No xlsx files found in {year_dir}, skipping.")
        return None, {}

    print(f"  {len(xlsx_files)} file(s) found")
    frames = []
    audit = {"files": [], "skipped": [], "raw_total": 0, "processed_total": 0}

    for path in xlsx_files:
        fname = os.path.basename(path)
        print(f"  {fname}")
        df, raw_rows = process_file(path)
        audit["raw_total"] += raw_rows
        if df is not None:
            frames.append(df)
            audit["files"].append({"file": fname, "raw": raw_rows, "processed": len(df)})
            audit["processed_total"] += len(df)
        else:
            audit["skipped"].append(fname)

    if not frames:
        return None, audit

    year_merged = pd.concat(frames, ignore_index=True)
    year_csv = os.path.join(year_dir, f"merged_{year}.csv")
    year_merged.to_csv(year_csv, index=False, encoding="utf-8-sig")
    print(f"  -> merged_{year}.csv ({len(year_merged)} rows total)\n")
    return year_merged, audit


def run_validation(allyears, all_audits, year_dirs):
    """Print a validation report. Returns True if all checks pass."""
    print("\n" + "═" * 55)
    print("  VALIDATION REPORT")
    print("═" * 55)

    passed = True

    # 1. Row count: sum of all raw xlsx rows == allyears rows
    total_raw       = sum(a["raw_total"] for a in all_audits.values())
    total_processed = sum(a["processed_total"] for a in all_audits.values())
    allyears_rows   = len(allyears)

    print(f"\n{'CHECK 1: Row counts':}")
    print(f"  Raw xlsx rows (all files):   {total_raw:>7}")
    print(f"  Processed rows (all files):  {total_processed:>7}")
    print(f"  Rows in allyears.csv:        {allyears_rows:>7}")
    if total_processed == allyears_rows:
        print("  ✓ Processed rows match allyears.csv")
    else:
        diff = allyears_rows - total_processed
        print(f"  ✗ MISMATCH — difference: {diff:+d}")
        passed = False
    if total_raw != total_processed:
        lost = total_raw - total_processed
        print(f"  ⚠ {lost} rows dropped (skipped files or missing columns)")

    # 2. Year coverage
    print(f"\nCHECK 2: Year coverage")
    expected_years = {str(y) for y in range(2018, 2026)}
    found_years    = {os.path.basename(d) for d in year_dirs}
    missing_years  = expected_years - found_years
    if missing_years:
        print(f"  ✗ Missing year folders: {sorted(missing_years)}")
        passed = False
    else:
        print(f"  ✓ All years 2018–2025 present")

    # 3. Per-year row counts
    print(f"\nCHECK 3: Per-year breakdown")
    print(f"  {'Year':<6} {'Files':>5} {'Skipped':>8} {'Raw rows':>10} {'In output':>10}")
    print(f"  {'-'*6} {'-'*5} {'-'*8} {'-'*10} {'-'*10}")
    for year, audit in sorted(all_audits.items()):
        skipped = len(audit["skipped"])
        flag = " ⚠" if skipped else ""
        print(f"  {year:<6} {len(audit['files']):>5} {skipped:>8} {audit['raw_total']:>10} {audit['processed_total']:>10}{flag}")

    # 4. Skipped files
    all_skipped = [(y, f) for y, a in all_audits.items() for f in a["skipped"]]
    print(f"\nCHECK 4: Skipped files")
    if all_skipped:
        for year, fname in all_skipped:
            print(f"  ✗ {year}/{fname} — missing required columns")
        passed = False
    else:
        print(f"  ✓ No files skipped")

    # 5. Duplicate rows (exact match on Date + Url)
    print(f"\nCHECK 5: Duplicate rows (same Date + Url)")
    dupes = allyears.duplicated(subset=["Date", "Url"], keep=False).sum()
    if dupes:
        print(f"  ⚠ {dupes} rows share a Date+Url combination (may be intentional reposts)")
    else:
        print(f"  ✓ No duplicate Date+Url pairs")

    # 6. Empty content
    print(f"\nCHECK 6: Empty Content cells")
    empty_content = allyears["Content"].isna().sum() + (allyears["Content"] == "").sum()
    if empty_content:
        print(f"  ⚠ {empty_content} rows have empty Content")
    else:
        print(f"  ✓ No empty Content cells")

    # 7. Date values outside expected year
    print(f"\nCHECK 7: Dates outside expected year")
    allyears_copy = allyears.copy()
    allyears_copy["_year"] = pd.to_datetime(allyears_copy["Date"], errors="coerce").dt.year.astype("Int64")
    allyears_copy["Year"]  = allyears_copy["Year"].astype(int)
    mismatch = allyears_copy[allyears_copy["_year"] != allyears_copy["Year"]]
    if len(mismatch):
        print(f"  ⚠ {len(mismatch)} rows have a Date that doesn't match their year folder")
        print(f"    (first 5: {mismatch[['Year','Date']].head().to_dict('records')})")
    else:
        print(f"  ✓ All dates fall within their year folder")

    print("\n" + "═" * 55)
    print(f"  {'ALL CHECKS PASSED ✓' if passed else 'ISSUES FOUND — see above ✗'}")
    print("═" * 55 + "\n")
    return passed


def main():
    if not os.path.exists(ZIP_PATH):
        print(f"Zip file not found: {ZIP_PATH}")
        sys.exit(1)

    base_dir    = os.path.dirname(ZIP_PATH)
    zip_name    = os.path.splitext(os.path.basename(ZIP_PATH))[0]
    extract_dir = os.path.join(base_dir, zip_name)

    print(f"Unzipping to {extract_dir} ...")
    with zipfile.ZipFile(ZIP_PATH, "r") as z:
        z.extractall(extract_dir)

    year_dirs = sorted(
        d for d in glob.glob(os.path.join(extract_dir, "*"))
        if os.path.isdir(d) and os.path.basename(d).isdigit()
    )
    if not year_dirs:
        print(f"No year folders found inside zip.")
        sys.exit(1)

    print(f"Found {len(year_dirs)} year folder(s): {[os.path.basename(d) for d in year_dirs]}\n")

    all_frames = []
    all_audits = {}
    for year_dir in year_dirs:
        year = os.path.basename(year_dir)
        print(f"── {year} ──────────────────────────")
        df, audit = process_year(year_dir, year)
        all_audits[year] = audit
        if df is not None:
            df.insert(0, "Year", year)
            all_frames.append(df)

    if all_frames:
        allyears = pd.concat(all_frames, ignore_index=True)
        allyears_path = os.path.join(extract_dir, "allyears.csv")
        allyears.to_csv(allyears_path, index=False, encoding="utf-8-sig")
        print(f"All years combined -> {allyears_path}")
        print(f"Total rows: {len(allyears)}")

        run_validation(allyears, all_audits, year_dirs)

    print("Done.")


if __name__ == "__main__":
    main()
