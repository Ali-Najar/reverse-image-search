import requests
import json
from codes.llm_api import ChatAssistant
import os
from utils import fetch_plaintext, extract_links_from_file, prepare_and_upload

IMGBB_API_KEY = "9e1aef25f19ff71c6163cf7659cc644a"


def get_markdown(image_url):
    url = "https://reverse-image-search1.p.rapidapi.com/reverse-image-search"
    
    if isinstance(image_url, str) and os.path.exists(image_url): # is file
        image_url = prepare_and_upload(IMGBB_API_KEY, image_url)
    else:
        image_req = requests.get(image_url)
        if image_req.status_code == 200:
            with open("data/tmp_img.png", "wb") as file:
                file.write(image_req.content)
        
        image_url = prepare_and_upload(IMGBB_API_KEY, "data/tmp_img.png")

    # querystring = {"url":"https://media.licdn.com/dms/image/v2/D4E03AQHA8gahzHINPA/profile-displayphoto-shrink_800_800/profile-displayphoto-shrink_800_800/0/1694105527333?e=1754524800&v=beta&t=wBgk_EuzZc0mDAdgtHvohQibta74MeCS7b-HOgL0wlE","limit":"10","safe_search":"off"}
    querystring = {"url":image_url,"limit":"5","safe_search":"off"}

    headers = {
        "x-rapidapi-key": "d49559bba8msh87cb27666f75b9cp1363e6jsn761c41c132a1",
        "x-rapidapi-host": "reverse-image-search1.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers, params=querystring)

    with open(f"request.json", "w") as f:
        json.dump(response.json(), f, indent=2)

    links = extract_links_from_file(f"request.json")
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
            max_tokens=1000
        )

    resp = assistant.start(raw_text)
    return resp
