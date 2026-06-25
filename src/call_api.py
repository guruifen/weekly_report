import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not API_KEY:
    print("❌ 未找到 API Key，请检查 .env 文件")
    exit(1)

print(f"✅ Key 已加载，长度：{len(API_KEY)}")  # 调试信息

url = "https://api.deepseek.com/v1/chat/completions"
user_input = input("👤 你：")

payload = {
    "model": "deepseek-chat",
    "messages": [
        {"role": "system", "content": "你是一个 helpful 的 AI 助手。"},
        {"role": "user", "content": user_input}
    ],
    "stream": False
}

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

print("🤖 AI 思考中...")
try:
    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    print(f"状态码：{resp.status_code}")  # 调试信息
    if resp.status_code == 200:
        answer = resp.json()["choices"][0]["message"]["content"]
        print(f"\n🤖 AI：{answer}")
    else:
        print(f"❌ 请求失败，状态码：{resp.status_code}")
        print(f"服务器返回：{resp.text}")  # 关键！看错误原因
except Exception as e:
    print(f"❌ 网络异常：{e}")