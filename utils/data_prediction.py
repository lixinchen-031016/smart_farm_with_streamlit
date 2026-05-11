import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime

import models
from auth import session
from utils.logger import log_operation
from utils.predictions import prepare_prediction_ui, multivariate_prediction, get_historical_data, perform_prediction, \
    show_prediction_results
from utils.prediction_auto_save import auto_save_prediction, get_prediction_history


def show_prediction_history():
    """显示预测历史记录

    展示系统中存储的预测历史记录，包括总预测次数、今日预测次数和平均RMSE等统计信息，
    并以表格形式展示详细的历史预测数据。

    Returns:
        None: 无返回值，直接在Streamlit页面上显示内容

    Raises:
        Exception: 加载历史记录失败时会捕获并显示错误信息
    """
    st.subheader("📚 预测历史记录")

    try:
        history = get_prediction_history(limit=50)

        if not history:
            st.info("暂无预测历史记录")
            return

        # 显示统计信息
        stats_col1, stats_col2, stats_col3 = st.columns(3)
        with stats_col1:
            st.metric("总预测次数", len(history))
        with stats_col2:
            recent_count = sum(1 for h in history if h.get('created_at', '').startswith(
                pd.Timestamp.now().strftime('%Y-%m-%d')))
            st.metric("今日预测", recent_count)
        with stats_col3:
            avg_rmse = sum(h.get('rmse', 0) for h in history if h.get('rmse')) / max(
                sum(1 for h in history if h.get('rmse')), 1)
            st.metric("平均RMSE", f"{avg_rmse:.4f}")

        # 显示历史记录表格
        history_df = pd.DataFrame(history)
        if 'created_at' in history_df.columns:
            history_df['created_at'] = pd.to_datetime(history_df['created_at']).dt.strftime('%Y-%m-%d %H:%M:%S')

        # 选择要显示的列
        display_cols = ['prediction_id', 'prediction_type', 'model_type', 'prediction_days',
                        'rmse', 'r_squared', 'created_at']
        available_cols = [col for col in display_cols if col in history_df.columns]

        st.dataframe(history_df[available_cols], use_container_width=True)

        # 自动存储功能已启用，所有预测结果会自动保存到 predictions_exports 目录

    except Exception as e:
        st.error(f"加载历史记录失败: {str(e)}")


