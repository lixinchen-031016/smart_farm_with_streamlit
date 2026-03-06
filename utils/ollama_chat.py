import json
from datetime import datetime

import ollama
import streamlit as st


class OllamaChat:
    def __init__(self, model_name="qwen3:4b"):
        """
        初始化Ollama聊天类
        :param model_name: 要使用的模型名称，默认为qwen3:4b
        """
        self.model_name = model_name
        self.chat_history = []
        
    def check_model_available(self):
        """检查模型是否可用"""
        try:
            # 获取可用模型列表
            models_response = ollama.list()
            
            # 检查响应格式并提取模型名称
            available_models = []
            if hasattr(models_response, 'models'):
                for model in models_response.models:
                    # Ollama库返回的是自定义对象，需要通过属性访问
                    # 根据dir(model)输出，模型对象使用'model'属性而不是'name'属性
                    if hasattr(model, 'model'):
                        available_models.append(model.model)
                    elif hasattr(model, 'name'):  # 备选属性名
                        available_models.append(model.name)
                    else:
                        # 处理其他可能的格式
                        available_models.append(str(model))
            
            # 检查指定模型是否在列表中
            model_exists = any(self.model_name.lower() in model_name.lower() for model_name in available_models)
            
            if not model_exists:
                # 尝试精确匹配
                model_exists = self.model_name in available_models
            
            return model_exists, available_models
        except Exception as e:
            st.error(f"无法连接到Ollama服务: {str(e)}")
            return False, []

    def pull_model_if_needed(self):
        """如果需要则拉取模型"""
        is_available, available_models = self.check_model_available()
        
        if not is_available:
            st.warning(f"模型 {self.model_name} 未找到。正在尝试拉取模型...")
            try:
                # 显示进度信息
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                status_text.text("正在拉取模型，请稍候...")
                
                # 拉取模型
                response = ollama.pull(self.model_name)
                
                # 更新进度
                progress_bar.progress(100)
                status_text.text("模型拉取完成!")
                
                # 稍等一下让模型加载
                import time
                time.sleep(2)
                
                st.success(f"模型 {self.model_name} 已成功拉取并准备就绪!")
                return True
            except Exception as e:
                st.error(f"拉取模型失败: {str(e)}")
                return False
        return True

    def send_message(self, message):
        """发送消息并获取响应"""
        try:
            # 添加用户消息到历史记录
            self.chat_history.append({
                'role': 'user',
                'content': message,
                'timestamp': datetime.now().isoformat()
            })
            
            # 准备请求数据
            messages = [{'role': msg['role'], 'content': msg['content']} for msg in self.chat_history]
            
            # 调用Ollama API
            response = ollama.chat(
                model=self.model_name,
                messages=messages,
                options={
                    'temperature': 0.7,  # 控制随机性
                    'top_p': 0.9,       # 控制多样性
                }
            )
            
            # 获取AI回复
            ai_response = response['message']['content']
            
            # 添加AI回复到历史记录
            self.chat_history.append({
                'role': 'assistant',
                'content': ai_response,
                'timestamp': datetime.now().isoformat()
            })
            
            return ai_response
            
        except Exception as e:
            error_msg = f"发生错误: {str(e)}"
            st.error(error_msg)
            return error_msg

    def send_message_stream(self, message, on_chunk_callback=None):
        """发送消息并以流式方式获取响应"""
        try:
            # 添加用户消息到历史记录
            self.chat_history.append({
                'role': 'user',
                'content': message,
                'timestamp': datetime.now().isoformat()
            })
            
            # 准备请求数据
            messages = [{'role': msg['role'], 'content': msg['content']} for msg in self.chat_history]
            
            # 调用Ollama流式API
            full_response = ""
            for chunk in ollama.chat(
                model=self.model_name,
                messages=messages,
                options={
                    'temperature': 0.7,  # 控制随机性
                    'top_p': 0.9,       # 控制多样性
                },
                stream=True
            ):
                if 'message' in chunk and 'content' in chunk['message']:
                    chunk_content = chunk['message']['content']
                    full_response += chunk_content
                    
                    # 如果提供了回调函数，则调用它
                    if on_chunk_callback:
                        on_chunk_callback(chunk_content)
            
            # 添加AI回复到历史记录
            self.chat_history.append({
                'role': 'assistant',
                'content': full_response,
                'timestamp': datetime.now().isoformat()
            })
            
            return full_response
            
        except Exception as e:
            error_msg = f"发生错误: {str(e)}"
            st.error(error_msg)
            return error_msg

    def reset_chat(self):
        """重置聊天历史"""
        self.chat_history = []

    def get_chat_history_json(self):
        """获取JSON格式的聊天历史"""
        return json.dumps(self.chat_history, ensure_ascii=False, indent=2)


def main():
    """主界面函数"""
    st.title("🤖 本地大模型聊天系统 (基于Ollama)")
    st.caption("使用 qwen3:4b 模型进行对话")
    
    # 初始化聊天实例
    if 'ollama_chat' not in st.session_state:
        st.session_state.ollama_chat = OllamaChat("qwen3:4b")
    
    chat = st.session_state.ollama_chat
    
    # 检查模型可用性
    is_available, available_models = chat.check_model_available()
    
    if not is_available:
        st.warning(f"⚠️ 模型 {chat.model_name} 未安装或不可用")
        col1, col2 = st.columns([3, 1])
        with col1:
            model_input = st.text_input("输入要使用的模型名称:", value=chat.model_name)
        with col2:
            if st.button("🔄 切换模型"):
                chat.model_name = model_input
                st.rerun()
        
        if st.button("📥 拉取模型", type="primary"):
            success = chat.pull_model_if_needed()
            if success:
                st.rerun()
    else:
        st.success(f"✅ 模型 {chat.model_name} 可用")
    
    # 聊天界面
    if is_available or chat.check_model_available()[0]:
        # 显示聊天历史
        if chat.chat_history:
            st.subheader("💬 聊天记录")
            for msg in chat.chat_history:
                if msg['role'] == 'user':
                    st.markdown(f"**👤 您:** {msg['content']}")
                else:
                    st.markdown(f"**🤖 AI:** {msg['content']}")
                st.markdown("---")
        
        # 输入区域
        st.subheader("📝 发送消息")
        user_input = st.text_area("输入您的消息:", height=100, key="user_input")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📤 发送", type="primary"):
                if user_input.strip():
                    with st.spinner("AI正在思考..."):
                        response = chat.send_message(user_input)
                    st.success("消息已发送!")
                    st.rerun()
                else:
                    st.warning("请输入有效消息!")
        
        with col2:
            if st.button("🗑️ 清空聊天"):
                chat.reset_chat()
                st.success("聊天历史已清空!")
                st.rerun()
        
        with col3:
            if st.button("💾 导出聊天记录"):
                if chat.chat_history:
                    chat_json = chat.get_chat_history_json()
                    st.download_button(
                        label="📥 下载JSON",
                        data=chat_json,
                        file_name=f"chat_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )
                else:
                    st.warning("没有聊天记录可导出!")


if __name__ == "__main__":
    main()