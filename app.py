import streamlit as st
import requests
import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# ========== 页面配置 ==========
st.set_page_config(
    page_title="AI 周报生成器",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

load_dotenv()

# ========== 配置 ==========
API_KEY = os.getenv("DEEPSEEK_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_NAME = "guruifen/weekly_report"

# ========== 初始化 session_state ==========
if "report_data" not in st.session_state:
    st.session_state.report_data = None
if "commits_count" not in st.session_state:
    st.session_state.commits_count = 0

# ========== 页头 ==========
st.title("📊 AI 周报生成器")
st.markdown("> ✨ 输入 GitHub 仓库，AI 自动生成本周工作报告，让你的团队协作一目了然。")
st.divider()

# ========== 侧边栏 ==========
with st.sidebar:
    st.header("⚙️ 配置")
    
    repo_input = st.text_input("📁 GitHub 仓库", value=REPO_NAME)
    days = st.slider("📅 统计天数", 1, 14, 7)
    
    st.divider()
    st.caption("🔑 需要配置以下密钥才能使用：")
    st.caption("• DeepSeek API Key")
    st.caption("• GitHub Token")
    st.caption("（已在 .env 中配置）")
    st.divider()
    
    # 使用 key 参数让按钮状态可追踪，disabled 控制禁用
    generate_btn = st.button(
        "🚀 生成周报", 
        type="primary", 
        use_container_width=True,
        key="generate_btn"
    )

# ========== 主区域占位 ==========
status_placeholder = st.empty()      # 用于显示状态信息
report_placeholder = st.empty()      # 用于显示周报内容

# ========== 显示缓存的周报 ==========
if st.session_state.report_data:
    with report_placeholder.container():
        display_report(st.session_state.report_data)

# ========== 生成逻辑 ==========
if generate_btn:
    # 禁用按钮（通过 st.session_state 控制）
    st.session_state.generating = True
    
    # 清空旧内容
    report_placeholder.empty()
    
    # 状态 1：拉取提交
    status_placeholder.info("📡 正在从 GitHub 拉取提交记录...")
    
    since_date = (datetime.now() - timedelta(days=days)).isoformat() + "Z"
    url = f"https://api.github.com/repos/{repo_input}/commits"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    params = {"since": since_date, "per_page": 20}
    
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30, verify=False)
        if resp.status_code == 200:
            commits = resp.json()
            if not commits:
                status_placeholder.warning("⚠️ 该仓库本周暂无提交记录")
                st.session_state.generating = False
            else:
                messages = []
                for c in commits:
                    msg = c.get("commit", {}).get("message", "")
                    first_line = msg.splitlines()[0] if msg else "无提交信息"
                    messages.append(f"- {first_line}")
                
                st.session_state.commits_count = len(messages)
                status_placeholder.success(f"✅ 获取到 {len(messages)} 条提交")
                
                # 状态 2：AI 生成
                status_placeholder.info("🤖 AI 正在撰写周报，请稍候...")
                
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
                    
                    # 保存到 session_state
                    st.session_state.report_data = data
                    
                    # 清除状态提示
                    status_placeholder.empty()
                    
                    # 显示周报
                    with report_placeholder.container():
                        display_report(data)
                else:
                    status_placeholder.error(f"❌ AI 生成失败：{ds_resp.text}")
        else:
            status_placeholder.error(f"❌ GitHub API 请求失败：{resp.status_code}")
    except Exception as e:
        status_placeholder.error(f"❌ 请求异常：{e}")
    
    st.session_state.generating = False

# ========== 页脚 ==========
st.divider()
st.caption("💡 提示：确保 .env 文件已配置 DEEPSEEK_API_KEY 和 GITHUB_TOKEN")


# ========== 辅助函数：显示周报 ==========
def display_report(data):
    """统一展示周报的组件"""
    col1, col2 = st.columns([4, 1])
    with col1:
        st.subheader("📋 本周周报")
    with col2:
        # 复制按钮
        report_text = f"""
📅 周报概览：{data.get('重点成果', data.get('week_summary', '未命名周报'))}

✅ 本周工作：
{chr(10).join(['- ' + item for item in data.get('本周工作', data.get('details', []))])}

🚀 下周计划：{data.get('下周计划', data.get('next_plan', '未指定'))}
        """
        st.download_button(
            label="📋 复制周报",
            data=report_text,
            file_name=f"周报_{datetime.now().strftime('%Y%m%d')}.md",
            mime="text/markdown",
            use_container_width=True
        )
    
    # 重点成果（蓝色信息框）
    summary = data.get("重点成果", data.get("week_summary", "未命名周报"))
    st.info(f"📌 **整体总结**：{summary}")
    
    # 本周工作（绿色成功框）
    details = data.get("本周工作", data.get("details", []))
    if details:
        st.success("✅ **本周工作**")
        for item in details:
            st.write(f"- {item}")
    
    # 下周计划（黄色警告框）
    next_plan = data.get("下周计划", data.get("next_plan", "未指定"))
    st.warning(f"🚀 **下周计划**：{next_plan}")
    
    # 显示生成时间
    st.caption(f"🕐 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")