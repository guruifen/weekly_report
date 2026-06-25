import os
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("DEEPSEEK_API_KEY")
print("Key 长度:", len(key) if key else "未加载")