import os
import requests
import json
# from speech_to_text import SpeechToText
# from text_to_speech import TextToSpeech

system_prompt = """ 
  Your task is to create a biography of the main person mentioned in the text and return it please in MARKDOWN format and structured.
  The biography should include the person's name, job, birth date and other relevant information if available.
  Ignore the other content of the text just focus on the biography of the person. Also just focus on one person which is the main person of the text and don't mention others.
  PLEASE ONLY TALK ABOUT THE PERSON AND DON'T MENTION THE SITE TEXTS I GAVE YOU OR ANYTHING ELSE.
  GIVE THE BIOGRAPHY IN ENGLISH.
  """

class ChatAssistant:
    def __init__(
        self,
        api_key: str,
        # text_to_speech: TextToSpeech,
        # speech_to_text: SpeechToText,
        provider: str = "openai_chat_completion",
        base_url: str = "https://api.metisai.ir",
        model: str = "gpt-4o-mini-2024-07-18",
        max_tokens: int = 300,
        assistant_type = "transaction"
    ):
        # self.speech_to_text = speech_to_text
        # self.text_to_speech = text_to_speech
        self.endpoint = f"{base_url}/api/v1/wrapper/{provider}/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self.model = model
        self.max_tokens = max_tokens
        self.messages = [{"role": "system", "content": "{system_prompt}"}]
        self.assistant_type = assistant_type

    def start(self,message):
        """
        Begin the interactive chat loop.
        Type 'stop' or 'exit' to end the session.
        """
        # same, user_input = self.speech_to_text.process_voice("new_voice.wav", flag=0)

        # Append user message
        self.messages.append({"role": "user", "content": message})

        # Build payload
        payload = {
            "model": self.model,
            "messages": self.messages,
            "max_tokens": self.max_tokens
        }
        resp = requests.post(self.endpoint, json=payload, headers=self.headers)
        
        data = resp.json()

        resp = data["choices"][0]["message"]["content"]

        self.messages.append({"role": "assistant", "content": resp})
        print(f"🤖 Assistant: {resp}\n")
        
        return resp

# ─────────── Usage ───────────
# if __name__ == "__main__":

#     assistant = ChatAssistant(
#         api_key="tpsg-MNvTQUAqUL84o4THLV1395IqTBIZHJJ",
#         # text_to_speech=t2s,
#         # speech_to_text=s2t,
#         provider="openai_chat_completion",
#         base_url="https://api.tapsage.com",
#         model="gpt-4o",
#         max_tokens=30
#     )
#     assistant.start("HELLLO")