def data_prediction():
    """显示数据预测页面，允许用户进行本地数据预测

    提供数据预测功能，支持单变量时间序列预测和多变量耦合预测两种模式。
    用户可以选择预测数据类型、模型类型和预测天数，系统会根据选择执行相应的预测
    并展示预测结果、特征重要性分析和趋势图表。同时提供预测历史记录查看功能。

    Returns:
        None: 无返回值，直接在Streamlit页面上显示内容

    Raises:
        Exception: 预测过程中出现错误时会捕获并显示错误信息
    """
    if not st.session_state.get('logged_in'):
        st.query_params.page = "login"
        return

    st.title("数据预测")

    # 添加标签页
    tab1, tab2 = st.tabs(["🚀 执行预测", "📚 预测历史"])

    with tab2:
        show_prediction_history()

    with tab1:
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
                    merged_df, rf_temp, rf_humid, feature_importance, explanation, forecast_df = multivariate_prediction(
                        temp_data, humid_data, light_data, prediction_days, lstm_params
                    )

                    if merged_df is not None and forecast_df is not None:
                        progress_bar.progress(66)
                        st.write("预测进度：生成可视化结果...")

                        # 显示特征重要性
                        with st.expander("🔍 特征重要性分析", expanded=True):
                            st.markdown(explanation)

                        # 计算预测统计数据
                        forecast_stats = {
                            'temp_mean': forecast_df['temperature'].mean(),
                            'temp_min': forecast_df['temperature'].min(),
                            'temp_max': forecast_df['temperature'].max(),
                            'humid_mean': forecast_df['humidity'].mean(),
                            'humid_min': forecast_df['humidity'].min(),
                            'humid_max': forecast_df['humidity'].max(),
                            'light_mean': forecast_df['light'].mean() if 'light' in forecast_df.columns else 0,
                        }
                        
                        # 显示预测统计摘要
                        st.subheader("📈 预测数据时序分析")
                        stats_col1, stats_col2, stats_col3 = st.columns(3)
                        with stats_col1:
                            st.metric(
                                "预测平均温度",
                                f"{forecast_stats['temp_mean']:.1f}°C",
                                delta=f"{forecast_stats['temp_max'] - forecast_stats['temp_min']:.1f}°C 波动"
                            )
                        with stats_col2:
                            st.metric(
                                "预测平均湿度",
                                f"{forecast_stats['humid_mean']:.1f}%",
                                delta=f"{forecast_stats['humid_max'] - forecast_stats['humid_min']:.1f}% 波动"
                            )
                        with stats_col3:
                            if 'light' in forecast_df.columns:
                                st.metric(
                                    "预测平均光照",
                                    f"{forecast_stats['light_mean']:.0f}",
                                    help="光照强度平均值"
                                )
                        
                        # 创建多子图展示时序变化
                        st.markdown("### 🔍 各变量时序变化趋势")
                        
                        # 子图1: 温度时序变化
                        fig_temp = go.Figure()
                        
                        # 历史温度
                        fig_temp.add_trace(go.Scatter(
                            x=merged_df.index,
                            y=merged_df['temperature'],
                            name='历史数据',
                            line=dict(color='#FF6B6B', width=2),
                            mode='lines+markers',
                            marker=dict(size=4)
                        ))
                        
                        # 预测温度
                        fig_temp.add_trace(go.Scatter(
                            x=forecast_df.index,
                            y=forecast_df['temperature'],
                            name='预测数据',
                            line=dict(color='#FF6B6B', width=2, dash='dash'),
                            mode='lines+markers',
                            marker=dict(size=4, symbol='diamond')
                        ))
                        
                        # 添加预测区域的背景色
                        if len(forecast_df) > 0:
                            fig_temp.add_vrect(
                                x0=forecast_df.index[0],
                                x1=forecast_df.index[-1],
                                fillcolor="#FF6B6B",
                                opacity=0.08,
                                layer="below",
                                line_width=0,
                                annotation_text="预测区间",
                                annotation_position="top left"
                            )
                        
                        fig_temp.update_layout(
                            title="🌡️ 温度时序变化趋势",
                            xaxis_title="时间",
                            yaxis_title="温度 (°C)",
                            hovermode='x unified',
                            height=350,
                            showlegend=True,
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                        )
                        
                        st.plotly_chart(fig_temp, use_container_width=True)
                        
                        # 子图2: 湿度时序变化
                        fig_humid = go.Figure()
                        
                        # 历史湿度
                        fig_humid.add_trace(go.Scatter(
                            x=merged_df.index,
                            y=merged_df['humidity'],
                            name='历史数据',
                            line=dict(color='#4ECDC4', width=2),
                            mode='lines+markers',
                            marker=dict(size=4)
                        ))
                        
                        # 预测湿度
                        fig_humid.add_trace(go.Scatter(
                            x=forecast_df.index,
                            y=forecast_df['humidity'],
                            name='预测数据',
                            line=dict(color='#4ECDC4', width=2, dash='dash'),
                            mode='lines+markers',
                            marker=dict(size=4, symbol='diamond')
                        ))
                        
                        # 添加预测区域的背景色
                        if len(forecast_df) > 0:
                            fig_humid.add_vrect(
                                x0=forecast_df.index[0],
                                x1=forecast_df.index[-1],
                                fillcolor="#4ECDC4",
                                opacity=0.08,
                                layer="below",
                                line_width=0,
                                annotation_text="预测区间",
                                annotation_position="top left"
                            )
                        
                        fig_humid.update_layout(
                            title="💧 湿度时序变化趋势",
                            xaxis_title="时间",
                            yaxis_title="湿度 (%)",
                            hovermode='x unified',
                            height=350,
                            showlegend=True,
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                        )
                        
                        st.plotly_chart(fig_humid, use_container_width=True)
                        
                        # 子图3: 光照时序变化（如果有光照数据）
                        if 'light' in merged_df.columns and 'light' in forecast_df.columns:
                            fig_light = go.Figure()
                            
                            # 历史光照
                            fig_light.add_trace(go.Scatter(
                                x=merged_df.index,
                                y=merged_df['light'],
                                name='历史数据',
                                line=dict(color='#FFA500', width=2),
                                mode='lines+markers',
                                marker=dict(size=4)
                            ))
                            
                            # 预测光照
                            fig_light.add_trace(go.Scatter(
                                x=forecast_df.index,
                                y=forecast_df['light'],
                                name='预测数据',
                                line=dict(color='#FFA500', width=2, dash='dash'),
                                mode='lines+markers',
                                marker=dict(size=4, symbol='diamond')
                            ))
                            
                            # 添加预测区域的背景色
                            if len(forecast_df) > 0:
                                fig_light.add_vrect(
                                    x0=forecast_df.index[0],
                                    x1=forecast_df.index[-1],
                                    fillcolor="#FFA500",
                                    opacity=0.08,
                                    layer="below",
                                    line_width=0,
                                    annotation_text="预测区间",
                                    annotation_position="top left"
                                )
                            
                            fig_light.update_layout(
                                title="☀️ 光照强度时序变化趋势",
                                xaxis_title="时间",
                                yaxis_title="光照强度",
                                hovermode='x unified',
                                height=350,
                                showlegend=True,
                                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                            )
                            
                            st.plotly_chart(fig_light, use_container_width=True)
                        
                        # 综合对比图（可选）
                        with st.expander("📊 查看多维度综合对比图", expanded=False):
                            fig_combined = go.Figure()
                            
                            # 归一化后的历史数据
                            if merged_df['temperature'].max() > 0:
                                norm_temp_hist = merged_df['temperature'] / merged_df['temperature'].max() * 100
                                fig_combined.add_trace(go.Scatter(
                                    x=merged_df.index,
                                    y=norm_temp_hist,
                                    name='温度 (历史)',
                                    line=dict(color='red', width=1.5)
                                ))
                            
                            if merged_df['humidity'].max() > 0:
                                norm_humid_hist = merged_df['humidity'] / merged_df['humidity'].max() * 100
                                fig_combined.add_trace(go.Scatter(
                                    x=merged_df.index,
                                    y=norm_humid_hist,
                                    name='湿度 (历史)',
                                    line=dict(color='blue', width=1.5)
                                ))
                            
                            # 归一化后的预测数据
                            if len(forecast_df) > 0:
                                if forecast_df['temperature'].max() > 0:
                                    norm_temp_pred = forecast_df['temperature'] / max(merged_df['temperature'].max(), 1) * 100
                                    fig_combined.add_trace(go.Scatter(
                                        x=forecast_df.index,
                                        y=norm_temp_pred,
                                        name='温度 (预测)',
                                        line=dict(color='red', width=1.5, dash='dash')
                                    ))
                                
                                if forecast_df['humidity'].max() > 0:
                                    norm_humid_pred = forecast_df['humidity'] / max(merged_df['humidity'].max(), 1) * 100
                                    fig_combined.add_trace(go.Scatter(
                                        x=forecast_df.index,
                                        y=norm_humid_pred,
                                        name='湿度 (预测)',
                                        line=dict(color='blue', width=1.5, dash='dash')
                                    ))
                            
                            fig_combined.update_layout(
                                title="归一化综合对比图（相对变化趋势）",
                                xaxis_title="时间",
                                yaxis_title="相对值 (%)",
                                hovermode='x unified',
                                height=400,
                                showlegend=True
                            )
                            
                            st.plotly_chart(fig_combined, use_container_width=True)
                        
                        # 显示预测数据表格
                        with st.expander("📋 查看预测数据详情", expanded=False):
                            st.markdown(f"### 未来 {prediction_days} 天预测数据")
                            forecast_display = forecast_df.reset_index()
                            forecast_display.columns = ['时间', '温度 (°C)', '湿度 (%)', '光照强度']
                            forecast_display['时间'] = forecast_display['时间'].dt.strftime('%Y-%m-%d %H:%M:%S')
                            st.dataframe(forecast_display, use_container_width=True)
                            
                            # 提供下载按钮
                            csv_data = forecast_display.to_csv(index=False, encoding='utf-8-sig')
                            st.download_button(
                                label="📥 下载预测数据 (CSV)",
                                data=csv_data,
                                file_name=f"multivariate_forecast_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                mime="text/csv"
                            )

                        # 自动保存多变量预测结果
                        progress_bar.progress(90)
                        st.write("预测进度：自动保存结果...")

                        try:
                            # 计算R²值（使用温度的R²作为代表）
                            from scipy import stats
                            if len(forecast_df) > 1 and 'temperature' in forecast_df.columns:
                                forecast_values = forecast_df['temperature'].values
                                x = range(len(forecast_values))
                                slope, intercept, r_value, p_value, std_err = stats.linregress(x, forecast_values)
                                r_squared = float(r_value ** 2)  # 确保是浮点数
                            else:
                                r_squared = 0.0

                            # 准备历史数据用于保存（合并三个变量）
                            historical_combined = merged_df[['temperature', 'humidity', 'light']].copy()
                            historical_combined.index.name = 'timestamp'
                            
                            # 准备预测数据用于保存
                            forecast_combined = forecast_df[['temperature', 'humidity', 'light']].copy()
                            forecast_combined.index.name = 'timestamp'

                            # 自动保存预测结果
                            save_result = auto_save_prediction(
                                historical_data=historical_combined,
                                forecast_data=forecast_combined,
                                prediction_type="多变量耦合预测",
                                model_type="RandomForest-Multivariate",
                                prediction_days=prediction_days,
                                model_explanation=explanation,
                                rmse=0.0,  # 多变量模型不单独计算RMSE
                                r_squared=float(r_squared),  # 确保转换为浮点数
                                additional_metrics={
                                    "prediction_mode": "多变量耦合预测",
                                    "params": lstm_params,
                                    "variables": ["temperature", "humidity", "light"],
                                    "feature_importance": feature_importance.to_dict('records') if feature_importance is not None else []
                                },
                                username=st.session_state.get('username', 'system')
                            )

                            if save_result.get("status") == "success":
                                st.success(f"✅ 多变量预测结果已自动保存")
                                st.caption(f"📁 预测ID: {save_result.get('prediction_id')}")
                            else:
                                st.warning(f"⚠️ 自动保存失败: {save_result.get('message', '未知错误')}")

                        except Exception as save_error:
                            st.warning(f"⚠️ 自动保存过程出错: {str(save_error)}")
                            import traceback
                            st.code(traceback.format_exc())
                            log_operation(st.session_state.get('username', 'system'), "ERROR",
                                          "多变量预测结果自动保存失败", str(save_error))

                        progress_bar.progress(100)
                        st.success("✅ 多变量预测完成！\n\n💡 **提示**: 上方图表展示了各变量的时序变化趋势，虚线区域为预测区间。您可以观察预测期间的周期性模式和变化趋势。")
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

                # 自动保存预测结果
                progress_bar.progress(90)
                st.write("预测进度：自动保存结果...")

                try:
                    # 计算R²值
                    from scipy import stats
                    if len(forecast_data) > 1 and 'value' in forecast_data.columns:
                        forecast_values = forecast_data['value'].values
                        x = range(len(forecast_values))
                        slope, intercept, r_value, p_value, std_err = stats.linregress(x, forecast_values)
                        r_squared = r_value ** 2
                    else:
                        r_squared = 0.0

                    # 自动保存预测结果
                    save_result = auto_save_prediction(
                        historical_data=historical_data,
                        forecast_data=forecast_data,
                        prediction_type=data_type,
                        model_type=model_type,
                        prediction_days=prediction_days,
                        model_explanation=model_explanation,
                        rmse=rmse,
                        r_squared=r_squared,
                        additional_metrics={
                            "prediction_mode": "单变量时间序列预测",
                            "params": lstm_params
                        },
                        username=st.session_state.get('username', 'system')
                    )

                    if save_result.get("status") == "success":
                        st.success(f"✅ 预测结果已自动保存")
                        st.caption(f"📁 预测ID: {save_result.get('prediction_id')}")
                    else:
                        st.warning(f"⚠️ 自动保存失败: {save_result.get('message', '未知错误')}")

                except Exception as save_error:
                    st.warning(f"⚠️ 自动保存过程出错: {str(save_error)}")
                    log_operation(st.session_state.get('username', 'system'), "ERROR",
                                  "预测结果自动保存失败", str(save_error))

                # 更新进度条
                progress_bar.progress(100)
                st.success("预测完成")
