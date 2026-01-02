#!/usr/bin/env python3
"""
Gab News Article Scraper
Downloads HTML articles from Gab News using cloudscraper to bypass Cloudflare protection
"""

import cloudscraper
import os
import time
import shutil
import random
from tqdm import tqdm

# ==========================================
# URL LIST
# ==========================================
urls = [
    "https://news.gab.com/2021/11/remember-remember-the-3rd-of-november/",
    "https://news.gab.com/2021/10/important-download-covid-vaccine-religious-exemption-documents-here/",
    "https://news.gab.com/2021/10/an-eschatology-of-christ-first/",
    "https://news.gab.com/2021/10/an-eschatology-of-victory/",
    "https://news.gab.com/2021/10/the-fifth-great-awakening/",
    "https://news.gab.com/2021/10/gabs-statement-on-president-trumps-social-network/",
    "https://news.gab.com/2021/10/their-silly-shame-words-arent-working-anymore/",
    "https://news.gab.com/2021/10/gabs-response-to-the-adl/",
    "https://news.gab.com/2021/10/kingdom-of-god-economics/",
    "https://news.gab.com/2021/10/in-the-world-but-not-of-the-world/",
    "https://news.gab.com/2021/09/building-technology-to-power-a-parallel-christian-society/",
    "https://news.gab.com/2021/09/balkanization-is-the-only-way-forward-for-the-divided-states-of-america/",
    "https://news.gab.com/2019/09/university-of-texas-announces-new-free-speech-policy/",
    "https://news.gab.com/2019/09/facebook-and-instagram-are-removing-like-counts-to-hide-the-popularity-of-wrongthink-ideas/",
    "https://news.gab.com/2019/09/youtube-removes-100000-videos-bans-17000-channels-for-hate-speech/",
    "https://news.gab.com/2019/09/academics-attempt-to-smear-gab-and-alt-media-with-bogus-study/",
    "https://news.gab.com/2019/08/facebook-app-for-kids-introduced-children-to-adult-strangers/",
    "https://news.gab.com/2019/08/facebook-cites-baby-killer-abortionists-to-fact-check-pro-life-content/",
    "https://news.gab.com/2019/08/google-to-pay-up-to-200-million-to-ftc/",
    "https://news.gab.com/2019/08/sorry-but-aoc-is-right-no-one-is-entitled-to-a-platform-under-her-tweets-or-president-trumps-for-that-matter/",
    "https://news.gab.com/2019/08/the-battle-over-censorship-zones-is-heading-to-the%e2%80%88supreme-court-in-the-dystopian-uk/",
    "https://news.gab.com/2019/08/twitter-for-bans-ads-for-books-over-use-of-the-word-vagina/",
    "https://news.gab.com/2019/08/pinterest-thought-police-correct-the-record-on-searches-related-to-vaccines/",
    "https://news.gab.com/2019/08/youtube-crackdown-on-borderline-content-is-exported-to-the-uk/",
    "https://news.gab.com/2019/10/40-state-attorneys-general-plan-to-take-part-in-facebook-antitrust-probe/",
    "https://news.gab.com/2019/10/bitcoin-is-free-speech-money-gab-will-introduce-it-to-millions-of-people/",
    "https://news.gab.com/2019/10/google-targeted-homeless-people-with-dark-skin-to-improve-facial-recognition/",
    "https://news.gab.com/2019/10/christian-actress-fired-after-citing-bible-verse-on-social-media/",
    "https://news.gab.com/2019/10/iphone-user-sues-apple-claims-an-app-made-him-gay/",
    "https://news.gab.com/2019/10/twitter-censored-trumps-photograph-video-gab-wouldnt-have/",
    "https://news.gab.com/2019/10/study-finds-that-facebook-induces-feelings-of-depression/",
    "https://news.gab.com/2019/10/ai-determines-that-minorities-use-hate-speech-at-substantially-higher-rates-than-whites-on-twitter/",
    "https://news.gab.com/2019/10/facebook-could-be-forced-to-remove-hate-speech-around-the-world-by-the-eu/",
    "https://news.gab.com/2019/10/kamala-harris-calls-for-president-trump-to-be-suspended-from-twitter/",
    "https://news.gab.com/2019/10/zucked-read-mark-zuckerbergs-leaked-internal-meeting-transcripts/",
    "https://news.gab.com/2019/09/google-reportedly-under-antitrust-investigation-again/",
    "https://news.gab.com/2023/02/one-minute-with-marlin/",
    "https://news.gab.com/2023/02/a-christian-perspective-on-ai/",
    "https://news.gab.com/2023/02/parallel-christian-society-in-1000-bc/",
    "https://news.gab.com/2023/01/the-roundtable-amish-insights-on-pride/",
    "https://news.gab.com/2023/01/the-conservative-case-for-the-great-replacement/",
    "https://news.gab.com/2023/01/christians-must-enter-the-ai-arms-race/",
    "https://news.gab.com/2023/01/nations-are-built-upon-loyalty/",
    "https://news.gab.com/2023/01/how-four-adoptions-led-to-a-magazine/",
    "https://news.gab.com/2023/01/gab-under-attack-the-ddos-on-january-23rd/",
    "https://news.gab.com/2023/01/lessons-from-livestock-part-three/",
    "https://news.gab.com/2023/01/conservative-inc-and-the-deal-with-the-daily-wire-devil/",
    "https://news.gab.com/2023/01/the-atf-anarcho-tyranny-and-parallel-society/",
]

# ==========================================
# CONFIGURATION
# ==========================================
DOWNLOAD_FOLDER = "gab_articles_html"
ZIP_FILENAME = "gab_research_data"

def main():
    # Create a scraper instance designed to bypass Cloudflare/403 blocks
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )

    # 1. Create directory
    if os.path.exists(DOWNLOAD_FOLDER):
        shutil.rmtree(DOWNLOAD_FOLDER)
    os.makedirs(DOWNLOAD_FOLDER)

    print(f"Starting download of {len(urls)} articles using Cloudscraper...")

    success_count = 0
    error_count = 0

    # 2. Iterate and download
    for url in tqdm(urls):
        try:
            # Create a filename from the URL slug
            slug = url.strip('/').split('/')[-1]
            if not slug:
                slug = f"article_{urls.index(url)}"
            filename = f"{slug}.html"

            # Use the scraper instead of requests
            response = scraper.get(url, timeout=30)

            if response.status_code == 200:
                file_path = os.path.join(DOWNLOAD_FOLDER, filename)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(response.text)
                success_count += 1
            else:
                print(f"\nFailed ({response.status_code}): {url}")
                error_count += 1

            # IMPORTANT: Random sleep to behave like a human
            time.sleep(random.uniform(2, 5))

        except Exception as e:
            print(f"\nError downloading {url}: {e}")
            error_count += 1

    print(f"\nDownload complete.")
    print(f"Successful: {success_count}")
    print(f"Errors: {error_count}")

    # 3. Zip the files
    if success_count > 0:
        print("Zipping files...")
        shutil.make_archive(ZIP_FILENAME, 'zip', DOWNLOAD_FOLDER)
        print(f"Created {ZIP_FILENAME}.zip")
    else:
        print("No files were downloaded successfully. IP might be blocked.")

if __name__ == "__main__":
    main()
