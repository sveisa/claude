#!/usr/bin/env python3
"""
Cleans allyears.csv:

1. Finds missing Telegram post numbers per channel -> missing.csv
2. Resolves bit.ly links to real URLs; stores originals in bitly_orig column
3. Removes rows where the first URL column (Extracted URL 1) is empty
4. Removes duplicate rows (based on Url + Content)
5. Saves result as cleaned_allyears.csv
"""
import os
import re
import bisect
import requests
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
# Step 2: Resolve bit.ly links
# ---------------------------------------------------------------------------

BITLY_PATTERN = re.compile(r'https?://bit\.ly/\S+', re.IGNORECASE)
_resolve_cache = {}

BITLY_TOKEN = os.environ.get("BITLY_TOKEN", "")

def resolve_bitly(url):
    """
    Resolve a bit.ly URL using the Bitly API (works for dead links too).
    Falls back to direct redirect if no API token is set.
    """
    url = url.rstrip(")],.")
    if url in _resolve_cache:
        return _resolve_cache[url]

    resolved = url

    # --- Try Bitly API first (works even for dead links) ---
    if BITLY_TOKEN:
        try:
            # Extract the bit.ly ID from the URL
            bitly_id = url.split("bit.ly/")[-1].split("/")[0]
            resp = requests.get(
                f"https://api-ssl.bitly.com/v4/bitlinks/bit.ly/{bitly_id}",
                headers={"Authorization": f"Bearer {BITLY_TOKEN}"},
                timeout=8,
            )
            if resp.status_code == 200:
                long_url = resp.json().get("long_url", "")
                if long_url:
                    resolved = long_url
        except Exception:
            pass

    # --- Fall back to direct redirect if API didn't work ---
    if resolved == url:
        for method in ("head", "get"):
            try:
                fn = getattr(requests, method)
                resp = fn(url, allow_redirects=True, timeout=8,
                          headers={"User-Agent": "Mozilla/5.0"}, stream=(method == "get"))
                if resp.url != url:
                    resolved = resp.url
                    break
            except Exception:
                continue

    _resolve_cache[url] = resolved
    return resolved


def expand_bitly_in_df(df):
    """
    Scan every Extracted URL column for bit.ly links.
    Replace each with its resolved URL in-place.
    Collect original bit.ly URLs into a new 'bitly_orig' column (comma-separated).
    """
    url_cols = [c for c in df.columns if c.startswith("Extracted URL")]
    if not url_cols:
        print("  No Extracted URL columns found, skipping.")
        return df

    # Gather all unique bit.ly URLs first so we can show total count
    all_bitly = set()
    for col in url_cols:
        for val in df[col].dropna():
            for m in BITLY_PATTERN.findall(str(val)):
                all_bitly.add(m.rstrip(")],." ))

    if not all_bitly:
        print("  No bit.ly links found.")
        return df

    print(f"  Found {len(all_bitly)} unique bit.ly link(s) — resolving...")

    # Resolve with progress counter
    for i, url in enumerate(sorted(all_bitly), 1):
        resolved = resolve_bitly(url)
        status = "unchanged" if resolved == url else resolved
        print(f"  [{i}/{len(all_bitly)}] {url} -> {status}")

    # Apply replacements and collect originals per row
    bitly_orig_col = []
    for _, row in df.iterrows():
        row_originals = []
        for col in url_cols:
            val = str(row[col]) if pd.notna(row[col]) else ""
            matches = BITLY_PATTERN.findall(val)
            for m in matches:
                clean = m.rstrip(")],.")
                resolved = _resolve_cache.get(clean, clean)
                row_originals.append(clean)
                df.at[row.name, col] = val.replace(m, resolved)
        bitly_orig_col.append(", ".join(row_originals) if row_originals else "")

    df.insert(df.columns.get_loc("Extracted URL 1"), "bitly_orig", bitly_orig_col)
    resolved_count = sum(1 for v in bitly_orig_col if v)
    print(f"  Resolved bit.ly links in {resolved_count} rows; originals stored in 'bitly_orig'")
    return df


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

    # --- Step 2: Resolve bit.ly links ---
    print("\n── Step 2: Resolving bit.ly links ───────────────────────")
    df = expand_bitly_in_df(df)

    # --- Step 3: Remove rows with empty first URL column ---
    print("\n── Step 3: Remove rows with no extracted URLs ───────────")
    url_cols = [c for c in df.columns if c.startswith("Extracted URL")]
    if not url_cols:
        print("  No 'Extracted URL' columns found, skipping.")
    else:
        first_url_col = url_cols[0]
        before = len(df)
        df = df[df[first_url_col].notna() & (df[first_url_col].astype(str).str.strip() != "")]
        dropped = before - len(df)
        print(f"  Removed {dropped} rows where '{first_url_col}' was empty ({len(df)} remain)")

    # --- Step 4: Remove duplicates ---
    print("\n── Step 4: Remove duplicates (Url + Content) ────────────")
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
