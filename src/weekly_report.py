import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not API_KEY:
    print("❌ 请设置 API Key")
    exit(1)

url = "https://api.deepseek.com/v1/chat/completions"

# ==========================================
# 1. 模拟本周的“工作数据”（先固定写死）
# ==========================================
mock_data = """
- 修复了登录页面的 Bug
- 优化了数据查询接口的性能
- 参加了团队周会
- 完成了用户手册的编写
- 评审了同事的代码 PR
"""

# ==========================================
# 2. 核心：周报生成 Prompt（Few-shot 示例）
# ==========================================
prompt = f"""
你是一个专业的周报撰写助手。请根据以下工作内容，生成一份结构清晰的周报。

要求：
1. 按「本周工作」、「重点成果」、「下周计划」三个板块输出。
2. 语言精炼、专业。
3. 必须输出 JSON 格式。

工作内容：
{mock_data}

请返回 JSON：
{{
    "week_summary": "概括本周整体情况",
    "details": ["具体工作项1", "具体工作项2"],
    "next_plan": "下周主要方向"
}}
"""

payload = {
    "model": "deepseek-chat",
    "messages": [{"role": "system", "content": "你是一个专业的职场助手。"},
                 {"role": "user", "content": prompt}],
    "stream": False
}
headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

print("📝 AI 正在撰写周报...")
resp = requests.post(url, json=payload, headers=headers, timeout=30)

if resp.status_code == 200:
    result = resp.json()
    # 解析 AI 返回的 JSON
    try:
        report = json.loads(result["choices"][0]["message"]["content"])
        print("\n" + "="*30)
        print(f"📅 周报概览：{report.get('week_summary')}")
        print("\n✅ 本周工作：")
        for item in report.get('details', []):
            print(f"  - {item}")
        print(f"\n🚀 下周计划：{report.get('next_plan')}")
        print("="*30)
    except:
        print("AI 返回格式解析失败，原始内容如下：")
        print(result["choices"][0]["message"]["content"])
else:
    print(f"❌ 请求失败：{resp.text}")