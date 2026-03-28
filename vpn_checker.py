#!/usr/bin/env python3
"""
VPN URL Checker - liveness, screenshots, text, WHOIS, DNS, SSL, panel detection, Wayback.
"""
import os
import re
import ssl
import socket
import shutil
import datetime
import subprocess
import warnings
from urllib.parse import urlparse

import requests
import whois
import dns.resolver
import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from playwright.sync_api import sync_playwright

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

# Panel software fingerprints: checked against raw HTML source
PANEL_SIGNATURES = {
    "V2Board":     ["/api/v1/passport/", "v2board", "V2Board"],
    "XBoard":      ["xboard", "XBoard", "/api/v1/user/getSubscribe"],
    "SSPanel-UIM": ["SSPanel", "sspanel", "mu/user"],
    "WHMCS":       ["whmcs.com", "WHMCS"],
    "Trojan Panel":["trojan-panel", "trojanpanel"],
    "Sing-Box":    ["sing-box", "singbox"],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_root_url(url):
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}"


def get_hostname(url):
    return urlparse(url).netloc


def check_url_http(url):
    """GET root URL. Retries with verify=False on SSL errors. Returns (status_str, final_url)."""
    for verify in (True, False):
        try:
            resp = requests.get(url, timeout=HTTP_TIMEOUT, allow_redirects=True,
                                verify=verify, headers=HEADERS)
            note = " (SSL unverified)" if not verify else ""
            return str(resp.status_code) + note, resp.url
        except requests.exceptions.SSLError:
            if verify:
                continue
            return "error: SSL failure", url
        except requests.exceptions.Timeout:
            return "error: timeout", url
        except requests.exceptions.ConnectionError as e:
            s = str(e)
            if "NameResolution" in s or "nodename" in s or "Name or service" in s:
                return "error: DNS failed", url
            return "error: connection failed", url
        except requests.exceptions.TooManyRedirects:
            return "error: too many redirects", url
        except Exception as e:
            return f"error: {type(e).__name__}", url
    return "error: SSL failure", url


def get_whois(hostname):
    """Returns dict with registrar, created, expires."""
    result = {"registrar": "", "created": "", "expires": ""}
    try:
        w = whois.whois(hostname)
        result["registrar"] = str(w.registrar or "").strip() or ""

        def fmt_date(d):
            if isinstance(d, list):
                d = d[0]
            if isinstance(d, datetime.datetime):
                return d.strftime("%Y-%m-%d")
            return str(d)[:10] if d else ""

        result["created"] = fmt_date(w.creation_date)
        result["expires"] = fmt_date(w.expiration_date)
    except Exception:
        pass
    return result


def get_dns_and_ip(hostname):
    """Resolve A records; geolocate first IP via ip-api.com. Returns dict."""
    result = {"ip": "", "hosting": "", "ip_country": ""}
    try:
        answers = dns.resolver.resolve(hostname, "A", lifetime=8)
        ips = [str(r) for r in answers]
        result["ip"] = ", ".join(ips)
        if ips:
            # Geolocate first IP
            try:
                geo = requests.get(
                    f"http://ip-api.com/json/{ips[0]}?fields=country,org,as",
                    timeout=6,
                ).json()
                result["hosting"] = geo.get("org") or geo.get("as") or ""
                result["ip_country"] = geo.get("country") or ""
            except Exception:
                pass
    except Exception:
        pass
    return result


def get_ssl_info(hostname):
    """Connect on port 443 and extract cert details. Returns dict."""
    result = {"ssl_issuer": "", "ssl_expiry": "", "ssl_sans": ""}
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with socket.create_connection((hostname, 443), timeout=8) as raw:
            with ctx.wrap_socket(raw, server_hostname=hostname) as s:
                cert = s.getpeercert()
        if not cert:
            return result

        # Issuer
        issuer = dict(x[0] for x in cert.get("issuer", []))
        result["ssl_issuer"] = issuer.get("organizationName") or issuer.get("commonName") or ""

        # Expiry
        not_after = cert.get("notAfter", "")
        if not_after:
            try:
                dt = datetime.datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
                result["ssl_expiry"] = dt.strftime("%Y-%m-%d")
            except Exception:
                result["ssl_expiry"] = not_after

        # Subject Alternative Names
        sans = []
        for san_type, san_val in cert.get("subjectAltName", []):
            if san_type == "DNS" and san_val != hostname:
                sans.append(san_val)
        result["ssl_sans"] = ", ".join(sans[:10])  # cap at 10

    except Exception:
        pass
    return result


def get_wayback_count(hostname):
    """Query Wayback CDX API for total snapshot count."""
    try:
        resp = requests.get(
            "https://web.archive.org/cdx/search/cdx",
            params={
                "url": f"{hostname}/*",
                "output": "json",
                "fl": "timestamp",
                "limit": 10000,
                "matchType": "host",
            },
            timeout=12,
        )
        data = resp.json()
        # First row is header ["timestamp"]
        count = max(0, len(data) - 1)
        return f"{count}+" if count == 9999 else str(count)
    except Exception:
        return ""


