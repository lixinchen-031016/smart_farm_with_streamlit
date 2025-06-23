import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.statespace.sarimax import SARIMAX


def perform_prediction(data, model_type, prediction_days):
    df = pd.DataFrame(data, columns=['timestamp', 'value'])
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)

    if model_type == "ARIMA":
        model = ARIMA(df['value'], order=(5, 1, 0))
    elif model_type == "SARIMA":
        model = SARIMAX(df['value'], order=(5, 1, 0), seasonal_order=(1, 1, 1, 12))

    model_fit = model.fit()
    forecast = model_fit.forecast(steps=prediction_days)

    forecast_dates = pd.date_range(start=df.index[-1], periods=prediction_days + 1, freq='D')[1:]
    forecast_df = pd.DataFrame({'timestamp': forecast_dates, 'value': forecast})

    return df, forecast_df
'''
ARIMA与SARIMA的区别及预测用途：
区别
季节性处理：
ARIMA (ARIMA)：适用于非季节性时间序列，通过差分消除趋势后建模
SARIMA (SARIMAX)：扩展ARIMA支持季节性模式，通过双重差分（常规+季节性）处理周期波动
参数结构：
ARIMA参数：(p,d,q) 三元组
p: 自回归阶数
d: 差分次数
q: 移动平均阶数
SARIMA参数：(p,d,q)(P,D,Q,S) 六元组
新增：P季节自回归阶数，D季节差分次数，Q季节移动平均阶数，S季节周期长度（如12=年周期）
数学表达：
ARIMA: △yₜ = c + φ₁△yₜ₋₁ + ... + φₚ△yₜ₋ₚ + εₜ + θ₁εₜ₋₁ + ... + θ_qεₜ₋q
SARIMA: 在ARIMA基础上叠加季节性算子：Φ_P(B^S)∇^D_S y_t = ...
预测用途
ARIMA适用场景：
预测无明显季节波动的数据（如股票价格、随机生成序列）
案例：土壤湿度短期预测（假设无昼夜节律影响）
SARIMA适用场景：
预测具有固定周期模式的数据（如月度气温、季度农产品产量）
案例：农作物产量年度预测（代码中seasonal_order=(1,1,1,12)即针对年周期）
模型选择依据：
检查ACF/PACF图：SARIMA会出现周期性显著滞后项
检验季节性单位根（如CHTest）
业务知识判断（如种植业存在明显生长周期）
'''