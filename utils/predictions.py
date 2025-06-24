import pandas as pd
import numpy as np
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.statespace.sarimax import SARIMAX
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from sklearn.preprocessing import MinMaxScaler
import streamlit as st

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
    
    return df, forecast_df, explanation

def perform_prediction(data, model_type, prediction_days, lstm_params=None):
    df = pd.DataFrame(data, columns=['timestamp', 'value'])
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)

    model_explanation = ""  # 初始化解释字符串
    
    if model_type == "ARIMA":
        model = ARIMA(df['value'], order=(5, 1, 0))
        model_fit = model.fit()
        forecast = model_fit.forecast(steps=prediction_days)
        forecast_dates = pd.date_range(start=df.index[-1], periods=prediction_days + 1, freq='D')[1:]
        forecast_df = pd.DataFrame({'timestamp': forecast_dates, 'value': forecast})
        return df, forecast_df, model_explanation
        
    elif model_type == "SARIMA":
        model = SARIMAX(df['value'], order=(5, 1, 0), seasonal_order=(1, 1, 1, 12))
        model_fit = model.fit()
        forecast = model_fit.forecast(steps=prediction_days)
        forecast_dates = pd.date_range(start=df.index[-1], periods=prediction_days + 1, freq='D')[1:]
        forecast_df = pd.DataFrame({'timestamp': forecast_dates, 'value': forecast})
        return df, forecast_df, model_explanation
        
    elif model_type == "LSTM":
        # 调用LSTM预测函数
        return lstm_prediction(data, prediction_days, lstm_params or {})
        
    return df, pd.DataFrame(), model_explanation