def detect_panel(html):
    """Detect panel software from raw HTML source."""
    detected = []
    for name, sigs in PANEL_SIGNATURES.items():
        if any(sig in html for sig in sigs):
            detected.append(name)
    return ", ".join(detected) if detected else ""


# ---------------------------------------------------------------------------
# Playwright helpers
# ---------------------------------------------------------------------------

def is_cloudflare_block(page):
    try:
        text = page.evaluate("() => document.body?.innerText || ''").lower()
        title = (page.title() or "").lower()
        html = page.content()
        return any([
            "attention required" in title,
            "just a moment" in title,
            "you have been blocked" in text,
            "checking your browser" in text,
            "cf-browser-verification" in html,
            "challenge-platform" in html,
        ])
    except Exception:
        return False


def wait_for_spa_content(page, timeout_ms=8000):
    try:
        page.wait_for_function(
            """() => {
                const clone = document.body?.cloneNode(true);
                if (!clone) return false;
                clone.querySelectorAll('script,style,noscript,link').forEach(e => e.remove());
                return (clone.innerText || '').trim().length > 20;
            }""",
            timeout=timeout_ms,
        )
    except Exception:
        page.wait_for_timeout(3000)


def extract_text(page):
    try:
        raw = page.evaluate("""() => {
            const clone = document.body?.cloneNode(true);
            if (!clone) return '';
            clone.querySelectorAll('script,style,noscript,link,svg').forEach(e => e.remove());
            return clone.innerText || clone.textContent || '';
        }""")
        lines = [l.strip() for l in raw.splitlines() if l.strip()]
        return "\n".join(lines)
    except Exception as e:
        return f"Text extraction error: {e}"


