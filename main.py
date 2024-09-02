import streamlit as st
import yfinance as yf
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import gridspec
from datetime import datetime as dt
from datetime import timedelta, time
import pytz
import time

st.set_page_config(page_title='Algo Trade', page_icon=":material/waterfall_chart:", layout="wide")
tz=pytz.timezone('Asia/Kolkata')
fig = None
##-------------HELPER FUNCTIONS---------------------------
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

def get_ticker_data(duration):
    try:
        ticker = tickers[ticker_names.index(st.session_state.ticker_name)]
        end_date = dt.today() # + timedelta(days=-1)
        # end_date = end_date.astimezone('Asia/Kolkata')
        start_date = end_date + timedelta(days=-duration)
        # start_date = start_date.astimezone('Asia/Kolkata')
        data = yf.download(ticker, start=start_date, end=end_date)
        data.index = data.index.tz_localize('Asia/Kolkata')
        status = 1
    except Exception as error:
        status = 0
        data=[]
        print(error)

    return data, status


def get_live_data(ticker):
    try:
        t = yf.Ticker(ticker)
        today_data = t.history(period='1d', interval='1m')
        timeVal = today_data.index[-1].replace(tzinfo=tz)
        live_data = {'timeVal': timeVal,
                        'open': t.info['open'],
                        'last': today_data['Close'].iloc[-1],
                        'high': t.info['dayHigh'],
                        'low': t.info['dayLow'],
                        'pchange': 100*((today_data['Close'].iloc[-1]-t.info['previousClose'])/t.info['previousClose']),
                        'prev_close': t.info['previousClose'],
                        'tp_start': dt.fromtimestamp(t.history_metadata['currentTradingPeriod']['regular']['start'],tz=tz),
                        'tp_end': dt.fromtimestamp(t.history_metadata['currentTradingPeriod']['regular']['end'],tz=tz),
                        }
        status = 1

    except Exception as error:
        status = 0
        live_data = []
        print(error)

        
    return live_data, status

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

@st.fragment(run_every='10s')
def update_live_data():
    ticker = tickers[ticker_names.index(st.session_state.ticker_name)]
    live_data, status = get_live_data(ticker)
    placeholder = st.empty()
    with placeholder.container():
        cols = st.columns([0.1,0.4,0.2,0.3])
    if status == 1:
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

        with cols[1]:
            if live_data['pchange']>0:          
                st.markdown(f'<p class="big-font-green"><b>{live_data['last']:.2f} <span>&uarr;</span></b> ({live_data['pchange']:.2f}%)</p>', unsafe_allow_html=True)
            else:
                st.markdown(f'<p class="big-font-red"><b>{live_data['last']:.2f} <span>&darr;</span></b> ({live_data['pchange']:.2f}%)</p>', unsafe_allow_html=True)
            
        with cols[2]:
            st.markdown(f"**Prev Close**: {live_data['prev_close']:.2f}<br> \
                        **High**: {live_data['high']:.2f}<br> \
                        **Open**: {live_data['open']:.2f}<br> \
                        **Low**: {live_data['low']:.2f}", unsafe_allow_html=True)
        with cols[3]:
            last_updated = dt.strftime(live_data['timeVal'],'%d %b %Y %H:%M')
            st.markdown(f"<br><br><br>*Updated at {last_updated}*", unsafe_allow_html=True)

@st.fragment(run_every='10s')
def update_live_data_plot(ax):
    ticker = tickers[ticker_names.index(st.session_state.ticker_name)]
    live_data, status = get_live_data(ticker)
    if status==1:
        if (dt.now(tz=tz)>live_data['tp_start']) & (dt.now(tz=tz)<live_data['tp_end']):
            if live_data['last']-live_data['open']>0:
                ax.bar(live_data['timeVal'],live_data['last']-live_data['open'], bottom=live_data['open'], color='g', width=0.8)
                ax.bar(live_data['timeVal'],live_data['high']-live_data['last'], bottom=live_data['last'], color='g', width=0.03)
                ax.bar(live_data['timeVal'],live_data['low']-live_data['open'], bottom=live_data['open'], color='g', width=0.03)
            else:
                ax.bar(live_data['timeVal'],live_data['last']-live_data['open'], bottom=live_data['open'], color='r', width=0.8)
                ax.bar(live_data['timeVal'],live_data['high']-live_data['last'], bottom=live_data['last'], color='r', width=0.03)
                ax.bar(live_data['timeVal'],live_data['low']-live_data['open'], bottom=live_data['open'], color='r', width=0.03)


        l1 = ax.axhline(live_data['prev_close'], color='black', lw=0.3)

        if live_data['last']>=live_data['prev_close']:
            color = 'tab:green'
            va_prev_close = 'top'
            va_y_last = 'bottom'
        else:
            color = 'tab:red'
            va_prev_close = 'bottom'
            va_y_last = 'top'

        l2 = ax.axhline(live_data['last'], color=color, lw=0.3)

        x = ax.get_xlim()[1]
        d1 = ax.text(x,live_data['prev_close'], f"{live_data['prev_close']:.2f}", size=6, color='black', verticalalignment=va_prev_close,horizontalalignment='right')
        d2 = ax.text(x,live_data['last'], f"{live_data['last']:.2f}", size=6, color=color, verticalalignment=va_y_last, horizontalalignment='right')



