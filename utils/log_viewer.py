from datetime import datetime

import streamlit as st
from sqlalchemy.orm import Session

from models import OperationLog
from utils.database import get_session


def show_log_viewer():
    """显示日志查看器页面"""
    if not st.session_state.get('logged_in') or st.session_state['role'] != 'admin':
        st.experimental_set_query_params(page="login")
        return

    st.title("📜 操作日志查看器")
    
    # 添加时间范围选择
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("选择开始日期")
    with col2:
        end_date = st.date_input("选择结束日期")
    
    # 添加日志级别过滤
    log_level = st.selectbox("选择日志级别", ["ALL", "INFO", "WARNING", "ERROR", "DEBUG"], index=0)
    
    # 添加用户过滤
    try:
        session: Session = get_session()
        users = session.query(OperationLog.username).distinct().all()
        user_list = ["ALL"] + [user[0] for user in users]
        session.close()
    except:
        user_list = ["ALL"]
    
    selected_user = st.selectbox("选择用户", user_list, index=0)
    
    # 从数据库查询日志
    try:
        session: Session = get_session()
        # 转换日期格式并查询
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
        
        # 构建查询
        query = session.query(OperationLog).filter(
            OperationLog.log_time >= start_datetime,
            OperationLog.log_time <= end_datetime
        )
        
        # 添加日志级别过滤
        if log_level != "ALL":
            query = query.filter(OperationLog.log_level == log_level)
            
        # 添加用户过滤
        if selected_user != "ALL":
            query = query.filter(OperationLog.username == selected_user)
        
        logs = query.order_by(OperationLog.log_time.desc()).all()
        
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
            
            # 显示日志统计信息
            st.subheader("日志统计")
            st.write(f"总共找到 {len(logs)} 条日志记录")
            
            # 按级别统计
            level_counts = {}
            for log in logs:
                level = log.log_level
                level_counts[level] = level_counts.get(level, 0) + 1
            
            st.write("按级别统计:")
            for level, count in level_counts.items():
                st.write(f"- {level}: {count}")
        else:
            st.warning("选定时间范围内无日志记录")
            
    except Exception as e:
        st.error(f"数据库查询失败: {str(e)}")
    finally:
        session.close()