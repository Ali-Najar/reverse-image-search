import re
import json
import requests
from bs4 import BeautifulSoup
from transformers import pipeline
from dateutil.parser import parse as parse_date

# 1) Initialize a BERT‐NER pipeline once (caching the model in memory)
NER_MODEL = pipeline(
    "ner",
    model="dbmdz/bert-large-cased-finetuned-conll03-english",
    aggregation_strategy="simple"  # merge contiguous tokens into single span
)

def fetch_plaintext(url, timeout=10):
    """Download URL and return visible text (all <body> text)."""
    resp = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    # Remove scripts/styles, then get visible text
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return soup.get_text(separator=" ", strip=True), soup

def ner_extract(text):
    """
    Run the NER pipeline on `text`, return two sets:
      • names: list of PER spans
      • norps: list of NORP spans (nationalities/groups)
    """
    results = NER_MODEL(text[:50_000])  # limit length to first 50k chars
    names = []
    norps = []
    for ent in results:
        label = ent["entity_group"]
        span = ent["word"]
        if label == "PER":
            names.append(span)
        elif label == "NORP":
            norps.append(span)
    # Deduplicate while preserving order
    def unique(seq):
        seen = set()
        out = []
        for item in seq:
            if item not in seen:
                seen.add(item)
                out.append(item)
        return out

    return unique(names), unique(norps)

def extract_birthday(text):
    """
    Same regex as before, but applied to the entire page text.
    """
    patterns = [
        r"Born\s+([A-Za-z]{3,9}\s+\d{1,2},\s*\d{4})",
        r"Born[:\s]+(\d{4}-\d{2}-\d{2})",
        r"Date of Birth[:\s]+([A-Za-z]{3,9}\s+\d{1,2},\s*\d{4})",
        r"Date of Birth[:\s]+(\d{4}-\d{2}-\d{2})"
    ]
    for pat in patterns:
        match = re.search(pat, text)
        if match:
            try:
                dt = parse_date(match.group(1))
                return dt.strftime("%Y-%m-%d")
            except:
                continue
    return None

def extract_job_keywords(text):
    """
    Heuristic: look for common occupation keywords near the top of the page.
    Return the first match of a known occupation.
    """
    occupations = [
        "Film Director", "Director", "Actor", "Actress", "Writer",
        "Producer", "Screenwriter", "Cinematographer", "Composer"
    ]
    # Check each keyword—case insensitive
    for occ in occupations:
        if re.search(rf"\b{re.escape(occ)}\b", text, re.IGNORECASE):
            return occ
    return None

def extract_official_links(soup, base_domain):
    """
    Unchanged: collect <a href> whose domain matches IMDb/Wikipedia/Instagram
    or equals base_domain.
    """
    allowed = {"imdb.com", "wikipedia.org", "instagram.com"}
    out = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith("#") or href.startswith("javascript:"):
            continue
        parsed = requests.utils.urlparse(href)
        domain = parsed.netloc.lower()
        if base_domain in domain:
            out.add(href)
        else:
            for d in allowed:
                if domain.endswith(d):
                    out.add(href)
                    break
    return list(out)

def extract_known_for(soup, base_domain):
    """
    (Same as before: IMDb's “Known for” or Wikipedia “Known for” infobox.)
    """
    known_for = []
    if "imdb.com" in base_domain:
        for div in soup.select("div.knownfor-title-role"):
            a = div.find("a", href=True)
            if a and a.get_text(strip=True):
                known_for.append(a.get_text(strip=True))
    if "wikipedia.org" in base_domain:
        for th in soup.find_all("th"):
            if th.get_text(strip=True).lower() == "known for":
                td = th.find_next_sibling("td")
                if td:
                    for a in td.find_all("a", href=True):
                        title = a.get_text(strip=True)
                        if title:
                            known_for.append(title)
    return list(dict.fromkeys(known_for))


