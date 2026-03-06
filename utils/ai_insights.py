import numpy as np
import pandas as pd
import streamlit as st

from .analysis import describe_data, calculate_correlation
from .ollama_chat import OllamaChat


class AIInsightsAnalyzer:
    def __init__(self, model_name="qwen3:4b"):
        """
        初始化AI洞察分析器
        :param model_name: 要使用的模型名称，默认为qwen3:4b
        """
        self.chat = OllamaChat(model_name)
        self.model_name = model_name

    def analyze_data_insights_stream(self, data, data_description=None, on_chunk_callback=None):
        """
        分析数据洞察并使用AI进行智能解读（流式输出）
        """
        try:
            # 获取基本统计信息
            desc_stats = describe_data(data)
            correlation_matrix = calculate_correlation(data)

            # 准备数据摘要
            data_summary = {
                "shape": data.shape,
                "columns": list(data.columns),
                "numeric_columns": list(data.select_dtypes(include=[np.number]).columns),
                "date_columns": list(data.select_dtypes(include=['datetime64']).columns),
                "desc_stats": desc_stats.to_dict() if desc_stats is not None else {},
                "correlation_matrix": correlation_matrix.to_dict() if correlation_matrix is not None else {}
            }

            # 生成AI分析提示
            prompt = self._generate_data_analysis_prompt(data_summary, data_description)

            # 获取AI分析结果（流式）
            ai_response = self.chat.send_message_stream(prompt, on_chunk_callback)

            return ai_response, data_summary

        except Exception as e:
            st.error(f"AI数据分析过程中发生错误: {str(e)}")
            if on_chunk_callback:
                on_chunk_callback(f"AI分析失败: {str(e)}")
            return f"AI分析失败: {str(e)}", {}

    def _generate_data_analysis_prompt(self, data_summary, data_description=None):
        """
        生成数据分析的AI提示
        """
        base_prompt = f"""
        你是一位专业的农业数据分析专家，拥有丰富的农业数据解读和分析经验。
        请分析以下农业数据集，并提供详细的洞察和建议：

        数据集基本信息：
        - 数据形状: {data_summary['shape']}
        - 列名: {data_summary['columns']}
        - 数值型列: {data_summary['numeric_columns']}
        - 日期型列: {data_summary['date_columns']}

        描述性统计信息:
        {data_summary['desc_stats']}

        相关性矩阵:
        {data_summary['correlation_matrix']}

        请按以下结构提供分析:
        1. **数据概览**: 总结数据的基本特征
        2. **关键指标解读**: 分析重要的数值指标及其含义
        3. **趋势分析**: 识别数据中的重要趋势和模式
        4. **关联关系**: 解释指标之间的相关性及其农业意义
        5. **异常检测**: 指出任何异常值或值得关注的模式
        6. **农业建议**: 基于数据分析提出具体的操作建议
        7. **后续行动**: 推荐下一步的数据分析或操作步骤

        请使用专业但易懂的语言，重点突出对农业生产和管理有意义的洞察。
        """

        if data_description:
            base_prompt += f"\n\n额外背景信息: {data_description}"

        return base_prompt

    def integrate_analysis_with_ai(self, data, data_description=None):
        """
        整合数据分析与AI洞察（流式输出版本）
        """
        st.subheader("🤖 AI驱动的数据分析洞察")

        # 执行传统数据分析
        st.markdown("#### 传统数据分析结果")
        desc_stats, corr_matrix = self._show_basic_analysis(data)

        # AI智能分析
        st.markdown("#### AI智能解读与建议")

        # 创建一个容器来显示流式输出
        response_container = st.container()

        with response_container:
            response_text = st.empty()  # 创建一个空的文本元素来逐步显示响应

        full_response = ""

        def on_token_receive(token):
            nonlocal full_response
            full_response += token
            response_text.info(full_response)  # 实时更新显示

        # 准备数据以供AI分析 - 只使用数值列
        numeric_data = data.select_dtypes(include=[np.number])
        if numeric_data.empty:
            # 如果没有数值列，尝试转换可能的数值列
            for col in data.columns:
                if col != 'timestamp':  # 排除时间戳列
                    try:
                        numeric_series = pd.to_numeric(data[col], errors='coerce')
                        if not numeric_series.isna().all():  # 如果不是全部为NaN
                            numeric_data = pd.concat([numeric_data, numeric_series], axis=1)
                    except:
                        continue

        with st.spinner("AI正在分析数据并生成洞察..."):
            ai_insights, data_summary = self.analyze_data_insights_stream(numeric_data, data_description,
                                                                          on_token_receive)

        # 显示AI分析结果
        st.markdown("#### AI分析结果")
        st.info(ai_insights)

        # 提供基于AI的交互式建议
        self._provide_ai_recommendations(data_summary)

        return ai_insights, data_summary

    def _show_basic_analysis(self, data):
        """
        显示基本分析结果
        """
        from .enhanced_analysis import enhanced_data_analysis
        return enhanced_data_analysis(data)

    def _show_basic_prediction_results(self, historical_data, forecast_data, model_explanation, rmse):
        """
        显示基本预测结果
        """
        st.markdown(f"**模型性能指标**：")
        st.write(f"- RMSE: {rmse:.4f}")
        st.markdown(f"**模型解释**：")
        st.info(model_explanation)

        # 显示预测数据预览
        st.markdown(f"**预测数据预览**：")
        st.dataframe(forecast_data.head())

    def _provide_ai_recommendations(self, data_summary):
        """
        基于AI分析提供交互式建议
        """
        st.markdown("#### 💡 AI个性化建议")

        recommendation_options = [
            "基于当前数据，如何优化农业生产？",
            "从这些数据中可以看出哪些环境变化趋势？",
            "如何根据这些数据调整灌溉/施肥策略？",
            "数据中有哪些指标需要重点关注？",
            "如何利用这些数据进行病虫害预警？"
        ]

        selected_question = st.selectbox(
            "选择一个方面获取AI的专业建议:",
            recommendation_options
        )

        if st.button("获取AI建议"):
            with st.spinner("AI正在生成个性化建议..."):
                prompt = f"""
                基于以下数据集信息：{data_summary}
                
                请回答：{selected_question}
                
                提供具体、可操作的建议，并解释这些建议背后的原理。
                """

                # 为单独的AI建议也使用流式输出
                response_container = st.container()

                with response_container:
                    response_text = st.empty()  # 创建一个空的文本元素来逐步显示响应

                full_response = ""

                def on_token_receive(token):
                    nonlocal full_response
                    full_response += token
                    response_text.success(full_response)  # 实时更新显示

                ai_response = self.chat.send_message_stream(prompt, on_token_receive)
                st.success(ai_response)

    def show_ai_insights_page(self):
        """
        显示 AI 洞察分析页面（完整 UI 页面）
        """
        if not st.session_state.get('logged_in'):
            st.query_params.page = "login"
            return

        st.title("🤖 AI 洞察分析")
        st.caption("利用 AI 大模型对数据分析和预测结果进行智能解读和建议")

        # 初始化 AI 分析器
        if 'ai_analyzer' not in st.session_state:
            st.session_state.ai_analyzer = AIInsightsAnalyzer(self.model_name)

        analyzer = st.session_state.ai_analyzer

        # 检查模型可用性
        is_available, available_models = analyzer.chat.check_model_available()

        if not is_available:
            st.warning(f"⚠️ AI 模型 {analyzer.model_name} 未安装或不可用")
            col1, col2 = st.columns([3, 1])
            with col1:
                model_input = st.text_input("输入要使用的 AI 模型名称:", value=analyzer.model_name)
            with col2:
                if st.button("🔄 切换模型"):
                    analyzer.chat.model_name = model_input
                    analyzer.model_name = model_input
                    st.rerun()

            if st.button("📥 拉取 AI 模型", type="primary"):
                success = analyzer.chat.pull_model_if_needed()
                if success:
                    st.rerun()
        else:
            st.success(f"✅ AI 模型 {analyzer.model_name} 可用")

            # 选择分析类型
            st.markdown("### 数据洞察分析")

            if 'data' not in st.session_state:
                st.warning("请先在数据概览页面上传数据")
                return

            data = st.session_state['data']
            data_description = st.text_area("数据背景描述（可选）",
                                            placeholder="请输入关于数据来源、用途或其他相关信息的描述...", height=100)

            if st.button("执行 AI 数据洞察分析", type="primary"):
                with st.spinner("AI 正在分析数据并生成洞察..."):
                    ai_insights, data_summary = analyzer.integrate_analysis_with_ai(data, data_description)


def show_ai_insights():
    """
    模块入口函数：显示 AI 洞察分析页面
    """
    # 创建分析器实例并显示页面
    analyzer = AIInsightsAnalyzer("qwen3:4b")
    analyzer.show_ai_insights_page()