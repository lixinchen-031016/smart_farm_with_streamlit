import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import tensorflow as tf
from keras.src.layers import Bidirectional, Dropout
from sklearn.preprocessing import MinMaxScaler
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.statespace.sarimax import SARIMAX
from tensorflow.keras.layers import LSTM, Dense
from tensorflow.keras.models import Sequential

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
    """LSTM模型预测实现 - 使用PyTorch框架"""
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import TensorDataset, DataLoader
    
    # 参数解包
    look_back = params.get('look_back', 7)
    epochs = params.get('epochs', 30)
    batch_size = params.get('batch_size', 32)
    units = params.get('units', 32)
    dropout_rate = params.get('dropout_rate', 0.2)
    learning_rate = params.get('learning_rate', 0.001)
    patience = params.get('patience', 5)  # 早停耐心值

    # 添加学习率调度器参数
    lr_scheduler_params = {
        'step_size': params.get('lr_step_size', 5),
        'gamma': params.get('lr_gamma', 0.5)
    }

    import time
    
    # 数据预处理
    df = pd.DataFrame(data, columns=['timestamp', 'value'])
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    
    # 更精细的数据预处理 - 添加移动平均平滑
    df['value'] = df['value'].rolling(window=6, min_periods=1).mean()
    
    # 只选择最近30天的数据
    df = df[df.index >= (df.index.max() - pd.Timedelta(days=30))]
    
    # 归一化 - 使用更鲁棒的归一化方法
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
    
    # 转换数据为PyTorch张量
    trainX_tensor = torch.FloatTensor(trainX)
    trainY_tensor = torch.FloatTensor(trainY).view(-1, 1)
    testX_tensor = torch.FloatTensor(testX)
    testY_tensor = torch.FloatTensor(testY).view(-1, 1)

    # 创建DataLoader
    train_dataset = TensorDataset(trainX_tensor, trainY_tensor)
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=False)

    # 定义改进后的PyTorch LSTM模型
    class LSTMModel(nn.Module):
        def __init__(self):
            super().__init__()
            self.lstm1 = nn.LSTM(input_size=1, hidden_size=units, 
                               batch_first=True, bidirectional=True)
            self.ln1 = nn.LayerNorm(units*2)  # 添加层归一化
            self.dropout1 = nn.Dropout(dropout_rate)
            self.lstm2 = nn.LSTM(input_size=units*2, hidden_size=units//2,
                               batch_first=True, bidirectional=True)
            self.ln2 = nn.LayerNorm(units)  # 添加层归一化
            self.dropout2 = nn.Dropout(dropout_rate)
            self.attention = nn.MultiheadAttention(embed_dim=units, num_heads=2)
            self.linear = nn.Linear(units, 1)
            
        def forward(self, x):
            x, _ = self.lstm1(x)
            x = self.ln1(x)  # 层归一化
            x = self.dropout1(x)
            x, _ = self.lstm2(x)
            x = self.ln2(x)  # 层归一化
            x = self.dropout2(x)
            x = x.transpose(0, 1)
            x, _ = self.attention(x, x, x)
            x = x.mean(dim=0)
            return self.linear(x)

    model = LSTMModel()
    criterion = nn.MSELoss()
    optimizer = optim.NAdam(model.parameters(), 
                          lr=learning_rate,
                          betas=(0.9, 0.999),
                          momentum_decay=0.004)
    
    # 添加学习率调度器
    scheduler = optim.lr_scheduler.StepLR(optimizer, 
                                        step_size=lr_scheduler_params['step_size'],
                                        gamma=lr_scheduler_params['gamma'])

    # 添加早停机制
    best_loss = float('inf')
    patience_counter = 0

    # 训练模型
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    start_time = time.time()
    for epoch in range(epochs):
        model.train()
        total_loss = 0
        for batch_x, batch_y in train_loader:
            optimizer.zero_grad()
            outputs = model(batch_x)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        
        # 更新学习率
        scheduler.step()
        
        # 早停检查
        current_loss = total_loss/len(train_loader)
        if current_loss < best_loss:
            best_loss = current_loss
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= patience:
                status_text.text(f"早停触发: 训练在第{epoch+1}轮停止")
                break
        
        # 更新进度条
        progress = (epoch + 1) / epochs
        progress_bar.progress(progress)
        status_text.text(f"训练中: {epoch+1}/{epochs} 轮次 (loss: {current_loss:.4f}, lr: {scheduler.get_last_lr()[0]:.6f})")
    
    training_time = time.time() - start_time

    # 在测试集上评估模型
    model.eval()
    with torch.no_grad():
        testPredict = model(testX_tensor).numpy()
    testPredict = scaler.inverse_transform(testPredict)
    testY_orig = scaler.inverse_transform(testY.reshape(-1, 1))
    
    # 计算测试集RMSE
    rmse = np.sqrt(np.mean((testPredict - testY_orig) ** 2))

    # 生成预测
    model.eval()
    inputs = dataset[-look_back:]
    predictions = []
    with torch.no_grad():
        for _ in range(prediction_days):
            x_input = torch.FloatTensor(inputs[-look_back:].reshape(1, look_back, 1))
            y_pred = model(x_input).numpy()[0][0]
            predictions.append(y_pred)
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
    
    # 更新模型解释文本
    explanation = f"""
    **LSTM模型(PyTorch)训练说明**  
    
    本次预测使用了改进的双向LSTM模型，主要优化点包括：
    
    **模型改进:**
    1. 使用PyTorch框架实现更灵活的模型架构
    2. 采用NAdam优化器(初始学习率:{learning_rate})
    3. 实现多头注意力机制增强时序特征提取
    4. 添加层归一化(LayerNorm)提高训练稳定性
    5. 使用学习率调度器(StepLR)动态调整学习率
    6. 实现早停机制(耐心值:{patience})防止过拟合
    
    **性能指标:**
    - 训练时间: {training_time:.2f}秒
    - 测试集RMSE: {rmse:.4f}
    - 训练轮次: {epoch+1}轮
    - 最终学习率: {scheduler.get_last_lr()[0]:.6f}
    """
    
    return df, forecast_df, explanation, rmse

