#!/usr/bin/env python3
"""
VPN URL Checker - checks live status, screenshots, and extracts text.
"""
import os
import re
import time
import warnings
from urllib.parse import urlparse

import requests
import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from playwright.sync_api import sync_playwright

# Suppress InsecureRequestWarning for SSL fallback
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

URLS = [
    "https://xn--yusw35d.xyz/#/register?code=YutFnITJ",
    "https://xn--z4q48lcvpsq0c.com/#/register?code=BvRTqsvl",
    "https://xs.mashiroshina.top/#/register?code=22ZSIaBi",
    "https://xship.top/auth#signup",
    "https://xueli.lol/#/register?code=gEPQOSxr",
    "https://xunlian.site/#/register?code=FySDL3O0",
    "https://xuwuge.xyz/#/register?code=efgnkt9V",
    "https://xview.top/#/register?code=P1aulLZ5",
    "https://xyyjc.top/#/register?code=xeiLbK6N",
    "https://yam688.com/#/register?code=o4yuhGF1",
    "https://yefengjc.xyz/#/register?code=BlxfUIua",
    "https://yfh4rrze3snwnnwj.xn--4gq62f52gdss.vip/#/register?code=jiNyiQPH",
    "https://yifangaff.win/auth/register?code=naau",
    "https://yifenjichang.online/#/register?code=Q1I30hjD",
    "https://yiyuanlx.cc/#/register?code=ERZB34hE",
]

SCREENSHOTS_DIR = "./screenshots"
OUTPUT_FILE = "./output.xlsx"
HTTP_TIMEOUT = 10
PAGE_TIMEOUT = 15000

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
}


def get_root_url(url):
    """Extract root URL (scheme + host) from any URL."""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def check_url_http(url):
    """Check if URL is live via GET. Retries without SSL verification on cert errors."""
    for verify in (True, False):
        try:
            resp = requests.get(
                url,
                timeout=HTTP_TIMEOUT,
                allow_redirects=True,
                verify=verify,
                headers=HEADERS,
            )
            status = str(resp.status_code)
            note = ""
            if not verify:
                note = " (SSL unverified)"
            return status + note, resp.url
        except requests.exceptions.SSLError:
            if verify:
                continue  # retry without verification
            return "error: SSL failure", url
        except requests.exceptions.Timeout:
            return "error: timeout", url
        except requests.exceptions.ConnectionError as e:
            reason = str(e)
            if "NameResolution" in reason or "nodename" in reason:
                return "error: DNS resolution failed", url
            return f"error: connection failed", url
        except requests.exceptions.TooManyRedirects:
            return "error: too many redirects", url
        except Exception as e:
            return f"error: {type(e).__name__}", url
    return "error: SSL failure", url


def is_cloudflare_block(page):
    """Detect Cloudflare challenge/block pages."""
    try:
        text = page.evaluate("() => document.body?.innerText || ''")
        title = page.title() or ""
        cf_signals = [
            "Attention Required" in title,
            "Just a moment" in title,
            "Cloudflare" in title,
            "you have been blocked" in text.lower(),
            "checking your browser" in text.lower(),
            "cf-browser-verification" in page.content(),
            "challenge-platform" in page.content(),
        ]
        return any(cf_signals)
    except Exception:
        return False


def wait_for_spa_content(page, timeout_ms=8000):
    """Wait for SPA content to render (non-empty body text)."""
    try:
        page.wait_for_function(
            """() => {
                const body = document.body;
                if (!body) return false;
                const clone = body.cloneNode(true);
                clone.querySelectorAll('script, style, noscript, link').forEach(el => el.remove());
                const text = (clone.innerText || '').trim();
                return text.length > 20;
            }""",
            timeout=timeout_ms,
        )
    except Exception:
        # Fallback: just wait a bit for whatever renders
        page.wait_for_timeout(3000)


def extract_text(page):
    """Extract visible body text, cleaning whitespace."""
    try:
        body_text = page.evaluate("""() => {
            const body = document.body;
            if (!body) return '';
            const clone = body.cloneNode(true);
            clone.querySelectorAll('script, style, noscript, link, svg').forEach(el => el.remove());
            return clone.innerText || clone.textContent || '';
        }""")
        lines = [l.strip() for l in body_text.splitlines() if l.strip()]
        return "\n".join(lines)
    except Exception as e:
        return f"Text extraction error: {e}"


def safe_filename(url):
    """Convert URL to a safe filename."""
    name = re.sub(r"[^\w\-.]", "_", url.replace("https://", "").replace("http://", ""))
    return name[:120] + ".png"


