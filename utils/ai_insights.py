import numpy as np
import pandas as pd
import streamlit as st
import os
from datetime import datetime

from .analysis import describe_data, calculate_correlation
from .ollama_chat import OllamaChat


class AIInsightsAnalyzer:
    def __init__(self, model_name="qwen3.5:4b"):
        """
        初始化AI洞察分析器
        :param model_name: 要使用的模型名称，默认为qwen3.5:4b
        """
        self.chat = OllamaChat(model_name)
        self.model_name = model_name

    def save_ai_insights_to_md(self, ai_insights, data_summary, data_description=None):
        """
        将 AI 洞察分析结果保存为 markdown 文件
        :param ai_insights: AI 生成的分析结果
        :param data_summary: 数据摘要信息
        :param data_description: 数据背景描述
        :return: 保存的文件路径
        """
        # 创建保存目录（如果不存在）
        save_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ai_insights_exports')
        os.makedirs(save_dir, exist_ok=True)
        
        # 生成文件名（使用时间戳）
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"AI_Insights_{timestamp}.md"
        filepath = os.path.join(save_dir, filename)
        
        # 构建 markdown 内容
        md_content = f"""# 🤖 AI 农业数据分析洞察报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 📋 数据基本信息

- **数据形状**: {data_summary.get('shape', 'N/A')}
- **列名**: {', '.join(data_summary.get('columns', []))}
- **数值型列**: {', '.join(data_summary.get('numeric_columns', []))}
- **日期型列**: {', '.join(data_summary.get('date_columns', []))}

"""
        
        if data_description:
            md_content += f"""## 📝 数据背景描述

{data_description}

---

"""
        
        md_content += f"""## 🧠 AI 智能分析结果

{ai_insights}

---

## 💡 说明

本报告由 AI 大模型（{self.model_name}）自动生成，基于提供的数据进行智能分析和解读。
建议结合实际情况和专业农艺知识进行参考使用.
"""
        
        # 写入文件
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        return filepath

    def analyze_data_insights_stream(self, data, data_description=None, on_chunk_callback=None, on_think_callback=None):
        """
        分析数据洞察并使用 AI 进行智能解读（流式输出）
        直接将原始数据传递给 AI，由 AI 自行分析
        """
        try:
            # 准备数据摘要 - 包含所有列信息，特别是时间列
            date_columns = list(data.select_dtypes(include=['datetime64']).columns)
            
            # 查找可能的日期字符串列（对象类型但包含日期格式）
            for col in data.select_dtypes(include=['object']).columns:
                try:
                    # 尝试转换为 datetime，如果成功则是日期列
                    pd.to_datetime(data[col].dropna().head(10))
                    if col not in date_columns:
                        date_columns.append(col)
                except:
                    continue
            
            # 构建完整的数据摘要信息
            data_summary = {
                "shape": data.shape,
                "columns": list(data.columns),
                "numeric_columns": list(data.select_dtypes(include=[np.number]).columns),
                "date_columns": date_columns,
                "all_columns_types": {col: str(dtype) for col, dtype in data.dtypes.items()},
                "data_preview": data.head(10).to_dict(),  # 前 10 行数据预览
                "data_tail": data.tail(5).to_dict()  # 最后 5 行数据预览
            }
            
            # 只对数值列计算统计信息
            numeric_data = data.select_dtypes(include=[np.number])
            if not numeric_data.empty:
                desc_stats = describe_data(numeric_data)
                correlation_matrix = calculate_correlation(numeric_data)
                data_summary["desc_stats"] = desc_stats.to_dict() if desc_stats is not None else {}
                data_summary["correlation_matrix"] = correlation_matrix.to_dict() if correlation_matrix is not None else {}

            # 生成 AI 分析提示 - 直接传递完整数据
            prompt = self._generate_data_analysis_prompt(data, data_summary, data_description)

            # 获取 AI 分析结果（流式）
            ai_response = self.chat.send_message_stream(prompt, on_chunk_callback, on_think_callback)
            
            # 自动保存 AI 分析结果为 markdown 文件
            try:
                saved_filepath = self.save_ai_insights_to_md(ai_response, data_summary, data_description)
                if on_chunk_callback is None:  # 只在非流式模式下显示成功消息
                    st.success(f"✅ AI 分析结果已自动保存至：{saved_filepath}")
            except Exception as save_error:
                st.warning(f"⚠️ 保存 AI 分析结果失败：{str(save_error)}")
            
            return ai_response, data_summary

        except Exception as e:
            st.error(f"AI 数据分析过程中发生错误：{str(e)}")
            if on_chunk_callback:
                on_chunk_callback(f"AI 分析失败：{str(e)}")
            return f"AI 分析失败：{str(e)}", {}

    def _generate_data_analysis_prompt(self, raw_data, data_summary, data_description=None):
        """
        生成数据分析的 AI 提示 - 直接传递原始数据
        """
        # 准备数据预览文本 - 只显示前 5 行数据，并正确处理时间戳
        preview_rows = []
        for col in raw_data.columns:
            col_data = raw_data[col].head()
            
            # 如果是日期/时间类型，格式化为可读字符串
            if pd.api.types.is_datetime64_any_dtype(col_data):
                # 格式化为 YYYY-MM-DD HH:MM:SS
                formatted_vals = [val.strftime('%Y-%m-%d %H:%M:%S') if pd.notna(val) else 'NaT' 
                                 for val in col_data]
                preview_rows.append(f"列 '{col}' (时间类型): {', '.join(formatted_vals[:5])}...")
            elif col_data.dtype == 'object':
                # 对象类型，尝试检查是否为日期字符串
                try:
                    # 尝试转换为日期，如果成功则按日期格式化
                    date_vals = pd.to_datetime(col_data.dropna().head())
                    formatted_vals = [val.strftime('%Y-%m-%d %H:%M:%S') for val in date_vals]
                    preview_rows.append(f"列 '{col}' (日期字符串): {', '.join(formatted_vals[:5])}...")
                except:
                    # 不是日期，按原样显示
                    preview_rows.append(f"列 '{col}': {', '.join(map(str, list(col_data)[:5]))}...")
            else:
                # 数值或其他类型
                preview_rows.append(f"列 '{col}': {', '.join(map(str, list(col_data)[:5]))}...")
        
        data_preview_text = "\n".join(preview_rows)
        
        base_prompt = f"""
你是一位专业的农业数据分析专家，拥有丰富的农业数据解读和分析经验。
请分析以下农业数据集，并提供详细的洞察和建议：

【数据集基本信息】
- 数据形状：{data_summary['shape'][0]} 行 × {data_summary['shape'][1]} 列
- 所有列名：{', '.join(data_summary['columns'])}
- 数值型列：{', '.join(data_summary['numeric_columns'])}
- 日期/时间列：{', '.join(data_summary['date_columns'])}
- 数据类型详情：{data_summary['all_columns_types']}

【数据预览（前 5 行）】
{data_preview_text}

【描述性统计信息（仅数值列）】
{data_summary['desc_stats']}

【相关性矩阵（仅数值列）】
{data_summary['correlation_matrix']}

请按以下结构提供分析:
1. **数据概览**: 总结数据的基本特征（时间跨度、变量类型、数据质量等）
2. **关键指标解读**: 分析重要的数值指标及其含义（均值、范围、分布等）
3. **趋势分析**: 识别数据中的重要趋势和模式（时间序列趋势、周期性变化等）
4. **关联关系**: 解释指标之间的相关性及其农业意义（正相关、负相关、因果关系等）
5. **异常检测**: 指出任何异常值或值得关注的模式（离群点、突变点、异常模式等）
6. **农业建议**: 基于数据分析提出具体的操作建议（灌溉、施肥、温控等）
7. **后续行动**: 推荐下一步的数据分析或操作步骤（深入分析方向、监测重点等）

请使用专业但易懂的语言，重点突出对农业生产和管理有意义的洞察。
"""

        if data_description:
            base_prompt += f"\n\n【额外背景信息】\n{data_description}"
        
        return base_prompt

    def integrate_analysis_with_ai(self, data, data_description=None):
        """
        整合数据分析与 AI 洞察（流式输出版本）
        """
        st.subheader("🤖 AI 驱动的数据分析洞察")
    
        # AI 智能分析 - 直接使用完整原始数据
        st.markdown("#### AI 智能解读与建议")
        st.caption("将完整的原始数据传递给 AI 模型进行深度分析")
    
        # 创建两个容器：一个用于思考过程，一个用于最终回答
        think_container = st.container()
        response_container = st.container()
    
        with think_container:
            think_placeholder = st.empty()  # 用于显示思考过程
        
        with response_container:
            response_placeholder = st.empty()  # 占位符用于逐步显示响应
    
        full_response = ""
        thinking_content = ""
    
        def on_token_receive(token):
            nonlocal full_response
            full_response += token
            response_placeholder.markdown(full_response)  # 实时更新显示
        
        def on_think_receive(token):
            nonlocal thinking_content
            thinking_content += token
            # 使用折叠框显示思考过程
            think_placeholder.markdown(f"""
            <div style="background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin-bottom: 20px;">
                <details style="margin: 0;">
                    <summary style="cursor: pointer; color: #666; font-weight: bold;">🤔 AI 正在思考中...</summary>
                    <div style="margin-top: 10px; color: #888; font-size: 0.9em; line-height: 1.6;">
                        {thinking_content}
                    </div>
                </details>
            </div>
            """)
    
        # 直接传递原始数据给 AI，不做任何预处理
        with st.spinner("AI 正在分析完整数据并生成洞察..."):
            ai_insights, data_summary = self.analyze_data_insights_stream(data, data_description,
                                                                          on_token_receive,
                                                                          on_think_receive)
    
        # 如果思考完成后还有内容，确保它保持可见
        if thinking_content:
            think_placeholder.markdown(f"""
            <div style="background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin-bottom: 20px;">
                <details style="margin: 0;">
                    <summary style="cursor: pointer; color: #666; font-weight: bold;">✅ AI 思考过程</summary>
                    <div style="margin-top: 10px; color: #888; font-size: 0.9em; line-height: 1.6;">
                        {thinking_content}
                    </div>
                </details>
            </div>
            """)
    
        # 显示自动保存提示
        export_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ai_insights_exports')
        if os.path.exists(export_dir):
            export_files = [f for f in os.listdir(export_dir) if f.endswith('.md')]
            if export_files:
                st.caption(f"📁 已有 {len(export_files)} 份历史导出记录（自动保存）")
    
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
    analyzer = AIInsightsAnalyzer("qwen3.5:4b")
    analyzer.show_ai_insights_page()