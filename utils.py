
import requests
import json
from bs4 import BeautifulSoup
from requests.exceptions import RequestException
import time
from playwright.sync_api import sync_playwright
from codes.preprocess import prepare_face
import io
import cv2
from PIL import Image

def fetch_plaintext(url, timeout=10, headless=True):
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
        if "Just a moment" in text and "Verify you are human" in text:
            raise ValueError("CF interstitial detected")
        return text, soup

    except (RequestException, ValueError):
        try:
            return _fetch_with_playwright(url, timeout, headless, headers)
        except Exception:
            return "", ""

def extract_links_from_file(json_filepath):
    with open(json_filepath, 'r', encoding='utf-8') as f:
        content = json.load(f)
    
    items = content.get("data", [])
    
    links = [item["link"] for item in items if "link" in item]
    
    return links


def _fetch_with_playwright(url, timeout, headless, headers):
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
        context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        )
        page = context.new_page()

        page.goto(url, timeout=timeout*1000, wait_until="domcontentloaded")

        start = time.time()
        html = ""
        while time.time() - start < timeout:
            html = page.content()
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
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    return text, soup


def prepare_and_upload(api_key, image_path):
    url = "https://api.imgbb.com/1/upload"
    face = prepare_face(image_path)
    face_rgb = cv2.cvtColor(face, cv2.COLOR_BGR2RGB)
    with io.BytesIO() as buffer:
        pil_face = Image.fromarray(face_rgb)
        pil_face.save(buffer, format='JPEG')
        buffer.seek(0)
        files = {"image": ("face.jpg", buffer, "image/jpeg")}
        data = {"key": api_key}
        response = requests.post(url, files=files, data=data)
        if response.status_code == 200:
            return response.json()['data']['url']
        else:
            raise Exception(f"Upload failed: {response.text}")