import streamlit as st
from utils.logger import log_operation
def restore_ui(username):
    """
    处理数据恢复的用户界面逻辑
    """
    uploaded_sql_file = st.file_uploader("选择加密的SQL备份文件", type=["encrypted"])
    uploaded_key_file = st.file_uploader("选择密钥文件", type=["txt"])

    if uploaded_sql_file is not None and uploaded_key_file is not None:
        if st.button("恢复数据"):
            try:
                key = uploaded_key_file.read().decode('utf-8').strip()
                if not key:
                    raise ValueError("密钥文件为空或无效")
                log_operation(username, "ERROR", "数据恢复失败", f"文件: {uploaded_key_file}")
                
                from utils.backup import restore_data
                restore_data(uploaded_sql_file, key)
                
                log_operation(username, "INFO", "数据恢复", f"文件: {uploaded_sql_file.name}")
                st.success("数据已恢复")
            except Exception as e:
                st.error(f"恢复数据时出错: {e}")
                log_operation(username, "ERROR", "数据恢复失败", f"文件: {uploaded_sql_file.name}")