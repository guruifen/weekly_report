import streamlit as st
import requests
import json
import os
import re
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
from fpdf import FPDF

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
if "history" not in st.session_state:
    st.session_state.history = []
if "generating" not in st.session_state:
    st.session_state.generating = False
if "last_generate_time" not in st.session_state:
    st.session_state.last_generate_time = 0

# ========== 安全获取字符串 ==========
def safe_str(value, default=""):
    """安全地将任何值转换为字符串"""
    if value is None:
        return default
    if isinstance(value, list):
        # 如果值是列表，用逗号连接
        return ", ".join([str(v) for v in value if v is not None])
    if isinstance(value, dict):
        # 如果是字典，转成JSON字符串
        return json.dumps(value, ensure_ascii=False)
    return str(value)

def clean_text(text):
    if not text:
        return ""
    # 确保 text 是字符串
    text = safe_str(text)
    emoji_pattern = re.compile(
        "[\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001f926-\U0001f937"
        "\U00010000-\U0010ffff"
        "\u200d"
        "\u2640-\u2642"
        "\u2600-\u2B55"
        "\u23cf"
        "\u23e9"
        "\u231a"
        "\ufe0f"
        "\u3030"
        "]+",
        flags=re.UNICODE
    )
    text = emoji_pattern.sub(r'', text)
    text = text.replace('•', '-')
    text = text.replace('"', "'")
    text = text.replace('"', "'")
    return text

def repair_json(content):
    if not content:
        return content
    content = re.sub(r'```json\s*', '', content)
    content = re.sub(r'```\s*', '', content)
    if content.startswith('\ufeff'):
        content = content[1:]
    content = re.sub(r',\s*}', '}', content)
    content = re.sub(r',\s*]', ']', content)
    content = re.sub(r'"\s*"', '", "', content)
    content = re.sub(r',\s*$', '', content)
    return content

def parse_json_safely(content):
    try:
        return json.loads(content)
    except:
        pass
    try:
        fixed = repair_json(content)
        return json.loads(fixed)
    except:
        pass
    try:
        match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
        if match:
            return json.loads(match.group())
    except:
        pass
    return {
        "重点成果": "本周已完成工作",
        "本周工作": [content[:300] + "..." if len(content) > 300 else content],
        "下周计划": "继续推进当前工作"
    }

def generate_pdf(data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 18)
    pdf.cell(0, 12, "AI Weekly Report", ln=True, align="C")
    pdf.ln(6)
    pdf.set_font("Arial", "I", 10)
    pdf.cell(0, 6, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align="R")
    pdf.ln(6)
    
    # ====== 安全获取字段 ======
    pdf.set_font("Arial", "B", 13)
    pdf.cell(0, 8, "Summary", ln=True)
    pdf.set_font("Arial", "", 11)
    summary = clean_text(data.get("重点成果", data.get("week_summary", "未命名周报")))
    pdf.multi_cell(0, 7, summary)
    pdf.ln(4)
    
    pdf.set_font("Arial", "B", 13)
    pdf.cell(0, 8, "This Week's Work", ln=True)
    pdf.set_font("Arial", "", 11)
    details = data.get("本周工作", data.get("details", []))
    # 确保 details 是列表
    if not isinstance(details, list):
        details = [str(details)]
    for item in details:
        cleaned_item = clean_text(str(item))
        pdf.multi_cell(0, 7, f"  - {cleaned_item}")
    pdf.ln(4)
    
    pdf.set_font("Arial", "B", 13)
    pdf.cell(0, 8, "Next Week's Plan", ln=True)
    pdf.set_font("Arial", "", 11)
    # 安全获取下周计划，确保是字符串
    next_plan_raw = data.get("下周计划", data.get("next_plan", "未指定"))
    next_plan = clean_text(safe_str(next_plan_raw, "未指定"))
    pdf.multi_cell(0, 7, next_plan)
    
    pdf_output = pdf.output(dest='S')
    return pdf_output

