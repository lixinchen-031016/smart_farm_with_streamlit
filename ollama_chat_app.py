import streamlit as st

from utils.ollama_chat import main as ollama_chat_main


def main():
    # 设置页面配置
    st.set_page_config(
        page_title="本地大模型聊天系统",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # 自定义CSS样式
    st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        color: #1f4e79;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: bold;
    }
    .chat-container {
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        background-color: #fafafa;
    }
    .user-message {
        background-color: #e3f2fd;
        padding: 10px;
        border-radius: 8px;
        margin: 10px 0;
        border-left: 4px solid #2196f3;
    }
    .ai-message {
        background-color: #f1f8e9;
        padding: 10px;
        border-radius: 8px;
        margin: 10px 0;
        border-left: 4px solid #66bb6a;
    }
    .sidebar-info {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #007acc;
    }
    </style>
    """, unsafe_allow_html=True)

    # 侧边栏
    with st.sidebar:
        st.image("https://upload.wikimedia.org/wikipedia/commons/0/0c/Ollama_logo.png",
                 caption="", width=200)
        st.header("🤖 Ollama 聊天系统")

        st.markdown("""
        <div class="sidebar-info">
        <h4>ℹ️ 关于本系统</h4>
        <p>这是一个基于本地大语言模型的聊天系统，使用 Ollama 和 qwen3:4b 模型。</p>
        <ul>
        <li>✅ 本地运行，隐私安全</li>
        <li>🤖 支持多种大语言模型</li>
        <li>💬 实时对话体验</li>
        <li>🔄 可切换不同模型</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.header("⚙️ 设置")

        # 模型选择
        model_choice = st.selectbox(
            "选择模型:",
            ["qwen3:4b", "llama3:8b", "mistral:7b", "gemma:7b"],
            index=0
        )

        st.session_state.selected_model = model_choice

        # 其他设置选项
        temperature = st.slider("温度 (Creativity)", 0.0, 1.0, 0.7, 0.1)
        st.session_state.temperature = temperature

        st.markdown("---")
        st.header("📋 操作指南")
        st.markdown("""
        1. 确保Ollama服务正在运行
        2. 选择合适的模型
        3. 输入您的问题
        4. 点击发送获取回答
        """)

    # 主界面标题
    st.markdown('<div class="main-header">🤖 本地大模型聊天系统</div>', unsafe_allow_html=True)

    # 显示当前模型信息
    st.info(f"**当前模型:** {st.session_state.get('selected_model', 'qwen3:4b')} | "
            f"**温度:** {st.session_state.get('temperature', 0.7)}")

    # 运行Ollama聊天主界面
    ollama_chat_main()


if __name__ == "__main__":
    main()
