

import os
import json
import time
import hashlib
import argparse
import tempfile
import shutil
import random
import string

import requests
import numpy as np
from pathlib import Path
from tqdm import tqdm

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from DIP.codes.preprocess import prepare_face
from DIP.codes.feature_extraction import load_model, get_embedding


def generate_random_profile_name(length=8):
    """Generate a random profile name to avoid conflicts"""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))


def setup_chrome_with_manual_captcha():
    """Ultra-reliable Chrome setup with multiple fallbacks"""
    # First try: Regular incognito mode
    try:
        chrome_options = Options()
        chrome_options.add_argument("--incognito")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1200,800")
        return webdriver.Chrome(options=chrome_options)
    except Exception as e:
        print(f"[-] First attempt failed: {e}")
    
    # Second try: Fresh temp profile with proper cleanup
    try:
        temp_dir = Path(tempfile.mkdtemp(prefix="chrome_temp_"))
        print(f"[*] Using temporary profile: {temp_dir}")
        
        chrome_options = Options()
        chrome_options.add_argument(f"--user-data-dir={temp_dir}")
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--no-default-browser-check")
        chrome_options.add_argument("--window-size=1200,800")
        
        driver = webdriver.Chrome(options=chrome_options)
        
        # Add cleanup handler
        driver.cleanup = lambda: shutil.rmtree(temp_dir, ignore_errors=True)
        return driver
    except Exception as e:
        print(f"[-] Second attempt failed: {e}")
        if 'temp_dir' in locals():
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    # Third try: Portable Chrome with no profile at all
    try:
        chrome_options = Options()
        chrome_options.add_argument("--window-size=1200,800")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--headless=new")  # Last resort
        
        service = ChromeService()
        return webdriver.Chrome(service=service, options=chrome_options)
    except Exception as e:
        print(f"[-] All attempts failed: {e}")
        raise RuntimeError("Could not start Chrome after multiple attempts. " +
                         "Please check your Chrome installation and try again.")


