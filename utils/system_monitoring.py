import streamlit as st
import psutil
def system_monitoring():
    if not st.session_state.get('logged_in') or st.session_state['role'] != 'admin':
        st.experimental_set_query_params(page="login")
        return

    st.title("系统监控")
    st.write("服务器资源使用情况：")

    # 获取CPU使用情况
    cpu_usage = psutil.cpu_percent(interval=1)
    st.write(f"CPU 使用率: {cpu_usage}%")

    # 获取内存使用情况
    memory = psutil.virtual_memory()
    st.write(f"内存使用率: {memory.percent}%")
    st.write(f"已用内存: {memory.used / (1024 ** 3):.2f} GB")
    st.write(f"可用内存: {memory.available / (1024 ** 3):.2f} GB")

    # 获取磁盘使用情况
    disk = psutil.disk_usage('/')
    st.write(f"磁盘使用率: {disk.percent}%")
    st.write(f"已用磁盘空间: {disk.used / (1024 ** 3):.2f} GB")
    st.write(f"可用磁盘空间: {disk.free / (1024 ** 3):.2f} GB")