#!/usr/bin/env python3
"""
VPN URL Checker - checks live status, screenshots, and extracts text.
"""
import os
import requests
import openpyxl
from openpyxl.styles import Alignment
from playwright.sync_api import sync_playwright

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
HTTP_TIMEOUT = 10   # seconds for requests
PAGE_TIMEOUT = 15000  # ms for playwright


def check_url_http(url):
    """Check if URL is live via GET request. Returns (status_code_or_error, final_url)."""
    try:
        resp = requests.get(
            url,
            timeout=HTTP_TIMEOUT,
            allow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            },
        )
        return str(resp.status_code), resp.url
    except requests.exceptions.Timeout:
        return "error: timeout", url
    except requests.exceptions.ConnectionError as e:
        return f"error: connection ({e})", url
    except requests.exceptions.TooManyRedirects:
        return "error: too many redirects", url
    except Exception as e:
        return f"error: {e}", url


def safe_filename(url):
    """Convert URL to a safe filename."""
    import re
    name = re.sub(r"[^\w\-.]", "_", url.replace("https://", "").replace("http://", ""))
    return name[:120] + ".png"


def main():
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

    results = []

    print(f"Processing {len(URLS)} URLs...\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        )

        for i, url in enumerate(URLS, 1):
            print(f"[{i}/{len(URLS)}] {url}")

            # Step 1: HTTP check
            status, final_url = check_url_http(url)
            print(f"  HTTP status: {status}, final URL: {final_url}")

            title = ""
            body_text = ""
            screenshot_filename = ""

            is_live = status.isdigit() and status.startswith(("2", "3", "4", "5"))
            # Treat any numeric HTTP response as "live" (server responded)
            # But only do browser work for 2xx/3xx/4xx (not errors)
            do_browser = status.isdigit()

            if do_browser:
                try:
                    context = browser.new_context(
                        locale="zh-CN",
                        extra_http_headers={"Accept-Language": "zh-CN,zh;q=0.9"},
                        viewport={"width": 1280, "height": 900},
                    )
                    page = context.new_page()

                    # Navigate
                    try:
                        response = page.goto(
                            url,
                            timeout=PAGE_TIMEOUT,
                            wait_until="networkidle",
                        )
                    except Exception:
                        # Fallback: try with domcontentloaded
                        try:
                            response = page.goto(
                                url,
                                timeout=PAGE_TIMEOUT,
                                wait_until="domcontentloaded",
                            )
                            page.wait_for_timeout(3000)
                        except Exception as e:
                            print(f"  Page load error: {e}")
                            context.close()
                            results.append({
                                "url": url,
                                "status": status,
                                "final_url": str(final_url),
                                "title": "",
                                "body_text": f"Page load error: {e}",
                                "screenshot": "",
                            })
                            continue

                    # Get title
                    try:
                        title = page.title()
                    except Exception:
                        title = ""

                    # Get body text
                    try:
                        body_text = page.evaluate("""() => {
                            const body = document.body;
                            if (!body) return '';
                            // Remove script and style elements
                            const clone = body.cloneNode(true);
                            clone.querySelectorAll('script, style, noscript').forEach(el => el.remove());
                            return clone.innerText || clone.textContent || '';
                        }""")
                        # Clean up whitespace
                        lines = [l.strip() for l in body_text.splitlines() if l.strip()]
                        body_text = "\n".join(lines)
                    except Exception as e:
                        body_text = f"Text extraction error: {e}"

                    # Take screenshot
                    fname = safe_filename(url)
                    fpath = os.path.join(SCREENSHOTS_DIR, fname)
                    try:
                        page.screenshot(path=fpath, full_page=True, timeout=10000)
                        screenshot_filename = os.path.join("screenshots", fname)
                        print(f"  Screenshot saved: {screenshot_filename}")
                    except Exception as e:
                        print(f"  Screenshot error: {e}")
                        screenshot_filename = f"error: {e}"

                    context.close()

                except Exception as e:
                    print(f"  Browser error: {e}")
                    title = ""
                    body_text = f"Browser error: {e}"
                    screenshot_filename = ""
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

    # Style header row
    from openpyxl.styles import Font, PatternFill
    header_font = Font(bold=True)
    header_fill = PatternFill("solid", fgColor="D3D3D3")
    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(wrap_text=True, vertical="top")

    for r in results:
        row = [
            r["url"],
            r["status"],
            r["final_url"],
            r["title"],
            r["body_text"],
            r["screenshot"],
        ]
        ws.append(row)
        # Wrap text in all cells, align top
        for cell in ws[ws.max_row]:
            cell.alignment = Alignment(wrap_text=True, vertical="top")

    # Set column widths
    col_widths = [50, 12, 55, 40, 80, 45]
    for col_idx, width in enumerate(col_widths, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = width

    # Set row heights for data rows (allow tall rows for text)
    for row_idx in range(2, ws.max_row + 1):
        ws.row_dimensions[row_idx].height = 60

    wb.save(OUTPUT_FILE)
    print(f"\nDone! Results saved to {OUTPUT_FILE}")
    print(f"Screenshots in {SCREENSHOTS_DIR}/")

    # Summary
    live = sum(1 for r in results if r["status"].isdigit())
    errors = len(results) - live
    print(f"\nSummary: {live} live, {errors} errors out of {len(results)} URLs")


if __name__ == "__main__":
    main()
