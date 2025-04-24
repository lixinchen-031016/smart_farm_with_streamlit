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