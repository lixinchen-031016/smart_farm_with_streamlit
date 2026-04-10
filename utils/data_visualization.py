import json

import numpy as np
import pandas as pd
import plotly
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

from utils.enhanced_visualization import create_smart_chart_recommendation, create_dual_axis_chart, \
    create_multi_subplot_chart
from utils.visualization import visualize_data


# 函数：数据可视化
def data_visualization():
    """显示数据可视化页面，允许用户创建各种图表

    提供智能数据可视化功能，支持基础图表和高级图表的创建，
    包括散点图、线图、柱状图、箱线图、直方图、饼图、热力图、双轴图和多子图等，
    并提供智能推荐和图表解读功能。

    Returns:
        None: 无返回值，直接在Streamlit页面上显示内容

    Raises:
        Exception: 数据处理或图表生成过程中出现错误时会捕获并显示错误信息

    Examples:
        >>> data_visualization()
        # 会在Streamlit页面上显示数据可视化界面
    """
    if not st.session_state.get('logged_in'):
        st.query_params.page = "login"
        return

    st.title("数据可视化")
    if 'data' not in st.session_state:
        st.warning("请先在数据概览页面上传数据")
        return

    data = st.session_state['data']

    # 添加标签页以组织复杂功能
    tab1, tab2 = st.tabs(["📊 智能可视化", "📈 详细图表"])

    with tab1:
        # 动态参数调节面板
        has_timestamp = 'timestamp' in data.columns
        is_from_database = st.session_state.get('data_source', '') == "从数据库读取"

        # 仅在有时间戳列时显示时间范围选择器
        if has_timestamp:
            st.subheader("时间范围筛选")
            start_time = st.date_input("选择开始时间")
            end_time = st.date_input("选择结束时间")
            filtered_data = data[
                (data['timestamp'] >= pd.Timestamp(start_time)) &
                (data['timestamp'] <= pd.Timestamp(end_time))]
        else:
            filtered_data = data
            st.info("当前数据没有时间戳列，将使用全部数据进行可视化")

        # 数据质量检查
        st.subheader("数据质量检查")
        missing_values = filtered_data.isnull().sum().sum()
        duplicate_rows = filtered_data.duplicated().sum()

        col1, col2 = st.columns(2)
        with col1:
            st.metric("缺失值", missing_values)
        with col2:
            st.metric("重复行", duplicate_rows)

        if missing_values > 0:
            st.warning(f"⚠️ 检测到 {missing_values} 个缺失值，可能影响可视化效果")
        if duplicate_rows > 0:
            st.warning(f"⚠️ 检测到 {duplicate_rows} 个重复行，建议先进行数据清洗")

        # 智能推荐图表类型
        numeric_columns = filtered_data.select_dtypes(include=['float64', 'int64']).columns
        categorical_columns = filtered_data.select_dtypes(include=['object']).columns

        st.subheader("智能推荐")
        if len(numeric_columns) >= 2:
            st.info("💡 检测到多个数值型变量，推荐使用散点图探索变量间关系")
        elif len(numeric_columns) == 1 and len(categorical_columns) >= 1:
            st.info("💡 检测到数值型和分类型变量，推荐使用柱状图或箱线图进行比较分析")
        elif len(categorical_columns) >= 1 and 'timestamp' in filtered_data.columns:
            st.info("💡 检测到时间序列数据，推荐使用线图展示趋势变化")
        else:
            st.info("💡 根据当前数据特征，推荐使用直方图查看数据分布")

        # 设置统一的主题
        pio.templates.default = "plotly_white"
        color_sequence = px.colors.qualitative.Plotly

        # 添加高级可视化选项卡
        basic_tab, advanced_tab = st.tabs(["📊 基础图表", "🚀 高级图表"])

        with basic_tab:
            # 智能推荐图表类型
            if 'data' in st.session_state and len(st.session_state['data']) > 0:
                rec_result = create_smart_chart_recommendation(filtered_data)
                if rec_result[0] is not None:  # 检查是否成功返回推荐
                    rec_chart, rec_params, rec_reason = rec_result
                    with st.expander(f"💡 智能推荐：{rec_chart}", expanded=True):
                        st.markdown(f"**推荐理由**: {rec_reason}")
                        if rec_params.get('x_column'):
                            st.code(f"X 轴：{rec_params['x_column']}, Y 轴：{rec_params.get('y_column', 'N/A')}")

            # 图表类型说明
            with st.expander("📊 图表类型说明"):
                st.markdown("""
                **常用图表类型适用场景:**
                - **散点图**: 展示两个数值变量之间的关系
                - **线图**: 展示数据随时间的变化趋势
                - **柱状图**: 比较不同类别的数值大小
                - **箱线图**: 展示数据分布和异常值
                - **直方图**: 展示单个数值变量的分布情况
                - **饼图**: 展示各类别占比情况
                - **热力图**: 展示矩阵数据或相关性分析
                """)

            chart_type = st.selectbox("选择图表类型", ["散点图", "线图", "柱状图", "箱线图", "直方图", "饼图", "热力图"])

        if len(numeric_columns) == 0:
            st.warning("数据集中没有数值列，无法进行可视化。")
            return

        x_column = None
        y_column = None
        color_column = None
        column = None

        if chart_type in ["散点图", "线图", "柱状图"]:
            x_column = st.selectbox("选择X轴", filtered_data.columns)
            y_column = st.selectbox("选择Y轴", numeric_columns)
            color_column = st.selectbox("选择颜色列（可选）", ["无"] + list(categorical_columns))
            if color_column == "无":
                color_column = None

        elif chart_type in ["箱线图", "直方图"]:
            column = st.selectbox("选择列", numeric_columns)

        elif chart_type == "饼图":
            if len(categorical_columns) == 0:
                st.warning("数据集中没有分类列，无法创建饼图。")
                return
            column = st.selectbox("选择列", categorical_columns)

        # 使用新的可视化模块生成图表
        fig = visualize_data(filtered_data, chart_type, x_column, y_column, color_column, column)

        with advanced_tab:
            st.subheader("🚀 高级可视化功能")
            st.markdown("探索更强大的图表类型和分析工具")

            # 高级图表类型选择
            adv_chart_type = st.selectbox(
                "选择高级图表类型",
                ["双轴图", "多子图"],
                help="双轴图：同时展示两个不同量纲的变量\n多子图：并列展示多个相关图表"
            )

            if adv_chart_type == "双轴图":
                st.markdown("### 📊 双 Y 轴图表")
                st.info("适合展示两个不同量纲或数量级的变量关系")

                dual_x = st.selectbox("X 轴", filtered_data.columns, key="dual_x")
                dual_y1 = st.selectbox("左 Y 轴变量", numeric_columns, key="dual_y1")
                dual_y2 = st.selectbox("右 Y 轴变量", numeric_columns, key="dual_y2")

                if dual_y1 != dual_y2:
                    if st.button("生成双轴图", key="gen_dual"):
                        dual_fig = create_dual_axis_chart(
                            filtered_data,
                            dual_x,
                            dual_y1,
                            dual_y2,
                            y1_title=dual_y1,
                            y2_title=dual_y2,
                            title=f"{dual_y1} vs {dual_y2} 双轴对比"
                        )
                        st.plotly_chart(dual_fig, use_container_width=True)

                        # 双轴图解读
                        st.markdown("**💡 图表解读**:")
                        st.write(f"- 展示了 **{dual_y1}** (左轴) 和 **{dual_y2}** (右轴) 随 **{dual_x}** 的变化趋势")

                        # 计算相关性
                        if dual_x in filtered_data.columns:
                            corr = filtered_data[[dual_y1, dual_y2]].corr().iloc[0, 1]
                            if abs(corr) > 0.7:
                                st.success(f"✅ 两者存在强相关性 (r={corr:.2f})")
                            elif abs(corr) > 0.3:
                                st.info(f"ℹ️ 两者存在中等相关性 (r={corr:.2f})")
                            else:
                                st.write(f"ℹ️ 两者相关性较弱 (r={corr:.2f})")
                else:
                    st.warning("⚠️ 左右 Y 轴变量不能相同")

            elif adv_chart_type == "多子图":
                st.markdown("### 📈 多变量对比分析")
                st.info("同时展示多个变量的变化趋势")

                # 使用 session_state 保存配置
                if 'multi_x' not in st.session_state:
                    st.session_state.multi_x = filtered_data.columns[0]
                if 'multi_vars' not in st.session_state:
                    st.session_state.multi_vars = numeric_columns[:3] if len(numeric_columns) >= 3 else numeric_columns

                multi_x = st.selectbox(
                    "共享 X 轴",
                    filtered_data.columns,
                    index=list(filtered_data.columns).index(st.session_state.multi_x) if st.session_state.multi_x in filtered_data.columns else 0,
                    key="multi_x_select"
                )
                selected_vars = st.multiselect(
                    "选择要展示的变量",
                    numeric_columns,
                    default=st.session_state.multi_vars,
                    key="multi_vars_select"
                )

                if len(selected_vars) >= 2:
                    # 构建设置字典
                    data_dict = {}
                    titles = {}
                    for var in selected_vars:
                        data_dict[var] = {
                            'x_column': multi_x,
                            'y_column': var
                        }
                        titles[var] = var

                    multi_fig = create_multi_subplot_chart(
                        filtered_data,
                        data_dict,
                        multi_x,
                        titles,
                        subplot_titles=[f"{var} 趋势" for var in selected_vars],
                        title="多变量对比分析"
                    )
                    st.plotly_chart(multi_fig, use_container_width=True)

                    st.markdown("**💡 图表解读**:")
                    st.write(f"- 并列展示了 {len(selected_vars)} 个变量的变化趋势")
                    st.write("- 可以通过共享 X 轴对比不同变量在同一时间点的表现")
                else:
                    st.warning("⚠️ 至少需要选择 2 个变量")

        with basic_tab:
            # 创建小图用于 UI 展示
            fig_small = go.Figure(fig)
            fig_small.update_layout(width=700, height=500)
            st.plotly_chart(fig_small, use_container_width=True)

            # 提供图表解读
            st.subheader("📊 图表解读")
            if chart_type == "散点图":
                st.write(f"• 散点图展示了 **{x_column}** 与 **{y_column}** 之间的关系")
                if x_column and y_column:
                    corr = filtered_data[[x_column, y_column]].corr().iloc[0, 1]
                    if abs(corr) > 0.7:
                        st.success(f"💡 **智能洞察**: {x_column} 和 {y_column} 之间存在强相关性 (相关系数：{corr:.2f})")
                        if corr > 0:
                            st.write(f"  - 两者呈现明显的正相关关系，即一个变量增加时另一个变量也倾向于增加")
                        else:
                            st.write(f"  - 两者呈现明显的负相关关系，即一个变量增加时另一个变量倾向于减少")
                    elif abs(corr) > 0.3:
                        st.info(f"💡 **智能洞察**: {x_column} 和 {y_column} 之间存在中等相关性 (相关系数：{corr:.2f})")
                        if corr > 0:
                            st.write(f"  - 两者存在一定的正相关关系")
                        else:
                            st.write(f"  - 两者存在一定的负相关关系")
                    else:
                        st.write(f"  - 两者相关性较弱，可能没有明显的线性关系")

                    # 提供农业相关的解读
                    if ('temperature' in x_column.lower() or '温' in x_column) and (
                            'humidity' in y_column.lower() or '湿' in y_column):
                        if corr > 0:
                            st.write(f"  - 温度与湿度呈正相关，说明高温时湿度也相对较高")
                        elif corr < 0:
                            st.write(f"  - 温度与湿度呈负相关，说明高温时湿度相对较低，符合蒸发原理")

            elif chart_type == "线图":
                st.write(f"• 线图展示了 **{y_column}** 随 **{x_column}** 变化的趋势")
                if 'timestamp' in x_column.lower() or '时间' in x_column:
                    trend_data = filtered_data[y_column].dropna()
                    if len(trend_data) > 1:
                        first_val = trend_data.iloc[0]
                        last_val = trend_data.iloc[-1]
                        if last_val > first_val * 1.1:
                            st.write(f"  - {y_column} 呈现上升趋势，从 {first_val:.2f} 增加到 {last_val:.2f}")
                        elif last_val < first_val * 0.9:
                            st.write(f"  - {y_column} 呈现下降趋势，从 {first_val:.2f} 下降到 {last_val:.2f}")
                        else:
                            st.write(f"  - {y_column} 基本保持稳定")

            elif chart_type == "柱状图":
                st.write(f"• 柱状图比较了不同 **{x_column}** 类别下的 **{y_column}** 值")

            elif chart_type == "箱线图":
                st.write(f"• 箱线图展示了 **{column}** 的数据分布情况")
                q75, q25 = filtered_data[column].quantile([0.75, 0.25])
                iqr = q75 - q25
                median_val = filtered_data[column].median()
                st.write(f"  - 中位数：{median_val:.2f}")
                st.write(f"  - 四分位距 (IQR): {iqr:.2f} (Q1: {q25:.2f}, Q3: {q75:.2f})")

                # 检查异常值
                outliers = filtered_data[
                    (filtered_data[column] < q25 - 1.5 * iqr) | (filtered_data[column] > q75 + 1.5 * iqr)]
                if len(outliers) > 0:
                    st.warning(f"  - 检测到 {len(outliers)} 个异常值")
                else:
                    st.write(f"  - 未检测到明显异常值")

            elif chart_type == "直方图":
                st.write(f"• 直方图展示了 **{column}** 的分布情况")
                mean_val = filtered_data[column].mean()
                std_val = filtered_data[column].std()
                median_val = filtered_data[column].median()
                mode_val = filtered_data[column].mode().iloc[0] if not filtered_data[column].mode().empty else 'N/A'

                st.write(f"  - 平均值: {mean_val:.2f}, 中位数: {median_val:.2f}, 众数: {mode_val:.2f}")
                st.write(f"  - 标准差: {std_val:.2f}, 方差: {filtered_data[column].var():.2f}")

                # 判断分布形状
                skewness = filtered_data[column].skew()
                kurtosis = filtered_data[column].kurtosis()

                if skewness > 1:
                    st.write(f"  - 分布右偏（正偏）：数据集中在较低值区域，右侧有长尾")
                    st.write(f"  - 数据分布不对称，平均值大于中位数，存在较高值的异常点")
                elif skewness < -1:
                    st.write(f"  - 分布左偏（负偏）：数据集中在较高值区域，左侧有长尾")
                    st.write(f"  - 数据分布不对称，平均值小于中位数，存在较低值的异常点")
                else:
                    st.write(f"  - 分布接近对称")

                # 峰度解释
                if kurtosis > 0:
                    st.write(f"  - 峰度为{kurtosis:.2f}，分布比正态分布更尖锐，数据更集中")
                elif kurtosis < 0:
                    st.write(f"  - 峰度为{kurtosis:.2f}，分布比正态分布更平坦，数据更分散")

                # 农业相关解读
                if 'temperature' in column.lower() or '温' in column:
                    temp_range = filtered_data[column].max() - filtered_data[column].min()
                    if temp_range > 15:
                        st.write(f"  - 温度变化范围较大({temp_range:.2f}°C)，可能存在明显日温差")
                    else:
                        st.write(f"  - 温度变化范围较小({temp_range:.2f}°C)，环境相对稳定")

            elif chart_type == "饼图":
                st.write(f"• 饼图展示了 **{column}** 各类别的占比情况")
                value_counts = filtered_data[column].value_counts()
                total_count = len(filtered_data)

                for idx, (cat, count) in enumerate(value_counts.items()):
                    percentage = (count / total_count) * 100
                    st.write(f"  - {cat}: {count} 个 ({percentage:.1f}%, {count / total_count:.3f})")

                # 饼图多样性指数
                proportions = value_counts / total_count
                diversity_index = -(proportions * np.log(proportions)).sum()
                max_diversity = np.log(len(value_counts))
                normalized_diversity = diversity_index / max_diversity if max_diversity != 0 else 0

                if normalized_diversity > 0.7:
                    st.write(f"  - 类别分布较为均匀，多样性高")
                elif normalized_diversity > 0.3:
                    st.write(f"  - 类别分布中等，存在一定多样性")
                else:
                    st.write(f"  - 类别分布不均匀，某一类别占主导地位")

            elif chart_type == "热力图":
                st.write("• 热力图展示了数据相关性矩阵")
                numeric_cols = filtered_data.select_dtypes(include=['float64', 'int64']).columns
                if len(numeric_cols) >= 2:
                    corr_matrix = filtered_data[numeric_cols].corr()

                    # 计算整体相关性特征
                    abs_corr_values = corr_matrix.abs().values
                    upper_triangle_indices = np.triu_indices_from(abs_corr_values, k=1)
                    upper_triangle_values = abs_corr_values[upper_triangle_indices]

                    if len(upper_triangle_values) > 0:
                        avg_corr = np.mean(upper_triangle_values)
                        max_corr = np.max(upper_triangle_values)
                        min_corr = np.min(upper_triangle_values)

                        st.write(f"  - 平均相关系数: {avg_corr:.3f}")
                        st.write(f"  - 最强相关性: {max_corr:.3f}")
                        st.write(f"  - 最弱相关性: {min_corr:.3f}")

                    # 显示最高相关性对
                    corr_pairs = []
                    for i in range(len(corr_matrix.columns)):
                        for j in range(i + 1, len(corr_matrix.columns)):
                            corr_val = corr_matrix.iloc[i, j]
                            corr_pairs.append((corr_matrix.columns[i], corr_matrix.columns[j], corr_val, abs(corr_val)))

                    if corr_pairs:
                        max_corr_pair = max(corr_pairs, key=lambda x: x[3])
                        st.write(
                            f"  - 最强相关性: {max_corr_pair[0]} 与 {max_corr_pair[1]} (相关系数: {max_corr_pair[2]:.3f})")

                        # 农业相关解读
                        if ('temperature' in max_corr_pair[0].lower() or '温' in max_corr_pair[0].lower()) and \
                                ('humidity' in max_corr_pair[1].lower() or '湿' in max_corr_pair[1].lower()) or \
                                ('humidity' in max_corr_pair[0].lower() or '湿' in max_corr_pair[0].lower()) and \
                                ('temperature' in max_corr_pair[1].lower() or '温' in max_corr_pair[1].lower()):
                            if max_corr_pair[2] > 0:
                                st.write(f"    • 温湿度呈正相关，说明温度升高时湿度也倾向上升")
                            else:
                                st.write(f"    • 温湿度呈负相关，符合典型的蒸发型环境特征")

        with tab2:
            # 创建下载链接
            fig_large = go.Figure(fig)
            fig_large.update_layout(width=1200, height=800)

            # 将Plotly图表转换为JSON
            fig_json = json.dumps(fig_large, cls=plotly.utils.PlotlyJSONEncoder)

            # 添加图表说明
            with st.expander("📈 图表交互说明"):
                st.markdown("""
            **图表交互功能：**
            - **缩放**: 在图表上拖拽可缩放区域
            - **平移**: 按住Shift键并拖拽可平移视图
            - **图例**: 点击图例项可显示/隐藏对应数据系列
            - **导出**: 点击右上角相机图标可下载图表
            """)

            # 添加智能推荐
            if chart_type == "散点图" and x_column and y_column:
                corr = filtered_data[[x_column, y_column]].corr().iloc[0, 1]
                if abs(corr) > 0.7:
                    st.success(f"💡 **智能洞察**: {x_column} 和 {y_column} 之间存在强相关性 (相关系数: {corr:.2f})")
                elif abs(corr) > 0.3:
                    st.info(f"💡 **智能洞察**: {x_column} 和 {y_column} 之间存在中等相关性 (相关系数: {corr:.2f})")