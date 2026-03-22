import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import models
from auth import session
from utils.logger import log_operation
from utils.predictions import prepare_prediction_ui, multivariate_prediction, get_historical_data, perform_prediction, \
    show_prediction_results


def data_prediction():
    """显示数据预测页面，允许用户进行本地数据预测"""
    if not st.session_state.get('logged_in'):
        st.query_params.page = "login"
        return

    st.title("数据预测")

    # 使用预测模块的 UI 组件
    data_type, model_type, prediction_days, lstm_params, pred_mode = prepare_prediction_ui()

    # 默认使用单变量预测模式（向后兼容）
    if pred_mode is None or pred_mode == "单变量时间序列预测":
        model_mapping = {
            "Prophet+SARIMA(推荐)": "SARIMA",
            "纯 Prophet": "Prophet",
            "纯 SARIMA": "SARIMA",
        }
        actual_model_type = model_mapping.get(model_type, model_type)
    else:
        actual_model_type = "multivariate"

    if st.button("开始预测"):
        # 根据预测模式调用不同的处理函数
        if pred_mode == "多变量耦合预测":
            # 多变量预测模式
            st.info("🔬 多变量耦合预测 - 同时分析温度、湿度、光照的相互作用")
            log_operation(st.session_state['username'], "INFO", "多变量预测",
                          f"天数：{prediction_days}")
            progress_bar = st.progress(0)
            st.write("预测进度：获取多源环境数据中...")

            try:
                # 从数据库获取三种数据
                temp_data = session.query(models.AirTemperatureHumidity).order_by(
                    models.AirTemperatureHumidity.timestamp.desc()).limit(200).all()
                humid_data = session.query(models.AirTemperatureHumidity).order_by(
                    models.AirTemperatureHumidity.timestamp.desc()).limit(200).all()
                light_data = session.query(models.LightIntensity).order_by(
                    models.LightIntensity.timestamp.desc()).limit(200).all()

                if not temp_data or not humid_data or not light_data:
                    st.error("❌ 数据库中没有足够的环境数据，无法进行多变量预测")
                    progress_bar.empty()
                    return

                progress_bar.progress(33)
                st.write("预测进度：多变量模型训练中...")

                # 调用多变量预测函数
                merged_df, rf_temp, rf_humid, feature_importance, explanation = multivariate_prediction(
                    temp_data, humid_data, light_data, prediction_days, lstm_params
                )

                if merged_df is not None:
                    progress_bar.progress(66)
                    st.write("预测进度：生成可视化结果...")

                    # 显示特征重要性
                    with st.expander("🔍 特征重要性分析", expanded=True):
                        st.markdown(explanation)

                    # 显示多变量数据趋势
                    st.subheader("📊 多变量数据趋势")
                    fig = go.Figure()

                    # 温度
                    fig.add_trace(go.Scatter(
                        x=merged_df.index,
                        y=merged_df['temperature'],
                        name='温度',
                        line=dict(color='red')
                    ))

                    # 湿度
                    fig.add_trace(go.Scatter(
                        x=merged_df.index,
                        y=merged_df['humidity'],
                        name='湿度',
                        line=dict(color='blue'),
                        yaxis='y2'
                    ))

                    # 光照 (归一化)
                    if 'light' in merged_df.columns and merged_df['light'].max() > 0:
                        normalized_light = merged_df['light'] / merged_df['light'].max() * 50
                        fig.add_trace(go.Scatter(
                            x=merged_df.index,
                            y=normalized_light,
                            name='光照 (归一化)',
                            line=dict(color='orange', dash='dash')
                        ))

                    fig.update_layout(
                        title="温度、湿度、光照多维度趋势",
                        xaxis_title="时间",
                        yaxis_title="温度 (°C)",
                        yaxis2=dict(title="湿度 (%)", overlaying='y', side='right'),
                        hovermode='x unified'
                    )

                    st.plotly_chart(fig, use_container_width=True)

                    progress_bar.progress(100)
                    st.success("✅ 多变量分析完成！\n\n💡 **提示**: 基于随机森林模型的特征重要性结果，您可以了解各因素对预测目标的影响程度。")
                else:
                    st.warning("⚠️ 多变量预测失败，请检查数据质量")
                    progress_bar.empty()

            except Exception as e:
                st.error(f"❌ 多变量预测出错：{str(e)}")
                import traceback
                st.code(traceback.format_exc())
                progress_bar.empty()

        else:
            # 单变量预测逻辑
            log_operation(st.session_state['username'], "INFO", "数据预测",
                          f"类型：{data_type} 模型：{model_type} 天数：{prediction_days}")
            progress_bar = st.progress(0)
            st.write("预测进度：数据准备中...")

            # 修改：使用清洗后的数据而不是直接从数据库读取
            if 'data' in st.session_state:
                # 从 session_state 获取清洗后的数据
                cleaned_data = st.session_state['data'].copy()

                # 根据选择的数据类型提取相应列的数据
                if data_type == "空气温度":
                    if 'temperature' in cleaned_data.columns:
                        data = [(row['timestamp'], row['temperature']) for _, row in cleaned_data.iterrows() if
                                'temperature' in row and not pd.isna(row['temperature'])]
                    else:
                        st.error("清洗后的数据中未找到温度列")
                        return
                elif data_type == "空气湿度":
                    if 'humidity' in cleaned_data.columns:
                        data = [(row['timestamp'], row['humidity']) for _, row in cleaned_data.iterrows() if
                                'humidity' in row and not pd.isna(row['humidity'])]
                    else:
                        st.error("清洗后的数据中未找到湿度列")
                        return
                elif data_type == "土壤湿度":
                    if 'soil_moisture' in cleaned_data.columns:
                        data = [(row['timestamp'], row['soil_moisture']) for _, row in cleaned_data.iterrows() if
                                'soil_moisture' in row and not pd.isna(row['soil_moisture'])]
                    else:
                        st.error("清洗后的数据中未找到土壤湿度列")
                        return
                else:
                    st.error("不支持的数据类型")
                    return
            else:
                # 如果没有清洗后的数据，则从数据库读取（保持向后兼容）
                data = get_historical_data(session, data_type)

            # 更新进度条
            progress_bar.progress(33)
            st.write("预测进度：模型训练中...")

            # 调用预测模块
            historical_data, forecast_data, model_explanation, rmse = perform_prediction(
                data, actual_model_type, prediction_days, lstm_params)

            # 显示结果
            show_prediction_results(historical_data, forecast_data, model_explanation, rmse, data_type)

            # 更新进度条
            progress_bar.progress(100)
            st.success("预测完成")