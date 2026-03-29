#!/usr/bin/env python3
"""
Cleans allyears.csv:

1. Finds missing Telegram post numbers per channel -> missing.csv
2. Removes rows where the first URL column (Extracted URL 1) is empty
3. Removes duplicate rows (based on Url + Content)
4. Saves result as cleaned_allyears.csv
"""
import os
import re
import pandas as pd

INPUT_PATH      = "/Users/isakladegaard/airport_reviews_2018-2025/allyears.csv"
OUTPUT_CLEANED  = "/Users/isakladegaard/airport_reviews_2018-2025/cleaned_allyears.csv"
OUTPUT_MISSING  = "/Users/isakladegaard/airport_reviews_2018-2025/missing.csv"

TG_PATTERN = re.compile(r'https://t\.me/([^/]+)/(\d+)', re.IGNORECASE)


# ---------------------------------------------------------------------------
# Step 1: Find missing Telegram posts
# ---------------------------------------------------------------------------

def find_missing_posts(df):
    """
    For each Telegram channel, find all post numbers present,
    then return every integer in [min, max] that is absent.
    Year is inferred from the nearest known post in the same channel.
    """
    # Collect (channel, post_id, year) from every row
    records = []
    for _, row in df.iterrows():
        m = TG_PATTERN.search(str(row.get("Url", "")))
        if m:
            records.append({
                "channel": m.group(1),
                "post_id": int(m.group(2)),
                "year":    row.get("Year", ""),
            })

    if not records:
        print("  No Telegram URLs found.")
        return pd.DataFrame(columns=["Missing URL", "Channel", "Post ID", "Nearest Year"])

    posts_df = pd.DataFrame(records).sort_values(["channel", "post_id"])

    missing_rows = []
    for channel, grp in posts_df.groupby("channel"):
        present  = set(grp["post_id"])
        min_id   = grp["post_id"].min()
        max_id   = grp["post_id"].max()
        all_ids  = set(range(min_id, max_id + 1))
        gaps     = sorted(all_ids - present)

        if not gaps:
            print(f"  {channel}: posts {min_id}–{max_id}, no gaps")
            continue

        # Build a lookup: post_id -> year for known posts
        known = grp.set_index("post_id")["year"].to_dict()

        # For each gap, find the nearest known post and use its year
        known_ids = sorted(present)
        for gap_id in gaps:
            # Binary-search nearest neighbour
            import bisect
            idx = bisect.bisect_left(known_ids, gap_id)
            candidates = []
            if idx < len(known_ids):
                candidates.append(known_ids[idx])
            if idx > 0:
                candidates.append(known_ids[idx - 1])
            nearest = min(candidates, key=lambda x: abs(x - gap_id))
            nearest_year = known.get(nearest, "")

            missing_rows.append({
                "Missing URL":   f"https://t.me/{channel}/{gap_id}",
                "Channel":       channel,
                "Post ID":       gap_id,
                "Nearest Year":  nearest_year,
            })

        print(f"  {channel}: posts {min_id}–{max_id}, {len(gaps)} gap(s)")

    return pd.DataFrame(missing_rows)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if not os.path.exists(INPUT_PATH):
        print(f"Input file not found: {INPUT_PATH}")
        return

    print(f"Reading {INPUT_PATH} ...")
    df = pd.read_csv(INPUT_PATH, encoding="utf-8-sig", low_memory=False)
    print(f"  {len(df)} rows, {len(df.columns)} columns\n")

    # --- Step 1: Missing Telegram posts ---
    print("── Step 1: Finding missing Telegram posts ──────────────")
    missing_df = find_missing_posts(df)
    if not missing_df.empty:
        missing_df.to_csv(OUTPUT_MISSING, index=False, encoding="utf-8-sig")
        print(f"  {len(missing_df)} missing posts -> {OUTPUT_MISSING}")
    else:
        print("  No missing posts found.")

    # --- Step 2: Remove rows with empty first URL column ---
    print("\n── Step 2: Remove rows with no extracted URLs ───────────")
    # Find the first 'Extracted URL' column
    url_cols = [c for c in df.columns if c.startswith("Extracted URL")]
    if not url_cols:
        print("  No 'Extracted URL' columns found, skipping.")
    else:
        first_url_col = url_cols[0]
        before = len(df)
        df = df[df[first_url_col].notna() & (df[first_url_col].astype(str).str.strip() != "")]
        dropped = before - len(df)
        print(f"  Removed {dropped} rows where '{first_url_col}' was empty ({len(df)} remain)")

    # --- Step 3: Remove duplicates ---
    print("\n── Step 3: Remove duplicates (Url + Content) ────────────")
    before = len(df)
    df = df.drop_duplicates(subset=["Url", "Content"], keep="first")
    dropped = before - len(df)
    print(f"  Removed {dropped} duplicate rows ({len(df)} remain)")

    # --- Save ---
    print(f"\nSaving cleaned file -> {OUTPUT_CLEANED}")
    df.to_csv(OUTPUT_CLEANED, index=False, encoding="utf-8-sig")
    print(f"Done. {len(df)} rows in cleaned_allyears.csv")


if __name__ == "__main__":
    main()