def perform_prediction(data, model_type, prediction_days, lstm_params=None):
    df = pd.DataFrame(data, columns=['timestamp', 'value'])
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)

    # 农业数据预处理 - 处理异常值和缺失值
    df = df.interpolate(method='time')  # 时间序列插值
    df['value'] = np.where(df['value'] > df['value'].quantile(0.99), 
                          df['value'].median(), 
                          df['value'])
    
    # 只选择最近30天的数据
    df = df[df.index >= (df.index.max() - pd.Timedelta(days=30))]

    model_explanation = ""  # 初始化解释字符串
    rmse = 0.0  # 初始化RMSE
    
    if model_type == "ARIMA":
        # 优化ARIMA参数，更适合农业数据
        model = ARIMA(df['value'], order=(2, 1, 2))
        model_fit = model.fit()
        forecast = model_fit.forecast(steps=prediction_days)
        
        fitted = model_fit.fittedvalues
        rmse = np.sqrt(np.mean((df['value'] - fitted) ** 2))
        
        model_explanation = f"""
        **ARIMA模型(2,1,2)训练说明**
        
        1. 专门针对农业环境数据优化参数
        2. 自动处理了数据中的异常值
        3. 考虑了农业数据的短期依赖特性
        
        **性能指标:**
        - 历史数据拟合RMSE: {rmse:.4f}
        - 使用的数据范围: 最近30天数据
        - 预测天数: {prediction_days}天
        
        **农业数据特性处理:**
        - 自动填充缺失数据
        - 平滑异常值
        - 保留季节性特征
        """
        
        forecast_dates = pd.date_range(start=df.index[-1], periods=prediction_days + 1, freq='D')[1:]
        forecast_df = pd.DataFrame({'timestamp': forecast_dates, 'value': forecast})
        return df, forecast_df, model_explanation, rmse
        
    elif model_type == "SARIMA":
        # 优化SARIMA季节性参数，更适合农业数据
        model = SARIMAX(df['value'], order=(1, 1, 1), seasonal_order=(1, 1, 1, 24))
        model_fit = model.fit()
        forecast = model_fit.forecast(steps=prediction_days)
        
        fitted = model_fit.fittedvalues
        rmse = np.sqrt(np.mean((df['value'] - fitted) ** 2))
        
        model_explanation = f"""
        **SARIMA模型(1,1,1)(1,1,1,24)训练说明**
        
        1. 24小时季节性周期更适合农业环境数据
        2. 简化模型参数提高稳定性
        3. 考虑了农业数据的昼夜周期性
        
        **性能指标:**
        - 历史数据拟合RMSE: {rmse:.4f}
        - 使用的数据范围: 最近30天数据
        - 预测天数: {prediction_days}天
        
        **农业数据特性处理:**
        - 24小时季节性周期
        - 自动处理昼夜变化
        - 优化了温度/湿度等数据的预测
        """
        
        forecast_dates = pd.date_range(start=df.index[-1], periods=prediction_days + 1, freq='D')[1:]
        forecast_df = pd.DataFrame({'timestamp': forecast_dates, 'value': forecast})
        return df, forecast_df, model_explanation, rmse
        
    elif model_type == "LSTM":
        # 调用LSTM预测函数
        return lstm_prediction(data, prediction_days, lstm_params or {})
        
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
    return query.all()

def prepare_prediction_ui():
    """准备预测UI组件"""
    data_type = st.selectbox("选择预测的数据类型", ["空气温度", "空气湿度", "土壤湿度"])
    model_type = st.selectbox("选择预测模型", ["ARIMA", "SARIMA", "LSTM"])
    prediction_days = st.number_input("预测天数", min_value=1, max_value=30, value=7)
    
    lstm_params = {}
    if model_type in ["LSTM"]:
        with st.expander("LSTM参数配置"):
            lstm_params['look_back'] = st.slider("时间窗口大小", 1, 30, 7, 
                help="模型观察的历史数据点数")
            lstm_params['epochs'] = st.slider("训练轮次", 10, 200, 10)
            lstm_params['batch_size'] = st.slider("批次大小", 8, 64, 32)
            lstm_params['units'] = st.slider("LSTM单元数", 16, 128, 16)
    
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