def main():
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

    # Derive root URLs, deduplicating while preserving order
    seen = set()
    root_urls = []
    for url in URLS:
        root = get_root_url(url)
        if root not in seen:
            seen.add(root)
            root_urls.append(root)

    results = []

    print(f"Processing {len(root_urls)} root URLs...\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-blink-features=AutomationControlled",
            ],
        )

        for i, url in enumerate(root_urls, 1):
            print(f"[{i}/{len(root_urls)}] {url}")

            # Step 1: HTTP liveness check
            status, final_url = check_url_http(url)
            print(f"  HTTP: {status} -> {final_url}")

            title = ""
            body_text = ""
            screenshot_filename = ""

            do_browser = status.split()[0].isdigit()  # numeric status (may have " (SSL unverified)" suffix)

            if do_browser:
                try:
                    context = browser.new_context(
                        locale="zh-CN",
                        extra_http_headers={"Accept-Language": "zh-CN,zh;q=0.9"},
                        viewport={"width": 1280, "height": 900},
                        ignore_https_errors=True,
                    )
                    page = context.new_page()

                    # Navigate with networkidle, fallback to domcontentloaded
                    loaded = False
                    for wait_strat in ("networkidle", "domcontentloaded"):
                        try:
                            page.goto(url, timeout=PAGE_TIMEOUT, wait_until=wait_strat)
                            loaded = True
                            break
                        except Exception:
                            continue

                    if not loaded:
                        print(f"  Page load failed")
                        context.close()
                        results.append({
                            "url": url, "status": status,
                            "final_url": str(final_url),
                            "title": "", "body_text": "Page load failed",
                            "screenshot": "",
                        })
                        continue

                    # Detect Cloudflare — wait up to 10s for challenge to resolve
                    if is_cloudflare_block(page):
                        print(f"  Cloudflare detected, waiting for challenge...")
                        for _ in range(4):
                            page.wait_for_timeout(3000)
                            if not is_cloudflare_block(page):
                                print(f"  Cloudflare challenge passed")
                                break
                        else:
                            print(f"  Cloudflare block persists (recording as-is)")
                            status = status.split()[0] + " (Cloudflare blocked)"

                    # Wait for SPA content to render
                    wait_for_spa_content(page)

                    # Get final URL after any JS redirects
                    try:
                        final_url = page.url
                    except Exception:
                        pass

                    # Get title
                    try:
                        title = page.title() or ""
                    except Exception:
                        title = ""

                    # Get body text
                    body_text = extract_text(page)

                    # Take screenshot
                    fname = safe_filename(url)
                    fpath = os.path.join(SCREENSHOTS_DIR, fname)
                    try:
                        page.screenshot(path=fpath, full_page=True, timeout=10000)
                        screenshot_filename = os.path.join("screenshots", fname)
                        print(f"  Screenshot: {screenshot_filename}")
                    except Exception as e:
                        print(f"  Screenshot error: {e}")
                        screenshot_filename = f"error: {e}"

                    context.close()

                except Exception as e:
                    print(f"  Browser error: {e}")
                    body_text = f"Browser error: {e}"
            else:
                print(f"  Skipping browser (not live)")

            results.append({
                "url": url,
                "status": status,
                "final_url": str(final_url),
                "title": title,
                "body_text": body_text,
                "screenshot": screenshot_filename,
            })
            print()

        browser.close()

    # Write Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "VPN URL Check"

    headers = ["URL", "Status", "Final URL", "Page Title", "Extracted Text", "Screenshot Filename"]
    ws.append(headers)

    header_font = Font(bold=True)
    header_fill = PatternFill("solid", fgColor="D3D3D3")
    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(wrap_text=True, vertical="top")

    for r in results:
        ws.append([
            r["url"], r["status"], r["final_url"],
            r["title"], r["body_text"], r["screenshot"],
        ])
        for cell in ws[ws.max_row]:
            cell.alignment = Alignment(wrap_text=True, vertical="top")

    col_widths = [45, 25, 50, 40, 80, 45]
    for col_idx, width in enumerate(col_widths, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = width

    for row_idx in range(2, ws.max_row + 1):
        ws.row_dimensions[row_idx].height = 60

    wb.save(OUTPUT_FILE)
    print(f"\nDone! Results saved to {OUTPUT_FILE}")
    print(f"Screenshots in {SCREENSHOTS_DIR}/")

    live = sum(1 for r in results if r["status"].split()[0].isdigit())
    cf = sum(1 for r in results if "Cloudflare" in r["status"])
    errors = len(results) - live
    print(f"\nSummary: {live} live ({cf} Cloudflare blocked), {errors} errors, {len(results)} total")


if __name__ == "__main__":
    main()
