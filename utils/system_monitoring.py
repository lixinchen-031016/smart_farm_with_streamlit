from datetime import datetime

import psutil
import streamlit as st


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

    # 新增日志观察与下载功能
    with st.expander("📜 操作日志观察", expanded=True):
        st.subheader("日志观察")
        
        # 添加时间范围选择
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("选择开始日期")
        with col2:
            end_date = st.date_input("选择结束日期")
        
        # 读取日志文件
        try:
            with open('operation_log.log', 'r') as f:
                logs = f.readlines()
            
            # 过滤指定时间范围的日志
            filtered_logs = []
            for log in logs:
                log_time_str = log.split(' - ')[0]
                log_time = datetime.strptime(log_time_str, '%Y-%m-%d %H:%M:%S').date()
                if start_date <= log_time <= end_date:
                    filtered_logs.append(log)
            
            # 显示日志内容
            st.code(''.join(filtered_logs), language='log')
            
            # 下载日志功能
            if filtered_logs:
                log_content = ''.join(filtered_logs)
                st.download_button(
                    label="下载选定日志",
                    data=log_content,
                    file_name=f'logs_{start_date}_{end_date}.log',
                    mime='text/plain'
                )
            else:
                st.warning("选定时间范围内无日志记录")
                
        except FileNotFoundError:
            st.error("日志文件不存在，请先进行操作生成日志")
