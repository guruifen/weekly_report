import os
import requests
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from github import Github

load_dotenv()
API_KEY = os.getenv("DEEPSEEK_API_KEY")

# ==========================================
# 配置区（按需修改）
# ==========================================
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")          # 替换成刚才复制的 token
REPO_NAME = "guruifen/weekly_report"            # 比如 "octocat/Hello-World"
DAYS = 7                                   # 统计最近几天的提交

# ==========================================
# 1. 从 GitHub 拉取最近一周的提交记录
# ==========================================
def get_commits():
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    since = datetime.now() - timedelta(days=DAYS)
    commits = repo.get_commits(since=since)
    return [f"- {c.commit.message.splitlines()[0]}" for c in commits][:20]  # 取前20条

# ==========================================
# 2. 调用 DeepSeek 生成周报
# ==========================================
def generate_report(commits):
    if not commits:
        return {"week_summary": "本周无提交记录", "details": [], "next_plan": "请记得写代码"}

    prompt = f"""
    你是一个专业的周报助手。根据以下本周提交记录，生成周报。
    按「本周工作」、「重点成果」、「下周计划」输出 JSON。

    提交记录：
    {chr(10).join(commits)}
    """

    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "system", "content": "你是一个专业职场助手。"},
                     {"role": "user", "content": prompt}],
        "stream": False
    }
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    
    resp = requests.post("https://api.deepseek.com/v1/chat/completions", 
                         json=payload, headers=headers, timeout=30)
    if resp.status_code == 200:
        return json.loads(resp.json()["choices"][0]["message"]["content"])
    else:
        return {"week_summary": f"API 错误: {resp.text}", "details": [], "next_plan": ""}

# ==========================================
# 3. 执行
# ==========================================
if __name__ == "__main__":
    print("📡 正在从 GitHub 拉取提交记录...")
    commits = get_commits()
    print(f"✅ 获取到 {len(commits)} 条提交")

    print("📝 AI 正在生成周报...")
    report = generate_report(commits)
    print("\n" + "="*30)
    print(f"📅 周报概览：{report.get('week_summary')}")
    print("\n✅ 本周工作：")
    for item in report.get('details', []):
        print(f"  - {item}")
    print(f"\n🚀 下周计划：{report.get('next_plan')}")
    print("="*30)