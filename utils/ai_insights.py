import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from .ollama_chat import OllamaChat
from .analysis import describe_data, calculate_correlation, group_and_aggregate
from .predictions import perform_prediction


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

    def analyze_prediction_insights_stream(self, historical_data, forecast_data, model_explanation, prediction_description=None, on_chunk_callback=None):
        """
        分析预测结果并使用AI进行智能解读和建议（流式输出）
        """
        try:
            # 准备预测摘要
            prediction_summary = {
                "historical_shape": historical_data.shape if historical_data is not None else (0, 0),
                "forecast_shape": forecast_data.shape if forecast_data is not None else (0, 0),
                "model_explanation": model_explanation,
                "historical_start": str(historical_data.index.min()) if historical_data is not None and not historical_data.empty else "N/A",
                "historical_end": str(historical_data.index.max()) if historical_data is not None and not historical_data.empty else "N/A",
                "forecast_start": str(forecast_data['timestamp'].min()) if forecast_data is not None and not forecast_data.empty else "N/A",
                "forecast_end": str(forecast_data['timestamp'].max()) if forecast_data is not None and not forecast_data.empty else "N/A",
            }
            
            # 生成AI预测分析提示
            prompt = self._generate_prediction_analysis_prompt(prediction_summary, prediction_description)
            
            # 获取AI分析结果（流式）
            ai_response = self.chat.send_message_stream(prompt, on_chunk_callback)
            
            return ai_response, prediction_summary
            
        except Exception as e:
            st.error(f"AI预测分析过程中发生错误: {str(e)}")
            if on_chunk_callback:
                on_chunk_callback(f"AI预测分析失败: {str(e)}")
            return f"AI预测分析失败: {str(e)}", {}

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

    def _generate_prediction_analysis_prompt(self, prediction_summary, prediction_description=None):
        """
        生成预测分析的AI提示
        """
        base_prompt = f"""
        你是一位专业的农业预测分析专家，擅长解读预测模型结果并提供实用建议。
        请分析以下农业数据预测结果，并提供详细的洞察和建议：

        预测模型信息：
        - 历史数据形状: {prediction_summary['historical_shape']}
        - 预测数据形状: {prediction_summary['forecast_shape']}
        - 历史数据时间范围: 从 {prediction_summary['historical_start']} 到 {prediction_summary['historical_end']}
        - 预测数据时间范围: 从 {prediction_summary['forecast_start']} 到 {prediction_summary['forecast_end']}
        - 模型解释: {prediction_summary['model_explanation']}

        请按以下结构提供分析:
        1. **预测概览**: 总结预测结果的主要特征
        2. **趋势解读**: 解释预测数据中的重要趋势
        3. **可信度评估**: 评价预测结果的可靠性
        4. **农业意义**: 解释预测结果对农业生产的实际意义
        5. **风险提示**: 指出预测中的不确定因素和风险
        6. **管理建议**: 基于预测结果提出具体的农业管理建议
        7. **监控要点**: 建议重点关注哪些指标和时间点

        请使用专业但易懂的语言，重点突出对农业生产和决策有价值的洞察。
        """
        
        if prediction_description:
            base_prompt += f"\n\n额外背景信息: {prediction_description}"
        
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
            ai_insights, data_summary = self.analyze_data_insights_stream(numeric_data, data_description, on_token_receive)
        
        # 显示AI分析结果
        st.markdown("#### AI分析结果")
        st.info(ai_insights)
        
        # 提供基于AI的交互式建议
        self._provide_ai_recommendations(data_summary)
        
        return ai_insights, data_summary

    def integrate_prediction_with_ai(self, data, model_type, prediction_days, params=None, prediction_description=None):
        """
        整合预测分析与AI洞察（流式输出版本）
        """
        st.subheader("🤖 AI驱动的预测分析与建议")
        
        # 执行传统预测
        st.markdown("#### 传统预测模型结果")
        with st.spinner("正在运行预测模型..."):
            historical_data, forecast_data, model_explanation, rmse = perform_prediction(
                data, model_type, prediction_days, params
            )
        
        # 显示预测结果
        self._show_basic_prediction_results(historical_data, forecast_data, model_explanation, rmse)
        
        # AI智能分析预测结果
        st.markdown("#### AI对预测结果的智能解读")
        
        # 创建一个容器来显示流式输出
        response_container = st.container()
        
        with response_container:
            response_text = st.empty()  # 创建一个空的文本元素来逐步显示响应
            
        full_response = ""
        
        def on_token_receive(token):
            nonlocal full_response
            full_response += token
            response_text.info(full_response)  # 实时更新显示
        
        with st.spinner("AI正在分析预测结果并生成建议..."):
            # 确保数据适合AI分析
            if historical_data is not None and not historical_data.empty:
                # 只选择数值列进行AI分析
                numeric_historical = historical_data.select_dtypes(include=[np.number])
                if numeric_historical.empty:
                    # 如果没有数值列，使用原始数据但确保时间列被排除
                    numeric_columns = [col for col in historical_data.columns if col != historical_data.index.name]
                    for col in numeric_columns:
                        if pd.api.types.is_numeric_dtype(historical_data[col]):
                            continue
                        else:
                            # 尝试转换为数值类型
                            try:
                                historical_data[col] = pd.to_numeric(historical_data[col], errors='coerce')
                            except:
                                pass  # 如果转换失败，保持原样
                    numeric_historical = historical_data.select_dtypes(include=[np.number])
            else:
                numeric_historical = historical_data
                
            ai_prediction_insights, prediction_summary = self.analyze_prediction_insights_stream(
                numeric_historical, forecast_data, model_explanation, prediction_description, on_token_receive
            )
        
        # 显示AI分析结果
        st.markdown("#### AI预测分析结果")
        st.info(ai_prediction_insights)
        
        # 提供基于AI的预测建议
        self._provide_prediction_recommendations(prediction_summary)
        
        return ai_prediction_insights, prediction_summary

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

    def _provide_prediction_recommendations(self, prediction_summary):
        """
        基于AI预测分析提供建议
        """
        st.markdown("#### 🌱 预测驱动的农业建议")
        
        prediction_recommendation_options = [
            "根据预测结果，未来一周应采取哪些管理措施？",
            "预测数据显示了哪些需要警惕的趋势？",
            "如何根据预测调整作物种植计划？",
            "预测结果对灌溉/施肥安排有何指导意义？",
            "基于预测，如何提前防范潜在风险？"
        ]
        
        selected_prediction_question = st.selectbox(
            "选择一个方面获取基于预测的AI建议:",
            prediction_recommendation_options,
            key="prediction_questions"
        )
        
        if st.button("获取预测建议", key="prediction_btn"):
            with st.spinner("AI正在生成基于预测的建议..."):
                prompt = f"""
                基于以下预测信息：{prediction_summary}
                
                请回答：{selected_prediction_question}
                
                提供具体、可操作的建议，并说明这些建议的时间敏感性。
                """
                
                # 为预测建议也使用流式输出
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


