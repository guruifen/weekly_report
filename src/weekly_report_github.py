import os
import requests
import json
import urllib3
from datetime import datetime, timedelta
from dotenv import load_dotenv

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv()

API_KEY = os.getenv("DEEPSEEK_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_NAME = "guruifen/weekly_report"
DAYS = 7

def get_commits_via_api():
    if not GITHUB_TOKEN:
        print("? 未找到 GITHUB_TOKEN")
        return []
    
    since_date = (datetime.now() - timedelta(days=DAYS)).isoformat() + "Z"
    url = f"https://api.github.com/repos/{REPO_NAME}/commits"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    params = {"since": since_date, "per_page": 20}
    
    try:
        resp = requests.get(url, headers=headers, params=params, verify=False, timeout=30)
        if resp.status_code == 200:
            commits = resp.json()
            messages = []
            for c in commits:
                msg = c.get("commit", {}).get("message", "")
                first_line = msg.splitlines()[0] if msg else "无提交信息"
                messages.append(f"- {first_line}")
            return messages
        else:
            print(f"? GitHub API 请求失败：{resp.status_code}")
            return []
    except Exception as e:
        print(f"? 网络异常：{e}")
        return []

def generate_report(commits):
    if not commits:
        return {"week_summary": "本周无提交记录", "details": [], "next_plan": "请记得写代码"}

    prompt = f"""
    你是一个专业的周报助手。根据以下本周提交记录，生成周报。
    按「本周工作」（具体工作项列表）、「重点成果」（整体总结）、「下周计划」输出 JSON。

    提交记录：
    {chr(10).join(commits)}
    """

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是一个专业职场助手，只返回合法的 JSON 格式，字段名用中文。"},
            {"role": "user", "content": prompt}
        ],
        "stream": False
    }
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    
    try:
        resp = requests.post("https://api.deepseek.com/v1/chat/completions", 
                             json=payload, headers=headers, timeout=30)
        if resp.status_code == 200:
            content = resp.json()["choices"][0]["message"]["content"]
            print("\\\\n?? AI 原始返回内容：")
            print("-" * 40)
            print(content)
            print("-" * 40)
            try:
                data = json.loads(content)
                # 兼容中英文键名
                return {
                    "week_summary": data.get("重点成果", data.get("week_summary", "未命名周报")),
                    "details": data.get("本周工作", data.get("details", [])),
                    "next_plan": data.get("下周计划", data.get("next_plan", "未指定"))
                }
            except json.JSONDecodeError:
                return {"week_summary": "AI 返回格式异常", "details": [content[:200]], "next_plan": ""}
        else:
            return {"week_summary": f"DeepSeek API 错误: {resp.status_code}", "details": [resp.text[:200]], "next_plan": ""}
    except Exception as e:
        return {"week_summary": f"请求异常: {str(e)}", "details": [], "next_plan": ""}

if __name__ == "__main__":
    print("?? 正在从 GitHub 拉取提交记录...")
    commits = get_commits_via_api()
    
    if commits:
        print(f"? 获取到 {len(commits)} 条提交")
        print("?? AI 正在生成周报...")
        report = generate_report(commits)
        print("\\\\n" + "="*30)
        print(f"?? 周报概览：{report.get('week_summary')}")
        print("\\\\n? 本周工作：")
        for item in report.get('details', []):
            print(f"  - {item}")
        print(f"\\\\n?? 下周计划：{report.get('next_plan', '未指定')}")
        print("="*30)
    else:
        print("?? 未获取到提交记录")