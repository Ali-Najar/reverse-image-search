import requests

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
    def __init__(self, api_key, provider="openai_chat_completion", base_url="https://api.metisai.ir",
        model="gpt-4o-mini-2024-07-18", max_tokens=300, assistant_type="transaction"):
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
        self.messages.append({"role": "user", "content": message})
        payload = {
            "model": self.model,
            "messages": self.messages,
        }
        resp = requests.post(self.endpoint, json=payload, headers=self.headers)
        
        data = resp.json()

        resp = data["choices"][0]["message"]["content"]

        self.messages.append({"role": "assistant", "content": resp})
        print(f"🤖 Assistant: {resp}\n")
        
        return resp