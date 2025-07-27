import requests
import json
from codes.llm_api import ChatAssistant
from utils import fetch_plaintext, extract_links_from_file, _fetch_with_playwright


def get_markdown(image_url):
    url = "https://reverse-image-search1.p.rapidapi.com/reverse-image-search"

    # querystring = {"url":"https://media.licdn.com/dms/image/v2/D4E03AQHA8gahzHINPA/profile-displayphoto-shrink_800_800/profile-displayphoto-shrink_800_800/0/1694105527333?e=1754524800&v=beta&t=wBgk_EuzZc0mDAdgtHvohQibta74MeCS7b-HOgL0wlE","limit":"10","safe_search":"off"}
    querystring = {"url":image_url,"limit":"5","safe_search":"off"}

    headers = {
        "x-rapidapi-key": "442330cd73msh2c111d452cb6be1p14bac9jsn77eedb6d3f72",
        "x-rapidapi-host": "reverse-image-search1.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers, params=querystring)

    with open(f"request.json", "w") as f:
        json.dump(response.json(), f, indent=2)

    links = extract_links_from_file(f"request.json")
    print("KKFKFK" , links)
    raw_text = ""
    for link in links:
        text = fetch_plaintext(link)
        raw_text += text[0] + "   "

    assistant = ChatAssistant(
            api_key="tpsg-MNvTQUAqUL84o4THLV1395IqTBIZHJJ",
            # text_to_speech=t2s,
            # speech_to_text=s2t,
            provider="openai_chat_completion",
            base_url="https://api.tapsage.com",
            model="o4-mini",
            max_tokens=500
        )

    resp = assistant.start(raw_text)
    return resp
