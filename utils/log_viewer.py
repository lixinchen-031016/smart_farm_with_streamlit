import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy.orm import Session

from sqlalchemy.orm import load_only
from models import OperationLog
from utils.database import get_session


def show_log_viewer():
    """显示日志查看器页面 - 增强版

    提供智能日志分析平台，支持时间范围选择、关键词搜索、高级过滤、
    统计分析、操作链追踪和异常告警等功能，帮助用户快速定位和分析系统运行情况。

    Returns:
        None: 无返回值，直接在Streamlit页面上显示内容

    Raises:
        Exception: 数据库查询失败时会捕获并显示错误信息

    Examples:
        >>> show_log_viewer()
        # 会在Streamlit页面上显示完整的日志分析平台界面
    """
    if not st.session_state.get('logged_in'):
        st.query_params.page = "login"
        st.rerun()
        return

    st.title("📜 智能日志分析平台")
    
    # 侧边栏控制面板
    with st.sidebar:
        st.header("🎛️ 控制面板")
        
        # 快捷时间选择
        st.subheader("⏱️ 快捷时间范围")
        if st.button("最近 1 小时"):
            st.session_state.time_range = "1h"
        if st.button("最近 6 小时"):
            st.session_state.time_range = "6h"
        if st.button("最近 24 小时"):
            st.session_state.time_range = "24h"
        if st.button("最近 7 天"):
            st.session_state.time_range = "7d"
        if st.button("自定义范围"):
            st.session_state.time_range = "custom"
        
        # 获取时间范围设置
        time_range = st.session_state.get('time_range', '24h')
        
        if time_range == "custom":
            start_date = st.date_input("开始日期", value=datetime.now() - timedelta(days=7))
            end_date = st.date_input("结束日期", value=datetime.now())
        else:
            # 根据快捷选择计算日期
            now = datetime.now()
            if time_range == "1h":
                start_date = now - timedelta(hours=1)
            elif time_range == "6h":
                start_date = now - timedelta(hours=6)
            elif time_range == "24h":
                start_date = now - timedelta(days=1)
            elif time_range == "7d":
                start_date = now - timedelta(days=7)
            end_date = now

    # 主界面布局
    # 第一行：搜索和过滤
    st.header("🔍 搜索与过滤")
    
    # 搜索框 - 支持关键词和正则表达式
    search_col, regex_col = st.columns([3, 1])
    with search_col:
        search_query = st.text_input("🔎 搜索关键词", placeholder="输入关键词或多个关键词 (空格分隔)")
    with regex_col:
        use_regex = st.checkbox("正则表达式", value=False)
    
    # 高级过滤选项
    with st.expander("⚙️ 高级过滤选项"):
        filter_col1, filter_col2, filter_col3 = st.columns(3)
        with filter_col1:
            log_level = st.selectbox("日志级别", ["ALL", "INFO", "WARNING", "ERROR", "DEBUG"], index=0)
        with filter_col2:
            selected_user = st.selectbox("用户", ["ALL"], index=0)  # 将在下面动态更新
        with filter_col3:
            action_type = st.selectbox("操作类型", ["ALL", "登录", "查询", "修改", "删除", "备份", "恢复"], index=0)
        
        # 布尔搜索选项
        boolean_search = st.radio("搜索模式", ["AND (且)", "OR (或)", "EXACT (精确)"], horizontal=True)

    # 从数据库查询日志
    try:
        with get_session() as session:
            # 转换日期格式并查询
            if isinstance(start_date, datetime):
                start_datetime = start_date
                end_datetime = end_date
            else:
                start_datetime = datetime.combine(start_date, datetime.min.time())
                end_datetime = datetime.combine(end_date, datetime.max.time())

            # 构建基础查询，只加载需要的字段，排除计算字段details_json
            query = session.query(OperationLog).options(
                load_only(
                    OperationLog.id,
                    OperationLog.log_time,
                    OperationLog.log_level,
                    OperationLog.username,
                    OperationLog.action_type,
                    OperationLog.action_details
                )
            ).filter(
                OperationLog.log_time >= start_datetime,
                OperationLog.log_time <= end_datetime
            )

            # 添加日志级别过滤
            if log_level != "ALL":
                query = query.filter(OperationLog.log_level == log_level)

            # 添加用户过滤
            if selected_user != "ALL":
                query = query.filter(OperationLog.username == selected_user)
            
            # 添加操作类型过滤
            if action_type != "ALL":
                query = query.filter(OperationLog.action_type.contains(action_type))

            # 获取所有日志用于后续处理
            logs = query.order_by(OperationLog.log_time.desc()).all()
            
            # 动态更新用户列表
            all_users = session.query(OperationLog.username).distinct().all()
            user_list = ["ALL"] + [user[0] for user in all_users]
            if selected_user not in user_list:
                selected_user = "ALL"
        
        # 关键词搜索和过滤
        filtered_logs = []
        if search_query:
            for log in logs:
                log_text = f"{log.action_type} {log.action_details} {log.username}"
                
                if use_regex:
                    # 正则表达式搜索
                    try:
                        if re.search(search_query, log_text, re.IGNORECASE):
                            filtered_logs.append(log)
                    except re.error:
                        st.error(f"正则表达式错误：{search_query}")
                        filtered_logs = logs
                        break
                else:
                    # 布尔搜索
                    keywords = search_query.split()
                    if "AND" in st.radio("", ["AND", "OR", "EXACT"], index=0, key="bool_mode"):
                        # AND 模式：所有关键词都要匹配
                        if all(kw.lower() in log_text.lower() for kw in keywords):
                            filtered_logs.append(log)
                    elif "OR":
                        # OR 模式：任一关键词匹配即可
                        if any(kw.lower() in log_text.lower() for kw in keywords):
                            filtered_logs.append(log)
                    else:
                        # EXACT 模式：精确匹配整个短语
                        if search_query.lower() in log_text.lower():
                            filtered_logs.append(log)
        else:
            filtered_logs = logs

        # 第二行：日志统计和可视化
        if filtered_logs:
            # 标签页展示不同视图
            tab1, tab2, tab3, tab4 = st.tabs(["📋 日志详情", "📊 统计分析", "🔗 操作链追踪", "⚠️ 异常告警"])
            
            with tab1:
                # 日志详情展示
                st.subheader(f"找到 {len(filtered_logs)} 条日志记录")
                
                # 关键词高亮显示
                if search_query and not use_regex:
                    def highlight_keywords(text, keywords):
                        for keyword in keywords:
                            text = re.sub(
                                f'({re.escape(keyword)})',
                                r'**\1**',
                                text,
                                flags=re.IGNORECASE
                            )
                        return text
                    
                    # 格式化并高亮日志
                    formatted_logs = []
                    for log in filtered_logs:
                        log_text = f"{log.log_time.strftime('%Y-%m-%d %H:%M:%S')} - {log.log_level} - 用户：{log.username}, 操作：{log.action_type}, 详情：{log.action_details}"
                        highlighted_text = highlight_keywords(log_text, search_query.split())
                        formatted_logs.append(highlighted_text)
                    
                    # 显示高亮后的日志
                    st.markdown('\n'.join(formatted_logs[:100]), unsafe_allow_html=True)  # 限制显示前 100 条
                    
                    if len(filtered_logs) > 100:
                        st.info(f"仅显示前 100 条，共 {len(filtered_logs)} 条")
                else:
                    # 普通显示
                    formatted_logs = [
                        f"{log.log_time.strftime('%Y-%m-%d %H:%M:%S')} - {log.log_level} - 用户：{log.username}, 操作：{log.action_type}, 详情：{log.action_details}"
                        for log in filtered_logs
                    ]
                    st.code('\n'.join(formatted_logs[:100]), language='log')
                
                # 下载日志
                log_content = '\n'.join(formatted_logs)
                st.download_button(
                    label="💾 下载选定日志",
                    data=log_content,
                    file_name=f'logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log',
                    mime='text/plain'
                )
            
            with tab2:
                # 统计分析
                st.header("📈 日志统计分析")
                
                # 按级别统计
                level_counts = Counter([log.log_level for log in filtered_logs])
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("日志级别分布")
                    fig_level = px.pie(
                        values=list(level_counts.values()),
                        names=list(level_counts.keys()),
                        title="日志级别占比"
                    )
                    st.plotly_chart(fig_level, use_container_width=True)
                
                with col2:
                    st.subheader("级别统计")
                    for level, count in sorted(level_counts.items(), key=lambda x: x[1], reverse=True):
                        st.metric(level, count)
                
                # 按时间趋势统计
                st.subheader("📅 日志时间趋势")
                logs_df = pd.DataFrame([
                    {'timestamp': log.log_time, 'level': log.log_level}
                    for log in filtered_logs
                ])
                
                if not logs_df.empty:
                    logs_df.set_index('timestamp', inplace=True)
                    hourly_counts = logs_df.resample('H').size()
                    
                    fig_trend = px.area(
                        x=hourly_counts.index,
                        y=hourly_counts.values,
                        title="每小时日志数量趋势",
                        labels={'x': '时间', 'y': '日志数量'}
                    )
                    st.plotly_chart(fig_trend, use_container_width=True)
                
                # 用户活跃度统计
                st.subheader("👥 用户活跃度 Top10")
                user_counts = Counter([log.username for log in filtered_logs])
                top_users = user_counts.most_common(10)
                
                fig_user = px.bar(
                    x=[count for user, count in top_users],
                    y=[user for user, count in top_users],
                    orientation='h',
                    title="用户操作频率 Top10"
                )
                st.plotly_chart(fig_user, use_container_width=True)
                
                # 操作类型统计
                st.subheader("🔧 操作类型分布")
                action_counts = Counter([log.action_type for log in filtered_logs])
                fig_action = px.pie(
                    values=list(action_counts.values()),
                    names=list(action_counts.keys()),
                    title="操作类型分布"
                )
                st.plotly_chart(fig_action, use_container_width=True)
                
                # 错误类型 Top10
                error_logs = [log for log in filtered_logs if log.log_level == 'ERROR']
                if error_logs:
                    st.subheader("❌ 高频错误 Top10")
                    error_messages = [log.action_details for log in error_logs]
                    error_counter = Counter(error_messages)
                    top_errors = error_counter.most_common(10)
                    
                    for i, (error, count) in enumerate(top_errors, 1):
                        st.error(f"Top{i}: {error[:100]}... (出现 {count} 次)")
            
            with tab3:
                # 操作链追踪
                st.header("🔗 操作链追踪")
                st.info("通过分析用户的连续操作，追踪完整的操作流程")
                
                # 按用户分组
                user_logs = defaultdict(list)
                for log in filtered_logs:
                    user_logs[log.username].append(log)
                
                # 选择要追踪的用户
                selected_track_user = st.selectbox("选择要追踪的用户", list(user_logs.keys()))
                
                if selected_track_user:
                    st.subheader(f"👤 {selected_track_user} 的操作链")
                    
                    user_log_list = sorted(user_logs[selected_track_user], key=lambda x: x.log_time)
                    
                    # 显示时间线
                    timeline_data = []
                    for i, log in enumerate(user_log_list):
                        timeline_data.append({
                            '时间': log.log_time.strftime('%H:%M:%S'),
                            '级别': log.log_level,
                            '操作': log.action_type,
                            '详情': log.action_details[:50] + '...' if len(log.action_details) > 50 else log.action_details
                        })
                    
                    timeline_df = pd.DataFrame(timeline_data)
                    st.dataframe(timeline_df, use_container_width=True)
                    
                    # 检测异常操作序列
                    st.subheader("⚠️ 潜在风险操作检测")
                    risk_patterns = ['删除', '修改', '恢复', '备份']
                    risky_logs = [log for log in user_log_list if any(pattern in log.action_type for pattern in risk_patterns)]
                    
                    if risky_logs:
                        for log in risky_logs[-5:]:  # 显示最近 5 条风险操作
                            st.warning(f"{log.log_time.strftime('%H:%M:%S')} - {log.action_type}: {log.action_details}")
                    else:
                        st.success("未检测到高风险操作")
            
            with tab4:
                # 异常告警
                st.header("⚠️ 日志告警监控")
                
                # 实时错误率计算
                total_logs = len(filtered_logs)
                error_count = len([log for log in filtered_logs if log.log_level == 'ERROR'])
                warning_count = len([log for log in filtered_logs if log.log_level == 'WARNING'])
                
                error_rate = (error_count / total_logs * 100) if total_logs > 0 else 0
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("错误率", f"{error_rate:.2f}%", delta=f"{error_count} 个错误")
                with col2:
                    st.metric("警告数", warning_count)
                with col3:
                    st.metric("总日志数", total_logs)
                
                # 告警阈值设置
                st.subheader("🔔 告警配置")
                alert_threshold = st.slider("错误率告警阈值 (%)", 0, 100, 10)
                
                if error_rate > alert_threshold:
                    st.error(f"⚠️ **警告**: 当前错误率 {error_rate:.2f}% 超过阈值 {alert_threshold}%")
                    
                    # 显示最近的错误日志
                    st.subheader("最近错误详情")
                    recent_errors = [log for log in filtered_logs if log.log_level == 'ERROR'][-10:]
                    for err in recent_errors:
                        st.error(f"{err.log_time.strftime('%H:%M:%S')} - {err.action_details}")
                else:
                    st.success(f"✅ 系统运行正常，错误率 {error_rate:.2f}% 低于阈值 {alert_threshold}%")
                
                # 异常时间段检测
                st.subheader("📊 异常时间段分析")
                if logs_df is not None and not logs_df.empty:
                    # logs_df 已经设置 timestamp 为索引，直接使用 resample
                    error_df = logs_df[logs_df['level'] == 'ERROR'].copy()
                    if not error_df.empty:
                        hourly_error_counts = error_df.resample('H').size()
                        
                        if hourly_error_counts.max() > 0:
                            peak_hour = hourly_error_counts.idxmax()
                            st.warning(f"⚠️ 错误高发时段：{peak_hour.strftime('%Y-%m-%d %H:00')}")
        else:
            st.warning("选定时间范围内无日志记录")

    except Exception as e:
        st.error(f"数据库查询失败: {str(e)}")