def display_report(data):
    unique_id = str(int(time.time() * 1000))
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader("📋 本周周报")
    with col2:
        # 安全获取各个字段
        summary = safe_str(data.get("重点成果", data.get("week_summary", "未命名周报")))
        details = data.get("本周工作", data.get("details", []))
        if not isinstance(details, list):
            details = [str(details)]
        next_plan = safe_str(data.get("下周计划", data.get("next_plan", "未指定")))
        
        report_text = f"""
📅 周报概览：{summary}

✅ 本周工作：
{chr(10).join(['- ' + str(item) for item in details if item])}

🚀 下周计划：{next_plan}
        """
        st.download_button(
            label="📋 复制周报",
            data=report_text,
            file_name=f"周报_{datetime.now().strftime('%Y%m%d')}.md",
            mime="text/markdown",
            use_container_width=True,
            key=f"download_md_{unique_id}"
        )
        pdf_data = generate_pdf(data)
        st.download_button(
            label="📄 下载 PDF",
            data=pdf_data,
            file_name=f"周报_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf",
            use_container_width=True,
            key=f"download_pdf_{unique_id}"
        )
    
    # ====== 页面展示 ======
    summary = safe_str(data.get("重点成果", data.get("week_summary", "未命名周报")))
    st.info(f"📌 **整体总结**：{summary}")
    
    details = data.get("本周工作", data.get("details", []))
    if not isinstance(details, list):
        details = [str(details)]
    if details:
        st.success("✅ **本周工作**")
        for item in details:
            st.write(f"- {item}")
    
    next_plan = safe_str(data.get("下周计划", data.get("next_plan", "未指定")))
    st.warning(f"🚀 **下周计划**：{next_plan}")
    st.caption(f"🕐 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ========== 页头 ==========
st.title("📊 AI 周报生成器")
st.markdown("> ✨ 输入 GitHub 仓库或手动粘贴工作内容，AI 自动生成本周工作报告")
st.divider()

# ========== 侧边栏 ==========
with st.sidebar:
    st.header("⚙️ 配置")
    input_mode = st.radio("📝 输入方式", ["GitHub 自动拉取", "手动输入内容"], index=0)
    if input_mode == "GitHub 自动拉取":
        repo_input = st.text_input("📁 GitHub 仓库", value=REPO_NAME, help="多个仓库用逗号分隔")
        days = st.slider("📅 统计天数", 1, 14, 7)
        manual_text = ""
    else:
        st.caption("💡 每行输入一条工作内容")
        manual_text = st.text_area(
            "📋 本周工作内容",
            placeholder="例如：\n- 修复了登录页面的 Bug\n- 优化了数据库查询性能",
            height=200
        )
        repo_input = REPO_NAME
        days = 7
    
    st.divider()
    
    dark_mode = st.toggle("🌙 暗黑模式", value=False)
    if dark_mode:
        st.markdown("""
            <style>
                .stApp { background-color: #0E1117; }
                .stApp *:not(input):not(textarea) { color: #FAFAFA !important; }
                .stApp .st-emotion-cache-1wmy9hl { background-color: #0E1117; }
                .stApp .st-emotion-cache-1gv3huu { background-color: #262730; }
                .stApp .st-emotion-cache-1r6slb0 { background-color: #262730; }
                .stApp .st-emotion-cache-16idsys { background-color: #262730; }
                .stApp .st-emotion-cache-1wrcr25 { color: #FAFAFA !important; }
                .stApp .st-emotion-cache-1v0mbdj { color: #FAFAFA !important; }
                .stApp .st-emotion-cache-1m4mwv6 { color: #FAFAFA !important; }
                .stApp .st-emotion-cache-6qob1r { background-color: #1E1E2E; }
                .stApp .st-emotion-cache-1v0mbdj button { background-color: #FF6B6B !important; color: #FFFFFF !important; }
                .stApp .st-emotion-cache-1m4mwv6 { background-color: #1E3A5F !important; border-left-color: #FF6B6B !important; }
                .stApp .st-emotion-cache-1wrcr25 { background-color: #1E4A3A !important; border-left-color: #00D4AA !important; }
                .stApp .st-emotion-cache-1v0mbdj { background-color: #4A3A1E !important; border-left-color: #FFB800 !important; }
                .stApp hr { border-color: #333333 !important; }
                .stApp input, .stApp textarea { background-color: #1E1E2E !important; color: #FAFAFA !important; border-color: #444444 !important; }
                .stApp input:focus, .stApp textarea:focus { border-color: #FF6B6B !important; }
                .stApp .st-emotion-cache-1gv3huu { background-color: #333333 !important; }
                .stApp .st-emotion-cache-1r6slb0 { background-color: #FF6B6B !important; }
                .stApp .st-emotion-cache-1v0mbdj button:hover { background-color: #FF8A8A !important; }
                .stApp .st-emotion-cache-1wmy9hl button { background-color: #2E2E3E !important; border-color: #444444 !important; }
                .stApp .st-emotion-cache-1wmy9hl button:hover { background-color: #3E3E4E !important; }
                ::-webkit-scrollbar { width: 8px; background-color: #1E1E2E; }
                ::-webkit-scrollbar-thumb { background-color: #444444; border-radius: 4px; }
                ::-webkit-scrollbar-thumb:hover { background-color: #666666; }
                .stApp .st-emotion-cache-16idsys { background-color: #1E1E2E !important; color: #FAFAFA !important; }
            </style>
        """, unsafe_allow_html=True)
    
    st.divider()
    st.caption("🔑 需要配置以下密钥才能使用：")
    st.caption("• DeepSeek API Key")
    if input_mode == "GitHub 自动拉取":
        st.caption("• GitHub Token")
    st.divider()
    
    st.subheader("📚 历史周报")
    if st.session_state.history:
        unique_history = []
        seen_summaries = set()
        for item in reversed(st.session_state.history[-10:]):
            summary = item.get("summary", "周报")[:20]
            if summary not in seen_summaries:
                seen_summaries.add(summary)
                unique_history.append(item)
        
        for i, item in enumerate(unique_history[:5]):
            summary = item.get("summary", "周报")
            if len(summary) > 20:
                summary = summary[:20] + "..."
            btn_key = f"history_{i}_{int(time.time() * 1000)}"
            if st.button(f"📅 {item['date']} - {summary}", key=btn_key):
                with report_placeholder.container():
                    display_report(item["data"])
    else:
        st.caption("暂无历史记录")
    st.divider()
    
    generate_btn = st.button("🚀 生成周报", type="primary", use_container_width=True)

# ========== 主区域 ==========
status_placeholder = st.empty()
report_placeholder = st.empty()

if st.session_state.report_data:
    with report_placeholder.container():
        display_report(st.session_state.report_data)

# ========== 生成逻辑 ==========
if generate_btn and not st.session_state.generating:
    current_time = time.time()
    if current_time - st.session_state.last_generate_time < 2:
        status_placeholder.warning("⏳ 请勿频繁点击，请稍后再试")
        st.session_state.generating = False
        st.stop()
    
    st.session_state.last_generate_time = current_time
    st.session_state.generating = True
    report_placeholder.empty()
    
    try:
        content_text = ""
        
        if input_mode == "手动输入内容":
            if not manual_text.strip():
                status_placeholder.warning("⚠️ 请先输入本周工作内容")
                st.session_state.generating = False
                st.stop()
            content_text = manual_text.strip()
            line_count = len([l for l in content_text.split("\n") if l.strip()])
            status_placeholder.success(f"✅ 获取到 {line_count} 条工作记录")
        else:
            repos = [r.strip() for r in repo_input.split(",") if r.strip()]
            if not repos:
                status_placeholder.warning("⚠️ 请输入至少一个仓库名")
                st.session_state.generating = False
                st.stop()
            
            status_placeholder.info(f"📡 正在从 {len(repos)} 个仓库拉取提交记录...")
            since_date = (datetime.now() - timedelta(days=days)).isoformat() + "Z"
            
            lines = []
            failed_repos = []
            
            for repo in repos:
                try:
                    url = f"https://api.github.com/repos/{repo}/commits"
                    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
                    params = {"since": since_date, "per_page": 10}
                    resp = requests.get(url, headers=headers, params=params, timeout=30, verify=False)
                    if resp.status_code == 200:
                        commits = resp.json()
                        if commits:
                            for c in commits:
                                msg = c.get("commit", {}).get("message", "")
                                first_line = msg.splitlines()[0] if msg else "无提交信息"
                                lines.append(f"- [{repo}] {first_line}")
                        else:
                            lines.append(f"- [{repo}] 本周无提交")
                    else:
                        failed_repos.append(repo)
                        lines.append(f"- [{repo}] 拉取失败（{resp.status_code}）")
                except Exception as e:
                    failed_repos.append(repo)
                    lines.append(f"- [{repo}] 网络异常：{str(e)[:30]}")
            
            if not lines:
                status_placeholder.warning("⚠️ 未获取到任何提交记录")
                st.session_state.generating = False
                st.stop()
            
            content_text = "\n".join(lines)
            
            if failed_repos:
                status_placeholder.warning(f"⚠️ 以下仓库拉取失败：{', '.join(failed_repos)}，已跳过")
            else:
                valid_count = len([l for l in lines if "无提交" not in l and "失败" not in l and "异常" not in l])
                status_placeholder.success(f"✅ 从 {len(repos)} 个仓库获取到 {valid_count} 条有效提交")
        
        status_placeholder.info("🤖 AI 正在撰写周报，请稍候...")
        
        if input_mode == "手动输入内容":
            prompt_prefix = "你是一个专业的周报助手。根据以下本周工作内容，生成一份结构清晰的专业周报。"
        else:
            prompt_prefix = "你是一个专业的周报助手。根据以下本周提交记录（仓库名已标注），生成一份综合周报。"
        
        if not content_text or not content_text.strip():
            content_text = "暂无有效工作内容"
        
        prompt = f"""
        {prompt_prefix}
        按「本周工作」（具体工作项列表）、「重点成果」（整体总结）、「下周计划」输出 JSON。

        工作内容：
        {content_text}
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
            data = parse_json_safely(content)
            
            is_duplicate = False
            if st.session_state.history:
                last_summary = st.session_state.history[-1].get("summary", "")
                current_summary = data.get("重点成果", data.get("week_summary", ""))[:30]
                if last_summary == current_summary:
                    is_duplicate = True
            
            if not is_duplicate:
                st.session_state.report_data = data
                st.session_state.history.append({
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "data": data,
                    "summary": data.get("重点成果", data.get("week_summary", "未命名周报"))[:30]
                })
                status_placeholder.empty()
                with report_placeholder.container():
                    display_report(data)
            else:
                status_placeholder.info("ℹ️ 本次生成的周报与上次相同，已自动跳过重复记录")
                with report_placeholder.container():
                    display_report(data)
        else:
            status_placeholder.error(f"❌ AI 生成失败：{ds_resp.text}")
    except Exception as e:
        status_placeholder.error(f"❌ 请求异常：{e}")
    
    st.session_state.generating = False

st.divider()
st.caption("💡 提示：确保 .env 文件已配置 DEEPSEEK_API_KEY")