# VPN URL Checker

Checks a list of VPN service URLs and outputs `output.xlsx` with the following columns:

| Column | Description |
|---|---|
| # | Unique ID (also prefixed on screenshot filenames) |
| URL | Root domain checked |
| Status | HTTP status code, or error reason |
| Page Title | Browser page title |
| Extracted Text | Full visible body text |
| Extracted Text (EN) | Auto-translated to English (blank if already English) |
| Screenshot | Relative path to the PNG (saved in `screenshots/`) |
| Registrar | Domain registrar from WHOIS |
| Domain Created | Registration date |
| IP Address | Resolved A record(s) |
| Hosting / ASN | Hosting provider / ASN |
| IP Country | Country the site is hosted in |
| Wayback Copies | Number of snapshots in the Wayback Machine |

Screenshots are saved as `screenshots/003_xship.top.png` etc. After the run you'll be prompted to optionally mirror any live sites with `wget`.

---

## Setup (Mac — do this once)

**1. Install prerequisites**

```bash
brew install wget
```

If you don't have Homebrew: https://brew.sh

**2. Clone the repo and switch to the right branch**

```bash
git clone https://github.com/sveisa/claude
cd claude
git checkout claude/vpn-url-checker-Qqc38
```

**3. Create a Python virtual environment and install dependencies**

```bash
python3 -m venv venv
source venv/bin/activate
pip install playwright openpyxl requests python-whois dnspython deep-translator
python -m playwright install chromium
```

---

## Running it

**Every time you open a new terminal, activate the environment first:**

```bash
cd claude
source venv/bin/activate
```

**Add your URLs** — open `vpn_checker.py` in any text editor and replace the URLs in the `URLS = [...]` list at the top. One URL per line, in quotes, comma-separated. Root URLs and full URLs with paths/fragments both work — the script strips everything down to the root domain automatically.

**Run:**

```bash
python vpn_checker.py
```

Results are saved to `output.xlsx` and screenshots to `screenshots/`. At the end you'll be asked if you want to mirror any live sites with wget — enter their IDs (e.g. `2, 4, 7`) or `0` to skip.

---

## Pulling updates

If the script has been updated:

```bash
git pull
```

---

# EPUB to TXT Converter

A simple, browser-based tool to convert EPUB files to plain text format. No server required - everything runs in your browser!

## Features

- **100% Client-Side**: All processing happens in your browser - no files are uploaded to any server
- **Drag & Drop**: Easy drag-and-drop interface or click to browse
- **Preserves Reading Order**: Extracts text in the correct chapter order
- **Clean Output**: Removes HTML tags and formatting, leaving only text content
- **Instant Download**: Download your converted TXT file immediately

## How to Use

### Online (GitHub Pages)

Visit the live app at: `https://sveisa.github.io/claude/`

**First-time setup:**
1. Go to your GitHub repository Settings
2. Navigate to "Pages" in the left sidebar
3. Under "Build and deployment":
   - Source: Select "GitHub Actions"
4. The app will automatically deploy when you push changes

### Local Usage

1. Clone or download this repository
2. Open `index.html` in your web browser
3. Upload an EPUB file by:
   - Clicking the upload area and selecting a file, or
   - Dragging and dropping an EPUB file onto the upload area
4. Wait for the conversion to complete
5. Click the "Download TXT File" button to save your converted file

## How It Works

1. **Upload**: The app reads your EPUB file using the HTML5 File API
2. **Unzip**: EPUB files are essentially ZIP archives, which are extracted using JSZip
3. **Parse**: The app reads the EPUB's structure (OPF file) to determine reading order
4. **Extract**: Text is extracted from each chapter's HTML/XHTML content
5. **Download**: The combined text is offered as a downloadable TXT file

## Technical Details

- **No Dependencies**: Single HTML file with embedded CSS and JavaScript
- **External Libraries**: Uses JSZip (CDN) for handling EPUB/ZIP files
- **Browser Compatibility**: Works in all modern browsers (Chrome, Firefox, Safari, Edge)
- **Privacy**: No data leaves your computer - 100% offline processing

## Browser Requirements

- Modern browser with JavaScript enabled
- Support for HTML5 File API
- Internet connection (only for loading JSZip library from CDN)

## Limitations

- Very large EPUB files (>100MB) may take longer to process
- Some complex EPUB formatting may not convert perfectly
- DRM-protected EPUB files are not supported

## License

MIT License - feel free to use and modify as needed!
