import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime as dt
from datetime import timedelta
import pytz
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly
import streamlit as st


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
        t = yf.Ticker(ticker)
        tz = pytz.timezone(t.info['timeZoneFullName'])
        end_date = dt.today()
        end_date = end_date.astimezone(tz=tz)
        start_date = end_date + timedelta(days=-duration)
        # start_date = start_date.astimezone('Asia/Kolkata')
        data = yf.download(ticker, start=start_date, end=end_date)
        data.index = data.index.tz_localize('Asia/Kolkata')
        
        if (t.info['quoteType'] == 'INDEX') | (t.info['quoteType'] == 'EQUITY'):
            live_data = t.history(period = '1d', interval='1m')
            live_data.reset_index(inplace=True)
            last_updated = dt.strftime(live_data.iloc[-1]['Datetime'],'%d %b %Y %H:%M')
        elif t.info['quoteType'] == 'MUTUALFUND':
            live_data = t.history(period = '1mo', interval='1d')
            live_data.reset_index(inplace=True)
            live_data.rename(columns={'Date': 'Datetime'}, inplace=True)
            last_updated = dt.strftime(live_data.iloc[-1]['Datetime'],'%d %b %Y %H:%M')
        else:
            last_updated = "N/A"
        
        status = 1
    except Exception as error:
        status = 0
        data=[]
        print(error)

    return data, live_data, last_updated, status

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