def main():
    """AI洞察分析主界面"""
    st.title("🤖 AI驱动的农业数据分析与预测")
    st.caption("结合传统数据分析与AI智能解读，提供深度洞察和专业建议")
    
    # 初始化AI分析器
    if 'ai_analyzer' not in st.session_state:
        st.session_state.ai_analyzer = AIInsightsAnalyzer("qwen3:4b")
    
    analyzer = st.session_state.ai_analyzer
    
    # 检查模型可用性
    is_available, available_models = analyzer.chat.check_model_available()
    
    if not is_available:
        st.warning(f"⚠️ AI模型 {analyzer.model_name} 未安装或不可用")
        col1, col2 = st.columns([3, 1])
        with col1:
            model_input = st.text_input("输入要使用的AI模型名称:", value=analyzer.model_name)
        with col2:
            if st.button("🔄 切换模型"):
                analyzer.chat.model_name = model_input
                analyzer.model_name = model_input
                st.rerun()
        
        if st.button("📥 拉取AI模型", type="primary"):
            success = analyzer.chat.pull_model_if_needed()
            if success:
                st.rerun()
    else:
        st.success(f"✅ AI模型 {analyzer.model_name} 可用")
        
        # 选择分析类型
        analysis_type = st.radio(
            "选择分析类型:",
            ["数据洞察分析", "预测结果分析"]
        )
        
        if analysis_type == "数据洞察分析":
            st.markdown("### 数据洞察分析")
            st.info("上传或选择数据进行AI驱动的深入分析")
            
            # 这里可以集成数据上传或选择功能
            # 为演示目的，我们使用模拟数据
            if st.button("执行AI数据洞察分析"):
                # 示例：使用模拟数据进行分析（实际应用中应使用真实数据）
                sample_data = pd.DataFrame({
                    'timestamp': pd.date_range(start='2023-01-01', periods=100, freq='D'),
                    'temperature': np.random.normal(25, 5, 100),
                    'humidity': np.random.normal(60, 10, 100),
                    'soil_moisture': np.random.normal(40, 8, 100)
                })
                analyzer.integrate_analysis_with_ai(sample_data, "农业环境监测数据")
        
        elif analysis_type == "预测结果分析":
            st.markdown("### 预测结果分析")
            st.info("选择数据和预测模型进行AI驱动的预测分析")
            
            # 这里可以集成预测参数设置
            model_type = st.selectbox("选择预测模型", ["SARIMA", "LSTM", "Transformer", "Prophet", "Hybrid"])
            prediction_days = st.number_input("预测天数", min_value=1, max_value=30, value=7)
            
            if st.button("执行AI预测分析"):
                # 示例：使用模拟数据进行预测分析（实际应用中应使用真实数据）
                sample_data = [(pd.Timestamp.now() - pd.Timedelta(days=x), np.random.uniform(20, 30)) 
                              for x in range(100, 0, -1)]
                analyzer.integrate_prediction_with_ai(sample_data, model_type, prediction_days)


if __name__ == "__main__":
    main()