def safe_filename(url):
    name = re.sub(r"[^\w\-.]", "_", url.replace("https://", "").replace("http://", ""))
    return name[:120] + ".png"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

    # Deduplicate to root URLs, preserving order
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
                "--no-sandbox", "--disable-setuid-sandbox",
                "--disable-dev-shm-usage", "--disable-gpu",
                "--disable-blink-features=AutomationControlled",
            ],
        )

        for i, url in enumerate(root_urls, 1):
            hostname = get_hostname(url)
            print(f"[{i}/{len(root_urls)}] {url}")

            # --- HTTP check ---
            status, final_url = check_url_http(url)
            print(f"  HTTP:    {status}")

            # --- WHOIS ---
            print(f"  WHOIS...")
            whois_data = get_whois(hostname)

            # --- DNS + IP geo ---
            print(f"  DNS/IP...")
            dns_data = get_dns_and_ip(hostname)

            # --- SSL ---
            print(f"  SSL...")
            ssl_data = get_ssl_info(hostname)

            # --- Wayback ---
            print(f"  Wayback...")
            wayback_count = get_wayback_count(hostname)

            title = ""
            body_text = ""
            screenshot_filename = ""
            panel = ""

            do_browser = status.split()[0].isdigit()

            if do_browser:
                try:
                    context = browser.new_context(
                        locale="zh-CN",
                        extra_http_headers={"Accept-Language": "zh-CN,zh;q=0.9"},
                        viewport={"width": 1280, "height": 900},
                        ignore_https_errors=True,
                    )
                    page = context.new_page()

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
                    else:
                        # Cloudflare: wait up to ~12s for challenge to pass
                        if is_cloudflare_block(page):
                            print(f"  Cloudflare detected, waiting...")
                            for _ in range(4):
                                page.wait_for_timeout(3000)
                                if not is_cloudflare_block(page):
                                    print(f"  Challenge passed")
                                    break
                            else:
                                status = status.split()[0] + " (Cloudflare blocked)"

                        wait_for_spa_content(page)

                        try:
                            final_url = page.url
                        except Exception:
                            pass

                        try:
                            title = page.title() or ""
                        except Exception:
                            pass

                        body_text = extract_text(page)

                        # Panel detection from raw HTML
                        try:
                            panel = detect_panel(page.content())
                        except Exception:
                            pass

                        # Screenshot
                        fname = safe_filename(url)
                        fpath = os.path.join(SCREENSHOTS_DIR, fname)
                        try:
                            page.screenshot(path=fpath, full_page=True, timeout=10000)
                            screenshot_filename = os.path.join("screenshots", fname)
                            print(f"  Screenshot: {screenshot_filename}")
                        except Exception as e:
                            screenshot_filename = f"error: {e}"

                        context.close()

                except Exception as e:
                    print(f"  Browser error: {e}")
                    body_text = f"Browser error: {e}"
            else:
                print(f"  Skipping browser (not live)")

            results.append({
                "id":          i,
                "url":         url,
                "status":      status,
                "final_url":   str(final_url),
                "title":       title,
                "body_text":   body_text,
                "screenshot":  screenshot_filename,
                "panel":       panel,
                "registrar":   whois_data["registrar"],
                "created":     whois_data["created"],
                "expires":     whois_data["expires"],
                "ip":          dns_data["ip"],
                "hosting":     dns_data["hosting"],
                "ip_country":  dns_data["ip_country"],
                "ssl_issuer":  ssl_data["ssl_issuer"],
                "ssl_expiry":  ssl_data["ssl_expiry"],
                "ssl_sans":    ssl_data["ssl_sans"],
                "wayback":     wayback_count,
            })
            print()

        browser.close()

    # --- Write Excel ---
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "VPN URL Check"

    columns = [
        ("#",                     5),
        ("URL",                  45),
        ("Status",               25),
        ("Final URL",            50),
        ("Page Title",           35),
        ("Extracted Text",       80),
        ("Screenshot",           45),
        ("Panel Software",       20),
        ("Registrar",            30),
        ("Domain Created",       15),
        ("Domain Expires",       15),
        ("IP Address",           18),
        ("Hosting / ASN",        35),
        ("IP Country",           15),
        ("SSL Issuer",           30),
        ("SSL Expiry",           14),
        ("SSL SANs",             45),
        ("Wayback Copies",       15),
    ]
    headers = [c[0] for c in columns]
    widths   = [c[1] for c in columns]

    ws.append(headers)
    hfont = Font(bold=True)
    hfill = PatternFill("solid", fgColor="D3D3D3")
    for cell in ws[1]:
        cell.font = hfont
        cell.fill = hfill
        cell.alignment = Alignment(wrap_text=True, vertical="top")

    for r in results:
        ws.append([
            r["id"],
            r["url"], r["status"], r["final_url"], r["title"], r["body_text"],
            r["screenshot"], r["panel"], r["registrar"], r["created"], r["expires"],
            r["ip"], r["hosting"], r["ip_country"],
            r["ssl_issuer"], r["ssl_expiry"], r["ssl_sans"],
            r["wayback"],
        ])
        for cell in ws[ws.max_row]:
            cell.alignment = Alignment(wrap_text=True, vertical="top")

    for col_idx, width in enumerate(widths, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = width

    for row_idx in range(2, ws.max_row + 1):
        ws.row_dimensions[row_idx].height = 60

    wb.save(OUTPUT_FILE)
    print(f"Done! Results saved to {OUTPUT_FILE}")

    live = sum(1 for r in results if r["status"].split()[0].isdigit())
    cf   = sum(1 for r in results if "Cloudflare" in r["status"])
    err  = len(results) - live
    print(f"Summary: {live} live ({cf} Cloudflare blocked), {err} errors, {len(results)} total")

    # --- Mirror prompt ---
    mirror_candidates = [r for r in results if r["status"].split()[0].isdigit()]
    if mirror_candidates:
        print("\n--- Sites available to mirror ---")
        for r in mirror_candidates:
            label = r["title"] or r["url"]
            print(f"  {r['id']:>2}.  {r['url']}  ({label})")
        print("\nEnter IDs to mirror (e.g. 2, 4, 7), or 0 to skip: ", end="", flush=True)
        try:
            raw = input().strip()
        except (EOFError, KeyboardInterrupt):
            raw = "0"

        if raw and raw != "0":
            chosen_ids = {int(x) for x in re.split(r"[,\s]+", raw) if x.strip().isdigit()}
            to_mirror  = [r for r in results if r["id"] in chosen_ids]
            if not to_mirror:
                print("No matching IDs found, skipping.")
            elif not shutil.which("wget"):
                print("wget not found — install it with: brew install wget")
            else:
                mirrors_dir = "./mirrors"
                os.makedirs(mirrors_dir, exist_ok=True)
                for r in to_mirror:
                    host = get_hostname(r["url"])
                    dest = os.path.join(mirrors_dir, host)
                    print(f"\nMirroring {r['url']} -> {dest}/")
                    cmd = [
                        "wget",
                        "--mirror",
                        "--convert-links",
                        "--adjust-extension",
                        "--page-requisites",
                        "--no-parent",
                        "--wait=1",
                        "--random-wait",
                        "--tries=3",
                        "--timeout=15",
                        f"--user-agent={HEADERS['User-Agent']}",
                        "--header=Accept-Language: zh-CN,zh;q=0.9",
                        "--no-check-certificate",
                        "-P", dest,
                        r["url"],
                    ]
                    try:
                        subprocess.run(cmd, check=False)
                        print(f"  Mirror saved to {dest}/")
                    except Exception as e:
                        print(f"  wget failed: {e}")
        else:
            print("Skipping mirror.")


if __name__ == "__main__":
    main()
