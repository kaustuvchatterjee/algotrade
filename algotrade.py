import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime as dt
from datetime import timedelta
import pytz

tz=pytz.timezone('Asia/Kolkata')

def get_tickers(file_path='tickers.csv'):
    try:
        df = pd.read_csv(file_path)
        tickers=df['ticker'].to_list()
        ticker_names = []
        for ticker in tickers:
            t = yf.Ticker(ticker)
            ticker_names.append(t.info['shortName'])
    except:
        tickers =['^NSEI']
        ticker_names=['NIFTY 50']
    
    return tickers, ticker_names

def get_ticker_data(ticker, duration):
    try:
        end_date = dt.today()
        end_date = end_date.astimezone(tz=tz)
        start_date = end_date + timedelta(days=-duration)
        # start_date = start_date.astimezone('Asia/Kolkata')
        data = yf.download(ticker, start=start_date, end=end_date)
        # data.index = data.index.tz_localize('Asia/Kolkata')
        status = 1
    except Exception as error:
        status = 0
        data=[]
        print(error)

    return data, status

def get_rsi(data):
    change = data["Close"].diff()
    # change.dropna(inplace=True)
    change_up = change.copy()
    change_down = change.copy()

    # 
    change_up[change_up<0] = 0
    change_down[change_down>0] = 0

    # Verify that we did not make any mistakes
    change.equals(change_up+change_down)

    # Calculate the rolling average of average up and average down
    avg_up = change_up.rolling(14).mean()
    avg_down = change_down.rolling(14).mean().abs()

    rsi = 100 * avg_up / (avg_up + avg_down)
    return rsi

def get_macd(data, short_window=12, long_window=26, signal_window=9, bollinger_window=20):
    data['short'] = data['Close'].ewm(span=short_window).mean()
    data['long']  =  data['Close'].ewm(span=long_window).mean() 
    data['MACD'] = data['short'] - data['long']
    data['Signal'] = data['MACD'].rolling(signal_window).mean()
    data['MACD_Histo'] = data['MACD'] - data['Signal']
    data['Candle'] = data['Close'] - data['Open']
    data['Momentum'] = data['Candle'].rolling(7).mean()
    data['Dir'] = data['MACD_Histo'].diff()

    for i in range(len(data)):
        if data.iloc[i]['MACD_Histo'] > 0:
            if data.iloc[i]['Dir']>0:
                data.at[data.index[i],'Color'] = '#008080'
            else:
                data.at[data.index[i],'Color'] = '#b2d8d8'

        elif data.iloc[i]['MACD_Histo'] < 0:
            if data.iloc[i]['Dir']>0:
                data.at[data.index[i],'Color'] = '#ef7753'
            else:
                data.at[data.index[i],'Color'] = '#ec4242'

        else:
            data.at[data.index[i],'Color'] = 'white'
    
    # Zero Crossing of MACD Histogram
    data['neg'] = (data['MACD'] > data['Signal']) & (data['MACD'].shift(1) <= data['Signal'].shift(1))
    data['pos'] = (data['MACD'] < data['Signal']) & (data['MACD'].shift(1) >= data['Signal'].shift(1))
    data['z_cross'] = np.where(data['neg'],-1,
                               np.where(data['pos'],1,0))
    
    # Bollinger Bands
    data['sma'] = data['Close'].rolling(window=bollinger_window).mean()
    data['stddev'] = data['Close'].rolling(window=bollinger_window).std()
    data['upper_bound'] = data['sma'] + (data['stddev'] * 2)
    data['lower_bound'] = data['sma'] - (data['stddev'] * 2)

    # RSI
    rsi = get_rsi(data)
    data['rsi'] = rsi

    # Trade Signals
    cf = 0.05
    for i in range(len(data)):
        if (data.iloc[i]['Close'] > data.iloc[i]['upper_bound']) | \
            ((data.iloc[i]['Close'] > data.iloc[i]['upper_bound'] - cf * (data.iloc[i]['upper_bound']-data.iloc[i]['lower_bound'])) & \
                (rsi.iloc[i]>75)):
            data.at[data.index[i],'trade_signal'] = 1
        elif (data.iloc[i]['Close'] < data.iloc[i]['lower_bound'] + \
              (cf * (data.iloc[i]['upper_bound']-data.iloc[i]['lower_bound']))):
            data.at[data.index[i],'trade_signal'] = -1
        else:
            data.at[data.index[i],'trade_signal'] = 0
    
    data.reset_index(inplace=True)
    return data