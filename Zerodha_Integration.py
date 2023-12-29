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

def get_historical_data(instrument_token):
    global kite

    from_datetime = datetime.now() - timedelta(days=13)  # From last 1 day
    to_datetime = datetime.now()

    res = kite.historical_data(instrument_token, from_datetime, to_datetime, "day", continuous=False, oi=False)
    price_data = pd.DataFrame(res)
    price_data = price_data[['date', 'close']]
    price_data['date'] = pd.to_datetime(price_data['date']).dt.strftime('%Y-%m-%d')

    return price_data


def get_historical_data_combined_scanner(instrument_token, date, days):
    global kite
    from_datetime = datetime.now() - timedelta(days=days)  # From last 13 days
    to_datetime = datetime.now()
    res = kite.historical_data(instrument_token, from_datetime, to_datetime, "day", continuous=False, oi=False)
    price_data = pd.DataFrame(res)
    price_data = price_data[['date', 'close']]
    price_data['date'] = pd.to_datetime(price_data['date']).dt.strftime('%Y-%m-%d')
    filtered_data = price_data[price_data['date'] == date]
    datevalue=filtered_data['date'].iloc[0] if not filtered_data.empty else None
    close_price = filtered_data['close'].iloc[0] if not filtered_data.empty else None
    return close_price


def get_historical_data_combined(instrument_token, date):
    global kite
    try:
        from_datetime = datetime.now() - timedelta(days=13)  # From last 13 days
        to_datetime = datetime.now()
        res = kite.historical_data(instrument_token, from_datetime, to_datetime, "day", continuous=False, oi=False)
        price_data = pd.DataFrame(res)

        price_data = price_data[['date', 'close']]
        price_data['date'] = pd.to_datetime(price_data['date']).dt.strftime('%Y-%m-%d')

        filtered_data = price_data[price_data['date'] == date]

        datevalue=filtered_data['date'].iloc[0] if not filtered_data.empty else None
        close_price = filtered_data['close'].iloc[0] if not filtered_data.empty else None

        return close_price
    except (IndexError, KeyError) as e:
        print(f"Error: {e}")
        close_price=0
        return close_price




def convert_to_human_readable(df):
    df['date'] = df['date'].dt.strftime('%Y-%m-%d %H:%M:%S')
    return df
def get_yesterdayclose(symbol):
    res=float(kite.quote(f"NFO:{symbol}")[f"NFO:{symbol}"]['ohlc']['close'])
    return res

def combinedltp(formatted_symbols):
    res=kite.quote(formatted_symbols)
    return res

def get_ltp_option(symbol):

    res = kite.quote(f"NFO:{symbol}")[f"NFO:{symbol}"]
    first_buy_price = res['depth']['buy'][0]['price']


    return first_buy_price


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



