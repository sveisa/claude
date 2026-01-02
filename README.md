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

1. Go to your GitHub repository Settings
2. Navigate to "Pages" in the left sidebar
3. Under "Build and deployment":
   - Source: Select "GitHub Actions"
4. The app will automatically deploy when you push changes
5. Visit your GitHub Pages URL to use the converter

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