#----------------INPUTS-----------------------------------
tickers, ticker_names = get_tickers('tickers.csv')
st.sidebar.title('Parameters')
with st.sidebar:
    st.session_state.ticker_name = st.selectbox(label='Ticker', options=ticker_names, )
    # st.session_state.index = st.session_state.ticker_names.index(ticker_name)
    duration = st.number_input(label='Duration (days)', min_value=30, max_value=730, value=180, step=30)
    short_window = st.number_input(label='Short Window (days)', min_value=1, max_value=60, value=12, step=1)
    long_window = st.number_input(label='Long Window (days)', min_value=1, max_value=180, value=26, step=1)
    signal_window = st.number_input(label='Signal Window (days)', min_value=1, max_value=15, value=9, step=1)
    bollinger_window = st.number_input(label='Band Window (days)', min_value=1, max_value=180, value=20, step=1)

st.markdown(f'# {st.session_state.ticker_name}')
#----------------APP LOGIC---------------------------------
update_live_data()
##-----------GET HISTORICAL DATA--------------------------
data, status = get_ticker_data(duration)

if (status == 1) & (len(data)>0):
    rsi = get_rsi(data)
    data = get_macd(data, short_window, long_window, signal_window)
    up = data[data['Close']>=data['Open']]
    down = data[data['Close']<data['Open']]
else:
    st.write('Unable to retreive historical data!')

#-------------------PLOT--------------------------------------
if len(data)>0:
    try:
        st.cache_resource.clear()
        fig = plt.figure(figsize=(12, 6),dpi=1200)
        fig.clear()
        gs = gridspec.GridSpec(3, 1, height_ratios=[3,1,1])
        ax0 = plt.subplot(gs[0])
        ax1 = plt.subplot(gs[1], sharex=ax0)
        ax2 = plt.subplot(gs[2], sharex=ax0)
        
        
        ax0.plot(data.index, data['Close'], color='gray', lw=0.6)
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
                ax0.axvline(data.index[i], color='gray', lw=0.3, alpha=0.6)

        for i in range(len(data)):
            if data.iloc[i]['trade_signal'] == 1:
                ax0.axvline(data.index[i], color='tab:red', lw=0.8)
            if data.iloc[i]['trade_signal'] == -1:
                ax0.axvline(data.index[i], color='tab:green', lw=0.8)

        ax0.grid(axis='y', alpha=0.3)
        ax0.set_title(" "+st.session_state.ticker_name,loc='left',y=0.92)
        #-----RSI Plot------------
        ax1.plot(data.index, rsi, color='tab:red', alpha=0.8)
        ax1.axhline(70, linestyle='--', color='red')
        ax1.fill_between(data.index,70,rsi, where=rsi>=70, color='tab:orange', lw=0.6, alpha = 0.1)
        ax1.axhline(30, linestyle='--', color='teal')
        ax1.fill_between(data.index,30,rsi, where=rsi<=30, color='tab:green', lw=0.6, alpha = 0.1)
        ax1.set_ylim([0,100])
        for i in range(len(data)):
            if (data.iloc[i]['z_cross'] == 1) | (data.iloc[i]['z_cross'] == -1):
                ax1.axvline(data.index[i], color='gray', lw=0.3, alpha=0.3)

        ax1.grid(axis='y', alpha=0.3)
        ax1.set_title(' RSI',loc='left',y=0.78)

        #-----MACD Plot---------
        ax2.bar(data.index, data['MACD_Histo'], color=data['Color'])
        for i in range(len(data)):
            if (data.iloc[i]['z_cross'] == 1) | (data.iloc[i]['z_cross'] == -1):
                ax2.axvline(data.index[i], color='gray', lw=0.3, alpha=0.6)


        dateFmt = mdates.DateFormatter('%d %b')
        ax2.xaxis.set_major_formatter(dateFmt)
        ax2.grid(axis='y', alpha=0.6)
        ax2.set_title(f" MACD",loc='left',y=0.78)

        plt.setp(ax0.get_xticklabels(), visible=False)
        plt.setp(ax1.get_xticklabels(), visible=False)
        plt.tight_layout()
        fig.subplots_adjust(hspace=0)
        # plt.savefig('nifty.png', dpi=300)
        # plt.show()
        # data_plot = st.pyplot(fig, use_container_width=True, dpi=600)
        update_live_data_plot(ax0)
        st.pyplot(fig, dpi=600)



    except Exception as error:
        st.write("Unable to plot data!") 
        print(error)
else:
    st.write('Unable to plot data!')




while True:
    # Your Streamlit code here
    # st.write("Rerunning script...")
    time.sleep(60)  
    st.rerun()
