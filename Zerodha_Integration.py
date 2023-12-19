from kite_trade import *
import pyotp
import pandas as pd
from datetime import datetime,timedelta

kite=None
def login(user_id,password,twofa):
    global kite
    enctoken = get_enctoken(user_id, password, twofa)
    kite = KiteApp(enctoken=enctoken)
    return kite
def convert_to_human_readable(df):
    df['date'] = df['date'].dt.strftime('%Y-%m-%d %H:%M:%S')
    return df
def get_ltp(symbol):
    res=float(kite.quote(f"NSE:{symbol}")[f"NSE:{symbol}"]['ohlc']['close'])
    return res

def combinedltp(formatted_symbols):
    res=kite.quote(formatted_symbols)
    return res

def get_ltp_option(symbol):

    res = kite.quote(f"NFO:{symbol}")[f"NFO:{symbol}"]
    first_buy_price = res['depth']['buy'][0]['price']


    return first_buy_price

def flhgdifjjernf()
    pass

#
#
# def get_historical_data(sym, exp, timeframe, strategy_tag, type, strike, RSIPeriod, MAOFOI, MAOFVOl):
#     global kite
#     df = pd.read_csv('Instruments.csv')
#
#     selected_row = df[(df['instrument_type'] == type) &
#                       (df['expiry'].astype(str) == exp) &
#                       (df['strike'].astype(int) == strike) &
#                       (df['tradingsymbol'].str.contains(sym))]
#
#
#     instrument_token = selected_row['instrument_token'].values[0] if not selected_row.empty else None
#     print("instrument_token: ",instrument_token)
#     from_datetime = datetime.now() - timedelta(days=5)  # From last 1 day
#     to_datetime = datetime.now()
#
#     res = kite.historical_data(instrument_token=instrument_token, from_date=from_datetime, to_date=to_datetime,
#                                interval=timeframe, continuous=False, oi=True)
#     price_data = pd.DataFrame(res)
#     price_data = convert_to_human_readable(pd.DataFrame(res))
#     price_data["SYMBOL"] = sym
#     price_data['date'] = pd.to_datetime(price_data['date'])
#
#     # Calculate MA_VOL, MA_OI, and RSI
#     price_data["MA_VOL"] = ta.sma(close=price_data["volume"], length=MAOFVOl, offset=None)
#     price_data["MA_OI"] = ta.sma(close=price_data["oi"], length=MAOFOI, offset=None)
#     price_data["RSI"] = ta.rsi(close=price_data["close"], length=RSIPeriod)
#
#     # Remove the 'date' column temporarily
#     date_column = price_data['date']
#     price_data.drop('date', axis=1, inplace=True)
#
#     # Reorder columns
#     cols = ['open', 'high', 'low', 'close', 'volume', 'oi', 'SYMBOL', 'MA_VOL', 'MA_OI', 'RSI']
#     price_data = price_data[cols]
#
#     # Set 'date' as the index
#     price_data.set_index(date_column, inplace=True)
#
#     # Calculate VWAP
#     price_data["VWAP"] = ta.vwap(high=price_data["high"], low=price_data["low"], close=price_data["close"], volume=price_data["volume"])
#
#     # Reinsert 'date' as a column
#     price_data.insert(0, 'date', price_data.index)
#
#
#
#     # Save to CSV with index=False to preserve the 'date' column as a regular column
#
#
#     return price_data
#
#
#
#





# def get_historical_data(sym,exp,timeframe,strategy_tag,type,strike,RSIPeriod,MAOFOI,MAOFVOl):
#     global  kite
#     df = pd.read_csv('Instruments.csv')
#
#     selected_row = df[(df['instrument_type'] == type) &
#                       (df['expiry'].astype(str) == exp) &
#                       (df['strike'].astype(int) == strike) &
#                       (df['tradingsymbol'].str.contains(sym))]
#     instrument_token = selected_row['instrument_token'].values[0] if not selected_row.empty else None
#     from_datetime = datetime.now() - timedelta(days=1)  # From last & days
#     to_datetime = datetime.now()
#
#     res = kite.historical_data(instrument_token=instrument_token,from_date=from_datetime,to_date=to_datetime,
#                                interval= timeframe, continuous=False, oi=True)
#     price_data = pd.DataFrame(res)
#     print("Columns:", price_data.columns)
#     price_data = convert_to_human_readable(pd.DataFrame(res))
#     price_data["SYMBOL"]=sym
#     price_data['date'] = pd.to_datetime(price_data['date'])
#     price_data = price_data.sort_values(by='date')
#     price_data['date'] = price_data['date'].dt.strftime('%Y-%m-%d %H:%M:%S')
#     price_data["MA_VOL"]=ta.sma(close=price_data["volume"],length=MAOFVOl,offset=None)
#     price_data["MA_OI"] = ta.sma(close=price_data["oi"], length=MAOFOI, offset=None)
#     price_data["RSI"]=ta.rsi(close=price_data["close"],length=RSIPeriod)
#     price_data.set_index('date', inplace=True)  # Assuming 'date' is the datetime column in your DataFrame
#     price_data.index = pd.to_datetime(price_data.index)  # Ensure the index is of datetime type
#     price_data.sort_index(inplace=True)
#     price_data["VWAP"] = ta.vwap(high=price_data["high"], low=price_data["low"], close=price_data["close"], volume=price_data["volume"])
#     print("Columns:", price_data.columns)
#     # price_data.to_csv(f'{strategy_tag}.csv', index=False)
#     return price_data