def historical_figure(data, pchange):
    # traces
    ub_plot = go.Scatter(
        x = data['Date'],
        y = data['upper_bound'],
        mode = 'lines',
        line = dict(color='lightblue', width=0),
        name = 'Upper Bound'
    )

    lb_plot = go.Scatter(
        x = data['Date'],
        y = data['lower_bound'],
        mode = 'lines',
        line = dict(color='lightblue', width=0),
        fill = 'tonexty',
        fillcolor = 'rgba(31, 119, 180, 0.1)',
        name = 'Lower Bound'
    )

    sma_plot = go.Scatter(
        x = data['Date'],
        y = data['sma'],
        mode = 'lines',
        line = dict(color='#1f77b4', width=1),
        name = 'SMA'
    )

    close_plot = go.Scatter(
        x = data['Date'],
        y = data['Close'],
        mode = 'lines',
        line = dict(color='lightgray', width=1),
        name = 'Close'
    )

    candle_stick = go.Candlestick(
        x = data['Date'],
        open = data['Open'],
        close = data['Close'],
        high = data['High'],
        low = data['Low'],
        name = 'Candlestick'
    )

    rsi_plot = go.Scatter(
        x = data['Date'],
        y = data['rsi'],
        mode = 'lines',
        line = dict(color='red', width=2),
        name = 'RSI'
    )

    macd_plot = go.Bar(
        x= data['Date'],
        y = data['MACD_Histo'],
        marker_color = data['Color'],
        name='MACD'
    )

    # Figure
    fig = make_subplots(rows=3, cols=1, row_heights=[0.6,0.2,0.2], vertical_spacing=0, shared_xaxes=True)
    plot1 = [ub_plot, lb_plot, sma_plot, close_plot, candle_stick]
    plot2 = [rsi_plot]
    plot3 = [macd_plot]


    #subplot1
    fig.add_traces(plot1, rows=1, cols=1)
    fig.add_annotation(
        x=0,
        y=1,
        text = f"{st.session_state.ticker_name}",
        font=dict(size=20),
        showarrow=False,
        xanchor = 'left',
        yanchor = 'bottom',
        xref='x domain',
        yref='y domain',
        row = 1,
        col = 1,
    )

    if pchange>=0:
        fig.add_hline(y=data.iloc[-2]['Close'], line_color='black', line_width=0.3)
        fig.add_annotation(
                x=data.iloc[-1]['Date'],
                y=data.iloc[-2]['Close'],
                text=f"{data.iloc[-2]['Close']:.2f}",
                showarrow=False,
                xanchor="left",
                yanchor='top'
                )      
        fig.add_hline(y=data.iloc[-1]['Close'], line_color='green', line_width=0.3)
        fig.add_annotation(
                x=data.iloc[-1]['Date'],
                y=data.iloc[-1]['Close'],
                text=f"{data.iloc[-1]['Close']:.2f}",
                font=dict(color="green"),
                showarrow=False,
                xanchor="left",
                yanchor='bottom'
                )
    else:
        fig.add_hline(y=data.iloc[-2]['Close'], line_color='black', line_width=0.3)
        fig.add_annotation(
                x=data.iloc[-1]['Date'],
                y=data.iloc[-2]['Close'],
                text=f"{data.iloc[-2]['Close']:.2f}",
                showarrow=False,
                xanchor="left",
                yanchor='bottom'
                )      
        fig.add_hline(y=data.iloc[-1]['Close'], line_color='red', line_width=0.3)
        fig.add_annotation(
                x=data.iloc[-1]['Date'],
                y=data.iloc[-1]['Close'],
                text=f"{data.iloc[-1]['Close']:.2f}",
                font=dict(color="red"),
                showarrow=False,
                xanchor="left",
                yanchor='top'
                )
    for i in range(len(data)):
                if (data.iloc[i]['z_cross'] == 1) | (data.iloc[i]['z_cross'] == -1):
                    fig.add_vline(data.iloc[i]['Date'], line_color='lightgray', line_width=0.3)
    for i in range(len(data)):
                if data.iloc[i]['trade_signal'] == 1:
                    fig.add_vline(data.iloc[i]['Date'], line_color='red', line_width=0.8)
                if data.iloc[i]['trade_signal'] == -1:
                    fig.add_vline(data.iloc[i]['Date'], line_color='green', line_width=0.8)

    #subplot2
    fig.add_traces(plot2, rows=2, cols=1)
    fig.add_hline(y=70, line_color='red', line_dash='dash', row=2, col=1)
    fig.add_hline(y=30, line_color='teal', line_dash='dash', row=2, col=1)
    fig.add_annotation(
        x=0,
        y=1,
        text = "RSI",
        font=dict(size=20),
        showarrow=False,
        xanchor = 'left',
        xref='x domain',
        yref='y domain',
        row = 2,
        col = 1,
    )
    for i in range(len(data)):
                if (data.iloc[i]['z_cross'] == 1) | (data.iloc[i]['z_cross'] == -1):
                    fig.add_vline(data.iloc[i]['Date'], line_color='lightgray', line_width=0.3)
    for i in range(len(data)):
                if data.iloc[i]['trade_signal'] == 1:
                    fig.add_vline(data.iloc[i]['Date'], line_color='red', line_width=0.8)
                if data.iloc[i]['trade_signal'] == -1:
                    fig.add_vline(data.iloc[i]['Date'], line_color='green', line_width=0.8)
    #subplot3
    fig.add_traces(plot3, rows=3, cols=1)
    fig.add_annotation(
        x=0,
        y=1,
        text = "MACD",
        font=dict(size=20),
        showarrow=False,
        xanchor = 'left',
        xref='x domain',
        yref='y domain',
        row = 3,
        col = 1,
    )
    for i in range(len(data)):
                if (data.iloc[i]['z_cross'] == 1) | (data.iloc[i]['z_cross'] == -1):
                    fig.add_vline(data.iloc[i]['Date'], line_color='lightgray', line_width=0.3)
    for i in range(len(data)):
                if data.iloc[i]['trade_signal'] == 1:
                    fig.add_vline(data.iloc[i]['Date'], line_color='red', line_width=0.8)
                if data.iloc[i]['trade_signal'] == -1:
                    fig.add_vline(data.iloc[i]['Date'], line_color='green', line_width=0.8)


    # Figure Layout
    layout = {
        "height": 600,
        "showlegend": False,
        "xaxis": {"rangeslider": {"visible": False}},
        "yaxis2": {"range": [0,100]},
        "yaxis3": {"showticklabels": False},
    }
    fig.update_layout(layout)

    return fig

def current_figure(live_data):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    today_plot = go.Candlestick(
        x=live_data['Datetime'],
        open=live_data['Open'],
        close=live_data['Close'],
        high=live_data['High'],
        low=live_data['Low']
    )
    vol_plot = go.Bar(
        x=live_data['Datetime'],
        y=live_data['Volume'],
        name='Volume'
    )

    fig.add_trace(today_plot, secondary_y=False)
    fig.add_trace(vol_plot, secondary_y=True)

    layout = {
        "height": 600,
        "showlegend": False,
        "xaxis": {"rangeslider": {"visible": False}},
        "yaxis2": {"showticklabels": False,
                "showgrid": False,
                "range": [0,live_data['Volume'].max()*10]} 
    }
    fig.update_layout(layout)

    return fig