def phase4_with_bert(phase3_data, verbose=False):
    """
    Replace the earlier phase4_text_mining with BERT‐NER based extraction.
    Returns a list of objects in the Phase 4 schema.
    """
    results4 = []
    for entry in phase3_data:
        link = entry.get("link")
        domain = requests.utils.urlparse(link).netloc.lower()
        if verbose:
            print(f"\n[*] Crawling {link}")
        try:
            page_text, soup = fetch_plaintext(link)
        except Exception as e:
            if verbose:
                print(f"    [!] Failed to fetch page: {e}")
            # Fallback to nulls
            results4.append({
                **entry,
                "extracted": {
                    "name": None,
                    "job": None,
                    "nationality": None,
                    "birthday": None,
                    "additional_info": {
                        "official_links": [],
                        "known_for": []
                    }
                }
            })
            continue

        # 1) Run BERT- NER on the visible text
        names, norps = ner_extract(page_text)
        name = names[0] if names else None
        nationality = norps[0] if norps else None

        # 2) Extract birthday by regex
        birthday = extract_birthday(page_text)

        # 3) Extract job keyword
        job = extract_job_keywords(page_text)

        # 4) Official links + known_for using soup
        official_links = extract_official_links(soup, domain)
        known_for      = extract_known_for(soup, domain)

        if verbose:
            print(f"    • BERT names      = {names}")
            print(f"    • BERT nationalities = {norps}")
            print(f"    • birthday        = {birthday}")
            print(f"    • job (kw)        = {job}")
            print(f"    • official_links  = {official_links}")
            print(f"    • known_for       = {known_for}")

        results4.append({
            **entry,
            "extracted": {
                "name": name,
                "job": job,
                "nationality": nationality,
                "birthday": birthday,
                "additional_info": {
                    "official_links": official_links,
                    "known_for": known_for
                }
            }
        })
    return results4


def phase5_assemble(phase4_data, query_image_url):
    """
    Same as before: build the final Phase 5 JSON.
    """
    assembled = []
    for idx, ent in enumerate(phase4_data, start=1):
        ext = ent["extracted"]
        ai = ext["additional_info"]
        assembled.append({
            "rank":          idx,
            "link":          ent.get("link"),
            "name":          ext.get("name"),
            "job":           ext.get("job"),
            "nationality":   ext.get("nationality"),
            "birthday":      ext.get("birthday"),
            "official_links": ai.get("official_links", []),
            "known_for":     ai.get("known_for", [])
        })

    return {
        "query_image": query_image_url,
        "timestamp":   datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "results":     assembled
    }


if __name__ == "__main__":
    import argparse
    from datetime import datetime

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phase3_json", default="/home/xulei/shayan/DIP/rapidapi.json",
        help="Path to Phase 3 JSON (with top‐level 'data' array)."
    )
    parser.add_argument(
        "--out_phase4", default="/home/xulei/shayan/DIP/data/phase4.json",
        help="Where to write Phase 4 array (with BERT‐extracted fields)."
    )
    parser.add_argument(
        "--out_phase5", default="/home/xulei/shayan/DIP/data/phase5.json",
        help="Where to write final Phase 5 output."
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Verbose logging."
    )
    args = parser.parse_args()

    # 1) Load Phase 3
    with open(args.phase3_json, "r") as f:
        p3 = json.load(f)
    data3 = p3.get("data", [])
    if not isinstance(data3, list):
        raise ValueError("Phase 3 JSON must have a 'data' array.")

    query_image_url = p3.get("parameters", {}).get("url", "")

    # 2) Phase 4 with BERT
    phase4_data = phase4_with_bert(data3, verbose=args.verbose)
    with open(args.out_phase4, "w") as f4:
        json.dump(phase4_data, f4, indent=2)

    if args.verbose:
        print(f"\n[*] Phase 4 (BERT‐NER) written to {args.out_phase4} "
              f"({len(phase4_data)} entries)")

    # 3) Phase 5 assembly
    phase5_obj = phase5_assemble(phase4_data, query_image_url)
    with open(args.out_phase5, "w") as f5:
        json.dump(phase5_obj, f5, indent=2)

    if args.verbose:
        print(f"[*] Phase 5 output written to {args.out_phase5} "
              f"({len(phase5_obj['results'])} results)")
