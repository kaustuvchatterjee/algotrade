import streamlit as st
import yfinance as yf
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import gridspec
from datetime import datetime as dt
from datetime import timedelta, time
from nsepython import *

st.set_page_config(layout="wide")


##-------------HELPER FUNCTIONS---------------------------
def get_tickers(file_path='tickers.csv'):
    try:
        df = pd.read_csv(file_path)
        options=df['ticker'].to_list()
        option_names=df['name'].to_list()
        return options, option_names
    except:
        options=['^BSESN','^NSEI']
        option_names=['BSE SENSEX','NIFTY 50']
        return options, option_names

def get_ticker_data(ticker,duration):
    end_date = dt.today() + timedelta(days=-1)
    start_date = end_date + timedelta(days=-duration)

    data = yf.download(ticker, start=start_date, end=end_date,)
    return data

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
    
    return data

#----------------INPUTS-----------------------------------
options, option_names = get_tickers('tickers.csv')
st.sidebar.title('Parameters')
with st.sidebar:
    ticker_name = st.selectbox(label='Ticker', options=option_names, )
    duration = st.number_input(label='Duration (days)', min_value=30, max_value=730, value=180, step=30)
    short_window = st.number_input(label='Short Window (days)', min_value=1, max_value=60, value=24, step=1)
    long_window = st.number_input(label='Long Window (days)', min_value=1, max_value=180, value=52, step=1)
    signal_window = st.number_input(label='Signal Window (days)', min_value=1, max_value=15, value=9, step=1)
    bollinger_window = st.number_input(label='Band Window (days)', min_value=1, max_value=180, value=20, step=1)

ticker = options[option_names.index(ticker_name)]
title = ticker_name
st.markdown(f'# {title}')