def google_images_upload_and_wait(driver: webdriver.Chrome, query_image_path: Path, max_results: int, verbose: bool = False):
    """
    Improved version with better error handling and user guidance.
    """
    # 1) Navigate to Google Images
    driver.get("https://images.google.com/?hl=en")
    if verbose:
        print("[1] Opened Google Images")

    # 2) Handle cookie consent
    try:
        consent_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Accept all')]"))
        )
        consent_btn.click()
        if verbose:
            print("[2] Accepted cookie banner")
        time.sleep(1)
    except Exception:
        if verbose:
            print("[2] No cookie banner found")

    # 3) Click the camera icon with multiple selector options
    camera_selectors = [
        "div[aria-label='Search by image']",
        "div#qbi",
        "div[jsname='Ohx1pb']",
        "div[role='button'][aria-label='Search by image']"
    ]
    
    for attempt in range(3):
        try:
            for sel in camera_selectors:
                try:
                    camera_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
                    )
                    camera_button.click()
                    if verbose:
                        print(f"[3] Clicked camera icon using selector: {sel}")
                    break
                except Exception:
                    continue
            else:
                raise NoSuchElementException("Could not find camera button with any selector")
            break
        except Exception as e:
            if attempt == 2:
                raise RuntimeError(f"Failed to click camera icon after 3 attempts: {e}")
            print(f"[!] Camera click attempt {attempt+1} failed, retrying...")
            time.sleep(2)

    time.sleep(1)  # Wait for upload dialog

    # 4) Upload the image
    try:
        file_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
        )
        file_input.send_keys(str(query_image_path.absolute()))
        if verbose:
            print(f"[4] Uploaded image: {query_image_path}")
    except Exception as e:
        raise RuntimeError(f"Failed to upload image: {e}")

    # 5) Manual CAPTCHA solve prompt
    print("\n" + "="*60)
    print("🚨 IMPORTANT: Check the browser window now!")
    print("1. If you see a CAPTCHA, solve it completely")
    print("2. Wait until you see image results appearing")
    print("3. When done, return here and press ENTER to continue")
    print("="*60 + "\n")
    input()

    # 6) Wait for results with extended timeout
    try:
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-ri], a.wXeWr.islib.NFQFxe, div[jscontroller]"))
        )
        if verbose:
            print("[5] Results loaded")
    except TimeoutException:
        print("[!] Warning: Timed out waiting for results")
        print("[!] Possible reasons:")
        print("    - CAPTCHA wasn't solved completely")
        print("    - Google is blocking automated requests")
        print("    - The page structure changed")
        print("[!] Trying to proceed anyway...")

    # 7) Get results with multiple selector options
    result_selectors = [
        "a.wXeWr.islib.NFQFxe",
        "div[data-ri]",
        "div[jscontroller]",
        "div[jsname]"
    ]
    
    anchors = []
    for sel in result_selectors:
        try:
            anchors = driver.find_elements(By.CSS_SELECTOR, sel)
            if anchors:
                if verbose:
                    print(f"[6] Found {len(anchors)} results using selector: {sel}")
                break
        except Exception:
            continue

    return anchors[:max_results]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--query_image", required=True, help="Path to the aligned face crop")
    parser.add_argument("--max_results", type=int, default=30, help="Max results to process")
    parser.add_argument("--threshold", type=float, default=0.4, help="Similarity threshold")
    parser.add_argument("--device", type=int, default=0, help="CUDA device index")
    parser.add_argument("--download_dir", default="data/selenium_thumbs", help="Thumbnail download dir")
    parser.add_argument("--out_json", default="data/selenium_candidates.json", help="Output JSON path")
    parser.add_argument("--profile_dir", default=None, help="Chrome profile directory to reuse")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    # Load model and compute query embedding
    if args.verbose:
        print("[*] Loading model...")
    model = load_model(device=args.device)
    query_face = prepare_face(args.query_image, output_dir="data/preprocessed")
    if query_face is None:
        raise RuntimeError(f"Failed to preprocess query image '{args.query_image}'")
    query_emb = get_embedding(model, query_face)
    if args.verbose:
        print("[*] Computed query embedding")

    # Setup Chrome and perform search
    driver, profile_dir = None, None
    try:
        driver, profile_dir = setup_chrome_with_manual_captcha()
        if args.verbose:
            print("[*] Starting reverse image search...")
        anchors = google_images_upload_and_wait(driver, Path(args.query_image), args.max_results, args.verbose)
    except Exception as e:
        print(f"[!] Critical error during search: {e}")
        if driver:
            driver.save_screenshot("error_screenshot.png")
            print("[!] Saved screenshot to error_screenshot.png")
        raise
    finally:
        if driver:
            driver.quit()

    # Process results
    pairs = []
    for i, a in enumerate(anchors):
        try:
            m_attr = a.get_attribute("m") or a.get_attribute("data-m") or a.get_attribute("data-json")
            if not m_attr:
                continue
                
            try:
                meta = json.loads(m_attr)
                thumb_url = meta.get("tu") or meta.get("ou")
                page_url = meta.get("ru")
                if thumb_url and page_url:
                    pairs.append((thumb_url, page_url))
                    if args.verbose:
                        print(f"    • #{i+1}: thumb='{thumb_url[:60]}...', page='{page_url}'")
            except json.JSONDecodeError:
                continue
        except Exception as e:
            if args.verbose:
                print(f"    • Skipping result #{i+1}: {str(e)}")
            continue

    # Download and compare thumbnails
    candidates = []
    download_dir = Path(args.download_dir)
    for thumb_url, page_url in tqdm(pairs, desc="Processing results"):
        try:
            local_thumb = download_thumbnail(thumb_url, download_dir, args.verbose)
            if not local_thumb:
                continue

            face_crop = prepare_face(str(local_thumb), output_dir="data/preprocessed")
            if not face_crop:
                if args.verbose:
                    print(f"    [!] No face in {local_thumb.name}")
                continue

            emb = get_embedding(model, face_crop)
            sim = float(np.dot(query_emb, emb) / (np.linalg.norm(query_emb) * np.linalg.norm(emb)))
            
            if sim >= args.threshold:
                candidates.append({
                    "url": page_url,
                    "local_path": str(local_thumb),
                    "similarity": sim
                })
                if args.verbose:
                    print(f"    [+] Match (sim={sim:.3f}): {page_url}")
        except Exception as e:
            if args.verbose:
                print(f"    [!] Error processing {thumb_url}: {str(e)}")
            continue

    # Save results
    candidates.sort(key=lambda x: x["similarity"], reverse=True)
    os.makedirs(Path(args.out_json).parent, exist_ok=True)
    with open(args.out_json, "w") as f:
        json.dump(candidates, f, indent=2)

    if args.verbose:
        print(f"\n[*] Saved {len(candidates)} matches to {args.out_json}")

    # Clean up profile if temporary
    if args.profile_dir is None and profile_dir and profile_dir.exists():
        try:
            shutil.rmtree(profile_dir)
            if args.verbose:
                print(f"[*] Cleaned up temporary profile: {profile_dir}")
        except Exception as e:
            print(f"[!] Failed to clean up profile: {e}")


if __name__ == "__main__":
    main()