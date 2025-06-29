import pandas as pd
import numpy as np
import plotly.graph_objects as go
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.statespace.sarimax import SARIMAX
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from sklearn.preprocessing import MinMaxScaler
import streamlit as st
import models


def create_dataset(dataset, look_back=1):
    """创建LSTM训练数据集"""
    dataX, dataY = [], []
    for i in range(len(dataset)-look_back-1):
        a = dataset[i:(i+look_back), 0]
        dataX.append(a)
        dataY.append(dataset[i + look_back, 0])
    return np.array(dataX), np.array(dataY)

def lstm_prediction(data, prediction_days, params):
    """LSTM模型预测实现"""
    # 参数解包
    look_back = params.get('look_back', 7)
    epochs = params.get('epochs', 50)
    batch_size = params.get('batch_size', 16)
    units = params.get('units', 50)
    
    # 数据预处理
    df = pd.DataFrame(data, columns=['timestamp', 'value'])
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    
    # 归一化
    scaler = MinMaxScaler(feature_range=(0, 1))
    dataset = scaler.fit_transform(df[['value']])
    
    # 创建训练集
    train_size = int(len(dataset) * 0.8)
    train, test = dataset[0:train_size,:], dataset[train_size:len(dataset),:]
    
    # 创建时间窗口数据集
    trainX, trainY = create_dataset(train, look_back)
    testX, testY = create_dataset(test, look_back)
    
    # 调整数据形状 [样本数, 时间步长, 特征数]
    trainX = np.reshape(trainX, (trainX.shape[0], trainX.shape[1], 1))
    testX = np.reshape(testX, (testX.shape[0], testX.shape[1], 1))
    
    # 创建LSTM模型
    model = Sequential()
    model.add(LSTM(units, input_shape=(look_back, 1)))
    model.add(Dense(1))
    model.compile(loss='mean_squared_error', optimizer='adam')
    
    # 训练模型
    model.fit(trainX, trainY, epochs=epochs, batch_size=batch_size, verbose=0)
    
    # 在测试集上评估模型
    testPredict = model.predict(testX, verbose=0)
    testPredict = scaler.inverse_transform(testPredict)
    testY_orig = scaler.inverse_transform(testY.reshape(-1, 1))
    
    # 计算测试集RMSE
    rmse = np.sqrt(np.mean((testPredict - testY_orig) ** 2))
    
    # 生成预测
    inputs = dataset[-look_back:]
    predictions = []
    
    for _ in range(prediction_days):
        x_input = inputs[-look_back:].reshape(1, look_back, 1)
        y_pred = model.predict(x_input, verbose=0)
        predictions.append(y_pred[0][0])
        inputs = np.append(inputs, y_pred)
    
    # 反归一化
    predictions = scaler.inverse_transform(np.array(predictions).reshape(-1, 1))
    
    # 生成预测时间戳
    last_date = df.index[-1]
    forecast_dates = pd.date_range(
        start=last_date + pd.Timedelta(days=1), 
        periods=prediction_days
    )
    
    forecast_df = pd.DataFrame({
        'timestamp': forecast_dates,
        'value': predictions.flatten()
    })
    
    # 生成自然语言解释
    explanation = f"""
    **LSTM模型训练说明**  
    
    本次预测使用了长短期记忆网络(LSTM)模型，这是一种专门用于处理时间序列数据的循环神经网络。  
    
    **模型配置参数:**  
    - 时间窗口大小: {look_back}天 (模型观察的历史数据点数)  
    - LSTM单元数: {units}个  
    - 训练轮次: {epochs}次  
    - 批次大小: {batch_size}  
    
    **训练过程:**  
    1. 数据预处理: 对历史数据进行了归一化处理，将所有值转换到0-1范围内  
    2. 数据集划分: 使用80%的数据训练模型，20%的数据验证模型效果  
    3. 时间窗口构造: 基于{look_back}天的时间窗口创建训练样本  
    4. 模型训练: 使用均方误差(MSE)作为损失函数，Adam优化器进行优化  
    
    **预测说明:**  
    模型基于最近{look_back}天的数据生成未来{prediction_days}天的预测值。  
    LSTM特别适合捕捉时间序列中的长期依赖关系，能够有效处理农业环境数据的周期性变化。
    """
    
    # 更新解释文本，包含RMSE
    explanation += f"\n\n**模型评价指标:**  \n- 测试集RMSE: {rmse:.4f}"
    
    return df, forecast_df, explanation, rmse

