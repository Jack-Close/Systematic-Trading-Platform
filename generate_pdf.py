"""
generate_pdf.py
===============
Converts Trading_Platform_Documentation_v2.html to a PDF file.

Usage:
    python generate_pdf.py

Requirements:
    Primary method:  Google Chrome (checked in common Windows install locations)
    Fallback method: weasyprint  (pip install weasyprint)

Output:
    Trading_Platform_Documentation_v2.pdf  (same directory as this script)

Notes:
    - Chrome headless is the preferred method because it faithfully reproduces
      all CSS, including @media print rules, colour backgrounds, and fonts.
    - weasyprint is used as a fallback if Chrome is not found.
    - If neither is available, the script prints install instructions.
"""

import os
import subprocess
import sys

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
HTML_FILE = os.path.join(BASE_DIR, "Trading_Platform_Documentation_v2.html")
PDF_FILE  = os.path.join(BASE_DIR, "Trading_Platform_Documentation_v2.pdf")

# ---------------------------------------------------------------------------
# Chrome executable locations to check (Windows)
# ---------------------------------------------------------------------------

CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Google\Chrome\Application\chrome.exe"),
    # Edge as a fallback Chromium-based browser
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def find_chrome() -> str | None:
    """Return the path to the first Chrome (or Edge) executable found, or None."""
    for path in CHROME_PATHS:
        if path and os.path.isfile(path):
            return path
    return None


# ---------------------------------------------------------------------------
# Method 1: Chrome headless
# ---------------------------------------------------------------------------

def convert_with_chrome(chrome_path: str) -> bool:
    """
    Use Chrome headless to print the HTML file to PDF.

    Chrome command:
        chrome --headless=new --disable-gpu
               --print-to-pdf="<output>" --no-pdf-header-footer "<input>"
    """
    print(f"[INFO] Using Chrome at: {chrome_path}")
    print(f"[INFO] Input  : {HTML_FILE}")
    print(f"[INFO] Output : {PDF_FILE}")

    cmd = [
        chrome_path,
        "--headless=new",
        "--disable-gpu",
        "--run-all-compositor-stages-before-draw",
        "--disable-extensions",
        "--no-sandbox",
        f"--print-to-pdf={PDF_FILE}",
        "--no-pdf-header-footer",
        # Use the file:/// URI so Chrome can resolve local resources
        f"file:///{HTML_FILE.replace(os.sep, '/')}",
    ]

    print("[INFO] Running Chrome headless…")
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode == 0 and os.path.isfile(PDF_FILE):
            size_kb = os.path.getsize(PDF_FILE) / 1024
            print(f"[SUCCESS] PDF written: {PDF_FILE}  ({size_kb:.1f} KB)")
            return True
        else:
            print(f"[ERROR] Chrome exited with code {result.returncode}")
            if result.stderr:
                print("[STDERR]", result.stderr[:500])
            return False

    except subprocess.TimeoutExpired:
        print("[ERROR] Chrome timed out after 120 seconds.")
        return False
    except FileNotFoundError:
        print(f"[ERROR] Could not launch Chrome at: {chrome_path}")
        return False
    except Exception as exc:
        print(f"[ERROR] Unexpected error running Chrome: {exc}")
        return False


# ---------------------------------------------------------------------------
# Method 2: weasyprint fallback
# ---------------------------------------------------------------------------

def convert_with_weasyprint() -> bool:
    """
    Use weasyprint to convert the HTML file to PDF.
    Install with:  pip install weasyprint
    """
    print("[INFO] Attempting weasyprint fallback…")
    try:
        import weasyprint  # type: ignore
    except ImportError:
        print("[ERROR] weasyprint is not installed.")
        print("        Install it with:  pip install weasyprint")
        return False

    print(f"[INFO] Input  : {HTML_FILE}")
    print(f"[INFO] Output : {PDF_FILE}")

    try:
        html_uri = f"file:///{HTML_FILE.replace(os.sep, '/')}"
        doc = weasyprint.HTML(filename=HTML_FILE, base_url=BASE_DIR)
        doc.write_pdf(PDF_FILE)

        if os.path.isfile(PDF_FILE):
            size_kb = os.path.getsize(PDF_FILE) / 1024
            print(f"[SUCCESS] PDF written: {PDF_FILE}  ({size_kb:.1f} KB)")
            return True
        else:
            print("[ERROR] weasyprint ran but the output file was not created.")
            return False

    except Exception as exc:
        print(f"[ERROR] weasyprint failed: {exc}")
        return False


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 60)
    print("  Trading Research Platform — PDF Generator")
    print("=" * 60)

    # Verify the HTML source exists
    if not os.path.isfile(HTML_FILE):
        print(f"[ERROR] HTML source not found: {HTML_FILE}")
        print("        Please make sure Trading_Platform_Documentation_v2.html")
        print("        is in the same directory as this script.")
        sys.exit(1)

    # Try Chrome first
    chrome_path = find_chrome()
    if chrome_path:
        success = convert_with_chrome(chrome_path)
        if success:
            print()
            print("Done. Open the PDF with any PDF viewer.")
            return
        else:
            print("[WARN] Chrome conversion failed — trying weasyprint fallback.")
    else:
        print("[WARN] Google Chrome not found in any standard location.")
        print("       Checked paths:")
        for p in CHROME_PATHS:
            print(f"         {p}")
        print()

    # Try weasyprint fallback
    success = convert_with_weasyprint()
    if success:
        print()
        print("Done. Open the PDF with any PDF viewer.")
        return

    # Both methods failed
    print()
    print("[FAILED] Could not generate the PDF.")
    print()
    print("To fix this, choose one of the following options:")
    print()
    print("  Option 1 — Install Google Chrome:")
    print("    Download from https://www.google.com/chrome/")
    print("    Then re-run this script.")
    print()
    print("  Option 2 — Install weasyprint:")
    print("    pip install weasyprint")
    print("    Then re-run this script.")
    print()
    print("  Option 3 — Manual print-to-PDF:")
    print(f"    Open {HTML_FILE} in Chrome or Edge,")
    print("    press Ctrl+P, select 'Save as PDF', uncheck headers/footers,")
    print("    and save.")
    sys.exit(1)


if __name__ == "__main__":
    main()
