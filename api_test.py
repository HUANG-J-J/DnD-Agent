import os
from dotenv import load_dotenv
from openai import OpenAI
        

client = OpenAI(
    api_key=os.environ["LLM_API_KEY"],
    base_url=os.environ["LLM_BASE_URL"],
)

resp = client.chat.completions.create(
    model="glm-4.7-flash",
    messages=[{"role": "user", "content": "你好，介绍一下你自己的功能和角色"}],
)

print(resp.choices[0].message.content)