def hybrid_prediction(data, prediction_days, lstm_params):
    """混合预测：融合SARIMA和LSTM的预测结果"""
    # 调用SARIMA预测
    _, sarima_forecast, sarima_explanation, sarima_rmse = perform_prediction(data, "SARIMA", prediction_days, {})
    
    # 调用LSTM预测
    _, lstm_forecast, lstm_explanation, lstm_rmse = lstm_prediction(data, prediction_days, lstm_params)
    
    # 确保两个预测的时间戳对齐
    sarima_forecast = sarima_forecast.set_index('timestamp')
    lstm_forecast = lstm_forecast.set_index('timestamp')
    
    # 合并预测结果（加权平均）
    combined_forecast = (sarima_forecast['value'] * 0.3 + lstm_forecast['value'] * 0.7)
    
    # 创建结果DataFrame
    forecast_df = pd.DataFrame({
        'timestamp': combined_forecast.index,
        'value': combined_forecast.values
    })
    
    # 计算组合RMSE
    hybrid_rmse = (sarima_rmse + lstm_rmse) / 2
    
    # 更新解释文本
    explanation = f"""
    **混合预测模型说明**  
    
    本次预测使用了SARIMA和LSTM模型的融合结果，结合了两种模型的优势：
    - **SARIMA模型**：擅长捕捉时间序列的季节性和趋势性特征
    - **LSTM模型**：擅长处理非线性关系和长期依赖
    
    **融合方法：**  
    采用加权平均法，SARIMA和LSTM预测结果各占30%，70%权重。
    
    **模型配置参数:**  
    - LSTM时间窗口大小: {lstm_params.get('look_back', 7)}天  
    - LSTM单元数: {lstm_params.get('units', 50)}个  
    - LSTM训练轮次: {lstm_params.get('epochs', 50)}次  
    - LSTM批次大小: {lstm_params.get('batch_size', 16)}  
    """
    
    return sarima_forecast, forecast_df, explanation, hybrid_rmse

def perform_prediction(data, model_type, prediction_days, lstm_params=None):
    df = pd.DataFrame(data, columns=['timestamp', 'value'])
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)

    model_explanation = ""  # 初始化解释字符串
    rmse = 0.0  # 初始化RMSE
    
    if model_type == "ARIMA":
        model = ARIMA(df['value'], order=(5, 1, 0))
        model_fit = model.fit()
        forecast = model_fit.forecast(steps=prediction_days)
        
        # 计算历史数据拟合的RMSE
        fitted = model_fit.fittedvalues
        rmse = np.sqrt(np.mean((df['value'] - fitted) ** 2))
        
        # 更新解释文本
        model_explanation = f"**ARIMA模型训练说明**  \n使用(5,1,0)参数配置  \n**历史数据拟合RMSE: {rmse:.4f}**"
        
        forecast_dates = pd.date_range(start=df.index[-1], periods=prediction_days + 1, freq='D')[1:]
        forecast_df = pd.DataFrame({'timestamp': forecast_dates, 'value': forecast})
        return df, forecast_df, model_explanation, rmse
        
    elif model_type == "SARIMA":
        model = SARIMAX(df['value'], order=(5, 1, 0), seasonal_order=(1, 1, 1, 12))
        model_fit = model.fit()
        forecast = model_fit.forecast(steps=prediction_days)
        
        # 计算历史数据拟合的RMSE
        fitted = model_fit.fittedvalues
        rmse = np.sqrt(np.mean((df['value'] - fitted) ** 2))
        
        # 更新解释文本
        model_explanation = f"**SARIMA模型训练说明**  \n使用(5,1,0)(1,1,1,12)参数配置  \n**历史数据拟合RMSE: {rmse:.4f}**"
        
        forecast_dates = pd.date_range(start=df.index[-1], periods=prediction_days + 1, freq='D')[1:]
        forecast_df = pd.DataFrame({'timestamp': forecast_dates, 'value': forecast})
        return df, forecast_df, model_explanation, rmse
        
    elif model_type == "LSTM":
        # 调用LSTM预测函数
        return lstm_prediction(data, prediction_days, lstm_params or {})
        
    elif model_type == "混合预测(SARIMA+LSTM)":
        return hybrid_prediction(data, prediction_days, lstm_params or {})
        
    return df, pd.DataFrame(), model_explanation, rmse

