from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from sqlalchemy.orm import load_only
from models import OperationLog
from utils.database import get_session


class LogAnalyzer:
    def get_error_stats(self, hours=24):
        """获取错误统计信息"""
        with get_session() as session:
            since = datetime.now() - timedelta(hours=hours)
            errors = session.query(OperationLog).options(
                load_only(
                    OperationLog.log_time,
                    OperationLog.log_level,
                    OperationLog.username,
                    OperationLog.action_type,
                    OperationLog.action_details
                )
            ).filter(
                OperationLog.log_time >= since,
                OperationLog.log_level == 'ERROR'
            ).all()

            error_counts = {}
            for error in errors:
                action_type = error.action_type
                error_counts[action_type] = error_counts.get(action_type, 0) + 1

            return error_counts

    def get_user_activity(self, hours=24):
        """获取用户活动统计"""
        with get_session() as session:
            since = datetime.now() - timedelta(hours=hours)
            logs = session.query(OperationLog).options(
                load_only(
                    OperationLog.log_time,
                    OperationLog.log_level,
                    OperationLog.username,
                    OperationLog.action_type,
                    OperationLog.action_details
                )
            ).filter(
                OperationLog.log_time >= since
            ).all()

            user_activities = {}
            for log in logs:
                username = log.username
                if username not in user_activities:
                    user_activities[username] = {
                        'total_actions': 0,
                        'error_actions': 0
                    }
                user_activities[username]['total_actions'] += 1
                if log.log_level == 'ERROR':
                    user_activities[username]['error_actions'] += 1

            return user_activities

    def get_log_trends(self, days=7):
        """获取日志趋势数据"""
        with get_session() as session:
            since = datetime.now() - timedelta(days=days)
            logs = session.query(OperationLog).options(
                load_only(
                    OperationLog.log_time,
                    OperationLog.log_level,
                    OperationLog.username,
                    OperationLog.action_type,
                    OperationLog.action_details
                )
            ).filter(
                OperationLog.log_time >= since
            ).all()

            # 按日期和日志级别统计
            daily_stats = {}
            for log in logs:
                date_key = log.log_time.date()
                level = log.log_level

                if date_key not in daily_stats:
                    daily_stats[date_key] = {}

                if level not in daily_stats[date_key]:
                    daily_stats[date_key][level] = 0

                daily_stats[date_key][level] += 1

            return daily_stats

    def get_top_actions(self, limit=10, hours=24):
        """获取最常见的操作类型"""
        with get_session() as session:
            since = datetime.now() - timedelta(hours=hours)
            logs = session.query(OperationLog).options(
                load_only(
                    OperationLog.log_time,
                    OperationLog.log_level,
                    OperationLog.username,
                    OperationLog.action_type,
                    OperationLog.action_details
                )
            ).filter(
                OperationLog.log_time >= since
            ).all()

            action_counts = {}
            for log in logs:
                action = log.action_type
                action_counts[action] = action_counts.get(action, 0) + 1

            # 按次数排序并返回前N个
            sorted_actions = sorted(action_counts.items(), key=lambda x: x[1], reverse=True)
            return sorted_actions[:limit]

    def close(self):
        """关闭数据库会话"""
        # 由于使用上下文管理器，不需要手动关闭会话
        pass


def show_log_analysis():
    """显示日志分析页面"""
    if not st.session_state.get('logged_in') or st.session_state['role'] != 'admin':
        st.experimental_set_query_params(page="login")
        return

    st.title("📊 日志分析与聚合")

    analyzer = LogAnalyzer()

    try:
        # 时间范围选择
        analysis_period = st.selectbox(
            "选择分析周期",
            ["最近24小时", "最近7天", "最近30天"],
            index=0
        )

        # 将选择转换为小时数
        hours_map = {
            "最近24小时": 24,
            "最近7天": 24 * 7,
            "最近30天": 24 * 30
        }
        hours = hours_map[analysis_period]
        days = hours // 24

        # 创建分析选项卡
        tab1, tab2, tab3, tab4 = st.tabs([
            "错误统计",
            "用户活动",
            "日志趋势",
            "操作分析"
        ])

        with tab1:
            st.subheader("错误统计")
            error_stats = analyzer.get_error_stats(hours=hours)

            if error_stats:
                # 转换为DataFrame以便显示
                error_df = pd.DataFrame([
                    {"操作类型": action, "错误次数": count}
                    for action, count in error_stats.items()
                ]).sort_values("错误次数", ascending=False)

                st.dataframe(error_df)

                # 显示图表
                if not error_df.empty:
                    st.bar_chart(error_df.set_index("操作类型"))
            else:
                st.info("在选定的时间范围内没有发现错误日志")

        with tab2:
            st.subheader("用户活动统计")
            user_activities = analyzer.get_user_activity(hours=hours)

            if user_activities:
                # 转换为DataFrame以便显示
                activity_data = []
                for user, stats in user_activities.items():
                    activity_data.append({
                        "用户": user,
                        "总操作数": stats['total_actions'],
                        "错误操作数": stats['error_actions'],
                        "错误率(%)": round((stats['error_actions'] / stats['total_actions'] * 100), 2) if stats[
                                                                                                              'total_actions'] > 0 else 0
                    })

                activity_df = pd.DataFrame(activity_data).sort_values("总操作数", ascending=False)
                st.dataframe(activity_df)

                # 显示图表
                chart_data = activity_df.set_index("用户")[["总操作数", "错误操作数"]]
                st.bar_chart(chart_data)
            else:
                st.info("在选定的时间范围内没有用户活动日志")

        with tab3:
            st.subheader("日志趋势分析")
            log_trends = analyzer.get_log_trends(days=days)

            if log_trends:
                # 转换为DataFrame以便显示
                trend_data = []
                for date, levels in log_trends.items():
                    row = {"日期": date}
                    row.update(levels)
                    trend_data.append(row)

                trend_df = pd.DataFrame(trend_data).sort_values("日期")
                trend_df = trend_df.fillna(0)  # 填充缺失值

                st.dataframe(trend_df)

                # 显示图表（排除日期列）
                chart_df = trend_df.set_index("日期")
                st.line_chart(chart_df)
            else:
                st.info("在选定的时间范围内没有日志趋势数据")

        with tab4:
            st.subheader("热门操作分析")
            top_actions = analyzer.get_top_actions(limit=10, hours=hours)

            if top_actions:
                action_df = pd.DataFrame([
                    {"操作类型": action, "出现次数": count}
                    for action, count in top_actions
                ])

                st.dataframe(action_df)

                # 显示图表
                st.bar_chart(action_df.set_index("操作类型"))
            else:
                st.info("在选定的时间范围内没有操作日志")

    except Exception as e:
        st.error(f"日志分析过程中发生错误: {str(e)}")
    finally:
        analyzer.close()
