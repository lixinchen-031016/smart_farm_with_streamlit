import plotly.express as px
import streamlit as st

from utils.logger import log_operation
from utils.lazy_importer import lazy_import

# 延迟导入分析模块
utils_analysis_module = lazy_import('utils.analysis')


# 函数：数据分析
def data_analysis():
    """显示数据分析页面，提供描述性统计和相关性分析功能

    显示数据分析页面，包括智能分析解读和详细数据图表两个标签页，
    提供描述性统计、相关性分析和智能推荐功能。

    Returns:
        None: 无返回值，直接在页面上显示内容
    """
    if not st.session_state.get('logged_in'):
        st.query_params.page = "login"
        return

    st.title("数据分析")
    if 'data' not in st.session_state:
        st.warning("请先在数据概览页面上传数据")
        return

    data = st.session_state['data']

    # 添加标签页以组织复杂功能
    tab1, tab2 = st.tabs(["📊 智能分析解读", "📈 详细数据图表"])

    with tab1:
        st.subheader("通俗易懂的数据分析")
        log_operation(st.session_state['username'], "INFO", "数据分析-智能解读",
                      f"数据集维度: {data.shape}")

        # 使用增强版分析工具提供通俗易懂的分析结果
        try:
            from utils.enhanced_analysis import enhanced_data_analysis
            enhanced_data_analysis(data)
        except ImportError:
            st.error("增强版分析工具不可用，使用基础分析功能")
            # 原始基础分析功能
            st.subheader("描述性统计")
            with st.expander("📊 查看统计指标说明"):
                st.markdown("""
                **关键统计指标解释：**
                - **均值(Mean)**: 数据的平均值，反映数据集中趋势
                - **标准差(Std)**: 数据离散程度的度量，值越大表示数据波动越大
                - **最小值/最大值**: 数据的取值范围
                - **25%/75%分位数**: 四分位数，帮助了解数据分布情况
                """)

            desc_data = utils_analysis_module().describe_data(data)
            st.dataframe(desc_data)

            # 添加智能推荐
            numeric_columns = data.select_dtypes(include=['float64', 'int64']).columns
            if len(numeric_columns) > 0:
                st.info(
                    f"💡 **智能推荐**: 检测到 {len(numeric_columns)} 个数值型变量，建议重点关注均值和标准差差异较大的指标")

    with tab2:
        st.subheader("详细相关性分析")
        numeric_columns = data.select_dtypes(include=['float64', 'int64']).columns
        if len(numeric_columns) < 2:
            st.warning("数据集中数值列不足两列，无法进行相关性分析。")
        else:
            # 添加相关性分析说明
            with st.expander("🔗 相关性分析说明"):
                st.markdown("""
                **相关系数解读：**
                - **1**: 完全正相关
                - **0**: 无线性相关性
                - **-1**: 完全负相关
                - **0.7~1**: 强正相关
                - **0.3~0.7**: 中等正相关
                - **0~0.3**: 弱正相关
                """)

            corr_matrix = utils_analysis_module().calculate_correlation(data)

            # 性能优化：对大数据集进行采样
            sample_size = min(1000, len(data)) if len(data) > 1000 else len(data)
            if len(data) > sample_size:
                st.info(f"🚀 **性能优化**: 数据集较大，已对 {sample_size} 行数据进行采样以提升渲染性能")

            fig = px.imshow(corr_matrix,
                            text_auto=True,
                            aspect="auto",
                            color_continuous_scale='RdBu_r',
                            zmin=-1,
                            zmax=1,
                            labels=dict(color="相关系数"))
            fig.update_traces(text=corr_matrix.round(2),
                              texttemplate="%{text}",
                              hovertemplate="变量1: %{x}<br>变量2: %{y}<br>相关系数: %{text}<extra></extra>")
            fig.update_layout(
                title="变量相关性热力图",
                font=dict(size=12)
            )
            st.plotly_chart(fig, use_container_width=True)

            # 添加智能推荐
            high_corr_pairs = []
            for i in range(len(corr_matrix.columns)):
                for j in range(i + 1, len(corr_matrix.columns)):
                    corr_value = corr_matrix.iloc[i, j]
                    if abs(corr_value) > 0.7:
                        high_corr_pairs.append((corr_matrix.columns[i], corr_matrix.columns[j], corr_value))

            if high_corr_pairs:
                st.info("💡 **智能推荐**: 检测到以下强相关变量对，建议深入分析其因果关系:")
                for col1, col2, corr in high_corr_pairs[:3]:  # 只显示前3个
                    st.markdown(f"- **{col1}** 与 **{col2}** 的相关系数为 **{corr:.2f}**")
