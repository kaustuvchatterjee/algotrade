import algotrade
import yfinance as yf
import streamlit as st
from datetime import datetime as dt
import time
# import plotly.graph_objects as go
# from plotly.subplots import make_subplots
# import plotly

st.cache_data.clear()
st.set_page_config(
      page_title='Algo Trade',
      page_icon=":material/waterfall_chart:",
      layout="wide",
      )
st.markdown("""
        <style>
               .block-container {
                    padding-top: 1rem;
                    padding-bottom: 0rem;
                    padding-left: 5rem;
                    padding-right: 5rem;
                }
        </style>
        """, unsafe_allow_html=True)

#----------------INPUTS-----------------------------------
tickers, ticker_names = algotrade.get_tickers('tickers.csv')
st.sidebar.title('Parameters')
with st.sidebar:
    st.session_state.ticker_name = st.selectbox(label='Ticker', options=ticker_names, )
    # st.session_state.index = st.session_state.ticker_names.index(ticker_name)
    duration = st.number_input(label='Duration (days)', min_value=30, max_value=730, value=180, step=30)

#---------------FETCH DATA----------------------------------
ticker = tickers[ticker_names.index(st.session_state.ticker_name)]

# Historical Data
data, live_data, last_updated, hist_status = algotrade.get_ticker_data(ticker, duration)
if hist_status == 1:
    data = algotrade.get_macd(data)
    pchange = 100*(data.iloc[-1]['Close'] - data.iloc[-2]['Close'])/data.iloc[-2]['Close']
#-------------------PLOTS------------------------------------
fig1 = algotrade.historical_figure(data, pchange)
fig2 = algotrade.current_figure(live_data)

#----------------PAGE----------------------------
st.title(f"{st.session_state.ticker_name}")
cols = st.columns([0.5,0.2,0.3])
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

with cols[0]:
    if pchange>0:          
        st.markdown(f'<p class="big-font-green"><b>{data.iloc[-1]['Close']:.2f} <span>&uarr;</span></b> ({pchange:.2f}%)</p>', unsafe_allow_html=True)
    else:
        st.markdown(f'<p class="big-font-red"><b>{data.iloc[-1]['Close']:.2f} <span>&darr;</span></b> ({pchange:.2f}%)</p>', unsafe_allow_html=True)
    
with cols[1]:
    st.markdown(f"**Prev Close**: {data.iloc[-2]['Close']:.2f}<br> \
                **High**: {data.iloc[-1]['High']:.2f}<br> \
                **Open**: {data.iloc[-1]['Open']:.2f}<br> \
                **Low**: {data.iloc[-1]['Low']:.2f}", unsafe_allow_html=True)
with cols[2]:
    st.markdown(f"*Updated on {last_updated}*", unsafe_allow_html=True)
    refresh = st.button('Refresh')

tab1, tab2 = st.tabs(['Historical', 'Current'])

with tab1:
    st.plotly_chart(fig1)

with tab2:
      st.plotly_chart(fig2)


if refresh:
      st.rerun()