import streamlit as st
import requests
import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置
API_KEY = os.getenv("DEEPSEEK_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_NAME = "guruifen/weekly_report"

st.set_page_config(page_title="AI 周报生成器", page_icon="??")
st.title("?? AI 周报生成器")
st.caption("输入 GitHub 仓库，AI 自动生成本周工作报告")

# 侧边栏配置
with st.sidebar:
    st.header("?? 配置")
    repo_input = st.text_input("GitHub 仓库", value=REPO_NAME)
    days = st.slider("统计天数", 1, 14, 7)
    st.caption("需要 GitHub Token 和 DeepSeek API Key")
    if st.button("?? 生成周报"):
        with st.spinner("正在拉取提交记录..."):
            # 拉取 GitHub 提交
            since_date = (datetime.now() - timedelta(days=days)).isoformat() + "Z"
            url = f"https://api.github.com/repos/{repo_input}/commits"
            headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
            params = {"since": since_date, "per_page": 20}
            
            try:
                resp = requests.get(url, headers=headers, params=params, timeout=30, verify=False)
                if resp.status_code == 200:
                    commits = resp.json()
                    if not commits:
                        st.warning("该仓库本周暂无提交记录")
                    else:
                        # 提取提交信息
                        messages = []
                        for c in commits:
                            msg = c.get("commit", {}).get("message", "")
                            first_line = msg.splitlines()[0] if msg else "无提交信息"
                            messages.append(f"- {first_line}")
                        
                        st.success(f"? 获取到 {len(messages)} 条提交")
                        
                        # 调用 AI 生成周报
                        with st.spinner("AI 正在撰写周报..."):
                            prompt = f"""
                            你是一个专业的周报助手。根据以下本周提交记录，生成周报。
                            按「本周工作」（具体工作项列表）、「重点成果」（整体总结）、「下周计划」输出 JSON。

                            提交记录：
                            {chr(10).join(messages)}
                            """
                            payload = {
                                "model": "deepseek-chat",
                                "messages": [
                                    {"role": "system", "content": "你是一个专业职场助手，只返回合法的 JSON 格式，字段名用中文。"},
                                    {"role": "user", "content": prompt}
                                ],
                                "stream": False
                            }
                            headers_ds = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
                            ds_resp = requests.post("https://api.deepseek.com/v1/chat/completions", 
                                                     json=payload, headers=headers_ds, timeout=30)
                            if ds_resp.status_code == 200:
                                content = ds_resp.json()["choices"][0]["message"]["content"]
                                data = json.loads(content)
                                
                                # 显示周报
                                st.divider()
                                st.subheader("?? 本周周报")
                                
                                # 重点成果（整体总结）
                                summary = data.get("重点成果", data.get("week_summary", "未命名周报"))
                                st.info(f"?? **整体总结**：{summary}")
                                
                                # 本周工作
                                details = data.get("本周工作", data.get("details", []))
                                if details:
                                    st.write("**? 本周工作：**")
                                    for item in details:
                                        st.write(f"- {item}")
                                
                                # 下周计划
                                next_plan = data.get("下周计划", data.get("next_plan", "未指定"))
                                st.write(f"**?? 下周计划：** {next_plan}")
                            else:
                                st.error(f"AI 生成失败：{ds_resp.text}")
                else:
                    st.error(f"GitHub API 请求失败：{resp.status_code}")
            except Exception as e:
                st.error(f"请求异常：{e}")

# 页脚
st.divider()
st.caption("?? 提示：确保 .env 文件已配置 DEEPSEEK_API_KEY 和 GITHUB_TOKEN")