try:
    #----------------APP LOGIC---------------------------------
    if ticker =='^NSEI':
        # #Live Data
        df = nse_index()
        df = df[df['indexName']=='NIFTY 50'][['last','open','high','low','timeVal','percChange']]
        df['timeVal'] = pd.to_datetime(df['timeVal'])
        df['percChange'] = pd.to_numeric(df['percChange'])
        df['last'] = df['last'].str.replace(',', '').astype(float)
        df['open'] = df['open'].str.replace(',', '').astype(float)
        df['high'] = df['high'].str.replace(',', '').astype(float)
        df['low'] = df['low'].str.replace(',', '').astype(float)

        st.markdown("""
                    <style>
                    .big-font-green {
                    font-size:36px !important;
                    color:green;
                    }
                    .big-font-red{
                    font-size:36px !important;
                    color:red;
                    }
                    </style>
                    """, unsafe_allow_html=True)
        
        cols = st.columns([0.1,0.4,0.2,0.3])
        with cols[1]:
            if df['percChange'][0]>0:            
                st.markdown(f'<p class="big-font-green"><b>{df['last'][0]} <span>&uarr;</span></b> ({str(df['percChange'][0])}%)</p>', unsafe_allow_html=True)
            else:
                st.markdown(f'<p class="big-font-red"><b>{df['last'][0]} <span>&darr;</span></b> ({str(df['percChange'][0])}%)</p>', unsafe_allow_html=True)
            
        with cols[2]:
            st.markdown(f"**Open**: {df['open'][0]}<br> \
                        **Low**: {df['low'][0]}<br> \
                        **High**: {df['high'][0]}", unsafe_allow_html=True)
        with cols[3]:
            st.markdown(f"<br><br>*Updated at {df['timeVal'][0]}*", unsafe_allow_html=True)

        

    data = get_ticker_data(ticker, duration)
    rsi = get_rsi(data)
    data = get_macd(data, short_window, long_window, signal_window)
    up = data[data['Close']>=data['Open']]
    down = data[data['Close']<data['Open']]
    last_data = dt.strftime(data.index[-1],'%d %b %Y')
    
    #-------------------PLOT--------------------------------------
    fig = plt.figure(figsize=(12, 6),dpi=1200)
    gs = gridspec.GridSpec(3, 1, height_ratios=[3,1,1])
    ax0 = plt.subplot(gs[0])
    ax1 = plt.subplot(gs[1], sharex=ax0)  # second subplot
    ax2 = plt.subplot(gs[2], sharex=ax0)  # first subplot
    

    ax0.plot(data.index, data['Close'], color='gray', label='Nifty 50 Index', lw=0.6)
    ax0.bar(up.index, up['Close']-up['Open'], bottom=up['Open'], color='g', width=0.8)
    ax0.bar(up.index, up['High']-up['Close'], bottom=up['Close'], color='g', width=0.03)
    ax0.bar(up.index, up['Low']-up['Open'], bottom=up['Open'], color='g', width=0.03)
    ax0.bar(down.index, down['Close']-down['Open'], bottom=down['Open'], color='r', width=0.8)
    ax0.bar(down.index, down['High']-down['Close'], bottom=down['Close'], color='r', width=0.03)
    ax0.bar(down.index, down['Low']-down['Open'], bottom=down['Open'], color='r', width=0.03)

    ax0.fill_between(data.index, data['upper_bound'], data['lower_bound'], color='tab:blue', alpha=0.1)
    ax0.plot(data.index, data['sma'], color='tab:blue', lw=0.6)

    for i in range(len(data)):
        if (data.iloc[i]['z_cross'] == 1) | (data.iloc[i]['z_cross'] == -1):
            ax0.axvline(data.index[i], color='gray', lw=0.3, alpha=0.5)

    for i in range(len(data)):
        if data.iloc[i]['trade_signal'] == 1:
            ax0.axvline(data.index[i], color='tab:red', lw=0.8)
        if data.iloc[i]['trade_signal'] == -1:
            ax0.axvline(data.index[i], color='tab:green', lw=0.8)
    
    if ticker == '^NSEI':
        if df['last'][0]-df['open'][0]>0:
            ax0.bar(df['timeVal'][0],df['last'][0]-df['open'][0], bottom=df['open'][0], color='g', width=0.8)
            ax0.bar(df['timeVal'][0],df['high'][0]-df['last'][0], bottom=df['last'][0], color='g', width=0.03)
            ax0.bar(df['timeVal'][0],df['low'][0]-df['open'][0], bottom=df['open'][0], color='g', width=0.03)
        else:
            ax0.bar(df['timeVal'][0],df['last'][0]-df['open'][0], bottom=df['open'][0], color='r', width=0.8)
            ax0.bar(df['timeVal'][0],df['high'][0]-df['last'][0], bottom=df['last'][0], color='r', width=0.03)
            ax0.bar(df['timeVal'][0],df['low'][0]-df['open'][0], bottom=df['open'][0], color='r', width=0.03)

    ax0.grid(axis='y', alpha=0.3)

    ax1.plot(data.index, rsi, color='tab:red', alpha=0.8)
    ax1.axhline(75, linestyle='--', color='red')
    ax1.fill_between(data.index,75,rsi, where=rsi>=74, color='tab:orange', alpha = 0.1)
    ax1.set_ylim([0,100])
    ax1.grid(axis='y', alpha=0.3)

    ax2.bar(data.index, data['MACD_Histo'], color=data['Color'])
    for i in range(len(data)):
        if (data.iloc[i]['z_cross'] == 1) | (data.iloc[i]['z_cross'] == -1):
            ax2.axvline(data.index[i], color='gray', lw=0.3, alpha=0.5)
    

    dateFmt = mdates.DateFormatter('%d %b %y')
    ax2.xaxis.set_major_formatter(dateFmt)

    ax2.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    fig.subplots_adjust(hspace=0)
    # plt.savefig('nifty.png', dpi=300)
    # plt.show()

    st.pyplot(fig, use_container_width=True)
except:
    st.write('Unable to retreive data!!!')
# except Exception as error:
#     st.write("unable to retreive data") 
#     print(error)

while True:
    # Your Streamlit code here
    st.write("Rerunning script...")
    time.sleep(300)  # 5 minutes in seconds
    st.rerun()