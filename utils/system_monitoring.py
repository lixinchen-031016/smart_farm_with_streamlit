from datetime import datetime

import psutil
import streamlit as st
from streamlit_extras.metric_cards import style_metric_cards  # 添加卡片样式库


def system_monitoring():
    if not st.session_state.get('logged_in') or st.session_state['role'] != 'admin':
        st.experimental_set_query_params(page="login")
        return

    # 添加卡片样式
    st.markdown("""
    <style>
    .metric-card {
        background: rgba(255, 255, 255, 0.9) !important;
        border-radius: 12px !important;
        padding: 1.5rem !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
        transition: transform 0.3s ease;
    }
    .metric-card:hover {
        transform: translateY(-5px);
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("🖥️ 系统监控")
    st.write("服务器资源使用情况：")

    # 获取资源使用数据
    cpu_usage = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    # 使用卡片布局展示核心指标
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="💻 CPU 使用率", value=f"{cpu_usage}%",
                 delta="正常" if cpu_usage < 70 else "过高",
                 help="建议保持低于70%")
    with col2:
        st.metric(label="🧠 内存使用率", value=f"{memory.percent}%",
                 delta="正常" if memory.percent < 80 else "过高",
                 help="建议保持低于80%")
    with col3:
        st.metric(label="💾 磁盘使用率", value=f"{disk.percent}%",
                 delta="正常" if disk.percent < 85 else "过高",
                 help="建议保持低于85%")
    
    # 应用卡片样式
    style_metric_cards(background_color="#FFFFFF", border_color="#E0E0E0",
                       border_left_color="#4CAF50", box_shadow=True)
    
    # 详细资源信息展示
    with st.expander("📊 详细资源信息", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="已用内存", value=f"{memory.used / (1024 ** 3):.2f} GB")
            st.metric(label="可用内存", value=f"{memory.available / (1024 ** 3):.2f} GB")
        with col2:
            st.metric(label="已用磁盘空间", value=f"{disk.used / (1024 ** 3):.2f} GB")
            st.metric(label="可用磁盘空间", value=f"{disk.free / (1024 ** 3):.2f} GB")
    
    # 添加资源使用趋势图
    st.subheader("📈 资源使用趋势")
    col1, col2 = st.columns(2)
    with col1:
        st.line_chart([psutil.cpu_percent(interval=1) for _ in range(10)], height=200)
        st.caption("CPU 使用率趋势")
    with col2:
        st.line_chart([psutil.virtual_memory().percent for _ in range(10)], height=200)
        st.caption("内存使用率趋势")

    # 修改后的日志观察功能
    with st.expander("📜 操作日志观察", expanded=True):
        st.subheader("日志观察")
        
        # 添加时间范围选择
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("选择开始日期")
        with col2:
            end_date = st.date_input("选择结束日期")
        
        # 从数据库查询日志
        try:
            from models import OperationLog
            from utils.database import get_session
            session = get_session()
            
            # 转换日期格式并查询
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())
            
            logs = session.query(OperationLog).filter(
                OperationLog.log_time >= start_datetime,
                OperationLog.log_time <= end_datetime
            ).order_by(OperationLog.log_time.desc()).all()
            
            # 格式化日志内容
            filtered_logs = []
            for log in logs:
                log_entry = f"{log.log_time.strftime('%Y-%m-%d %H:%M:%S')} - {log.log_level} - User: {log.username}, Action: {log.action_type}, Details: {log.action_details}"
                filtered_logs.append(log_entry + '\n')
            
            # 显示日志内容
            if filtered_logs:
                st.code(''.join(filtered_logs), language='log')
                
                # 下载日志功能
                log_content = ''.join(filtered_logs)
                st.download_button(
                    label="下载选定日志",
                    data=log_content,
                    file_name=f'logs_{start_date}_{end_date}.log',
                    mime='text/plain'
                )
            else:
                st.warning("选定时间范围内无日志记录")
                
        except Exception as e:
            st.error(f"数据库查询失败: {str(e)}")
        finally:
            session.close()
