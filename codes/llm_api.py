import os
import requests
import json
# from speech_to_text import SpeechToText
# from text_to_speech import TextToSpeech

system_prompt = """
You are an expert biographer. Given any input text, identify the single main individual and generate a concise, well‐structured biography in Markdown. Your output must include:

- **Name**  
- **Occupation / Role**  
- **Birth date (and place, if available)**  
- **Key achievements or notable facts**  
- **Any other relevant personal details**

Follow these rules:
1. Focus strictly on the primary person; do not profile secondary figures.  
2. Do not quote or reference the source text or its site—only present the biography.  
3. Write entirely in English.  
4. Use proper Markdown headings, bullet lists, and emphasis for readability.
5. Provide the information if available.

Example structure: 

```markdown
# [Person’s Name]

**Occupation:** …

**Born:** [Date], [Place]

## Early Life
…

## Career & Achievements
…

## Personal Life
…

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
        self.messages = [{"role": "system", "content": system_prompt}]
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
            # "max_completion_tokens": self.max_tokens
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
# assistant = ChatAssistant(
#         api_key="tpsg-MNvTQUAqUL84o4THLV1395IqTBIZHJJ",
#         # text_to_speech=t2s,
#         # speech_to_text=s2t,
#         provider="openai_chat_completion",
#         base_url="https://api.tapsage.com",
#         model="o4-mini",
#         max_tokens=1000
#     )

# resp = assistant.start("GIVE ME A NEW GAME")