def get_historical_data(session, data_type):
    """获取历史数据"""
    if data_type == "空气温度":
        query = session.query(models.AirTemperatureHumidity.timestamp,
                             models.AirTemperatureHumidity.temperature).order_by(
            models.AirTemperatureHumidity.timestamp)
    elif data_type == "空气湿度":
        query = session.query(models.AirTemperatureHumidity.timestamp,
                             models.AirTemperatureHumidity.humidity).order_by(
            models.AirTemperatureHumidity.timestamp)
    elif data_type == "土壤湿度":
        query = session.query(models.SoilMoisture.timestamp, models.SoilMoisture.value).order_by(
            models.SoilMoisture.timestamp)
    elif data_type == "光照强度":
        query = session.query(models.LightIntensity.timestamp, models.LightIntensity.value).order_by(
            models.LightIntensity.timestamp)
    return query.all()

def prepare_prediction_ui():
    """准备预测UI组件"""
    data_type = st.selectbox("选择预测的数据类型", ["空气温度", "空气湿度", "土壤湿度", "光照强度"])
    model_type = st.selectbox("选择预测模型", ["ARIMA", "SARIMA", "LSTM", "混合预测(SARIMA+LSTM)"])
    prediction_days = st.number_input("预测天数", min_value=1, max_value=30, value=7)
    
    lstm_params = {}
    if model_type in ["LSTM", "混合预测(SARIMA+LSTM)"]:
        with st.expander("LSTM参数配置"):
            lstm_params['look_back'] = st.slider("时间窗口大小", 1, 30, 7, 
                help="模型观察的历史数据点数")
            lstm_params['epochs'] = st.slider("训练轮次", 10, 200, 50)
            lstm_params['batch_size'] = st.slider("批次大小", 8, 64, 16)
            lstm_params['units'] = st.slider("LSTM单元数", 16, 128, 50)
    
    return data_type, model_type, prediction_days, lstm_params

def show_prediction_results(historical_data, forecast_data, model_explanation, rmse, data_type):
    """显示预测结果"""
    if model_explanation:
        with st.expander("模型训练说明", expanded=True):
            st.markdown(model_explanation)
            st.markdown(f"**模型评价指标:**")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("RMSE (均方根误差)", f"{rmse:.4f}")
            with col2:
                st.markdown("RMSE值越小表示模型预测精度越高")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=historical_data.index, y=historical_data['value'], mode='lines', name='历史数据'))
    fig.add_trace(go.Scatter(x=forecast_data['timestamp'], y=forecast_data['value'], mode='lines', name='预测数据'))
    fig.update_layout(
        title=f"{data_type} 预测结果",
        xaxis_title="时间",
        yaxis_title="值",
        legend_title="数据类型"
    )
    st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("预测结果评价")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("预测天数", len(forecast_data))
    with col2:
        st.metric("历史数据量", len(historical_data))
    with col3:
        st.metric("模型精度 (RMSE)", f"{rmse:.4f}", 
                 delta="优" if rmse < 1.0 else "良" if rmse < 2.5 else "一般",
                 delta_color="inverse")
