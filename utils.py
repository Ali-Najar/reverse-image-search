
import requests
import json
from bs4 import BeautifulSoup
from requests.exceptions import RequestException
import time
from playwright.sync_api import sync_playwright

def fetch_plaintext(url, timeout=10, headless=True):
    """
    1) Try a plain HTTP request
    2) If it errors or returns a CF interstitial, fall back to Playwright
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/115.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        text, soup = _parse_html(resp.text)
        # if Cloudflare interstitial sneaks through, detect it
        if "Just a moment" in text and "Verify you are human" in text:
            raise ValueError("CF interstitial detected")
        return text, soup

    except (RequestException, ValueError):
        # fallback to browser automation
        try:
            return _fetch_with_playwright(url, timeout, headless, headers)
        except Exception:
            # If that also fails, give up
            return "", ""

def extract_links_from_file(json_filepath):
    """
    Reads a JSON file and extracts all 'link' values from the 'data' array.
    
    :param json_filepath: Path to the JSON file.
    :return: List of link strings.
    """
    with open(json_filepath, 'r', encoding='utf-8') as f:
        content = json.load(f)
    
    # Safely get the data array (or empty list if missing)
    items = content.get("data", [])
    
    # Extract 'link' from each item, if present
    links = [item["link"] for item in items if "link" in item]
    
    return links


def _fetch_with_playwright(url, timeout, headless, headers):
    """
    Uses Playwright to drive a real (headless) Chrome, waits for DOMContentLoaded,
    then polls until the CF check goes away or we have enough body text.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            channel="chrome",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--window-size=1920,1080",
            ],
        )
        context = browser.new_context(
            user_agent=headers["User-Agent"],
            viewport={"width": 1920, "height": 1080},
        )
        # hide webdriver flag
        context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        )
        page = context.new_page()

        # load up through DOMContentLoaded
        page.goto(url, timeout=timeout*1000, wait_until="domcontentloaded")

        start = time.time()
        html = ""
        while time.time() - start < timeout:
            html = page.content()
            # break if CF interstitial is gone and we have >200 chars of body text
            if not ("Just a moment" in html and "Verify you are human" in html):
                body = page.inner_text("body")
                if len(body) > 200:
                    break
            time.sleep(0.5)
        else:
            browser.close()
            raise RuntimeError("Timed out waiting for Cloudflare challenge to clear")

        browser.close()
        return _parse_html(html)


def _parse_html(html):
    """Strip scripts/styles and return (text, soup)."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    return text, soup