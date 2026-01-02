#!/usr/bin/env python3
"""
Gab News Article Scraper using Playwright (browser automation)
This version uses a real browser to bypass bot detection
"""

import os
import time
import shutil
import random
from tqdm import tqdm

# Note: This requires: pip install playwright && playwright install chromium

urls = [
    "https://news.gab.com/2021/11/remember-remember-the-3rd-of-november/",
    "https://news.gab.com/2021/10/important-download-covid-vaccine-religious-exemption-documents-here/",
    # ... (add all your URLs here)
]

DOWNLOAD_FOLDER = "gab_articles_html"
ZIP_FILENAME = "gab_research_data"

def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright not installed. Run: pip install playwright && playwright install chromium")
        return

    # Create directory
    if os.path.exists(DOWNLOAD_FOLDER):
        shutil.rmtree(DOWNLOAD_FOLDER)
    os.makedirs(DOWNLOAD_FOLDER)

    print(f"Starting download of {len(urls)} articles using Playwright (real browser)...")

    success_count = 0
    error_count = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for url in tqdm(urls):
            try:
                # Create filename from URL slug
                slug = url.strip('/').split('/')[-1]
                if not slug:
                    slug = f"article_{urls.index(url)}"
                filename = f"{slug}.html"

                # Navigate to the page
                page.goto(url, wait_until='networkidle', timeout=30000)

                # Get the HTML content
                html_content = page.content()

                # Save to file
                file_path = os.path.join(DOWNLOAD_FOLDER, filename)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(html_content)

                success_count += 1

                # Random sleep to behave like a human
                time.sleep(random.uniform(2, 5))

            except Exception as e:
                print(f"\nError downloading {url}: {e}")
                error_count += 1

        browser.close()

    print(f"\nDownload complete.")
    print(f"Successful: {success_count}")
    print(f"Errors: {error_count}")

    # Zip the files
    if success_count > 0:
        print("Zipping files...")
        shutil.make_archive(ZIP_FILENAME, 'zip', DOWNLOAD_FOLDER)
        print(f"Created {ZIP_FILENAME}.zip")
    else:
        print("No files were downloaded successfully.")

if __name__ == "__main__":
    main()
