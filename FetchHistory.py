from kite_trade import *
import pyotp
import pandas as pd
from datetime import datetime
import Zerodha_Integration
import threading
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, render_template
lock = threading.Lock()
import os
import sys
import traceback

def get_zerodha_credentials():

    credentials = {}
    try:
        df = pd.read_csv('ZerodhaCredentials.csv')
        for index, row in df.iterrows():
            title = row['Title']
            value = row['Value']
            credentials[title] = value
    except pd.errors.EmptyDataError:
        print("The CSV file is empty or has no data.")
    except FileNotFoundError:
        print("The CSV file was not found.")
    except Exception as e:
        print("An error occurred while reading the CSV file:", str(e))

    return credentials


credentials_dict = get_zerodha_credentials()

user_id = credentials_dict.get('ZerodhaUserId')  # Login Id
password = credentials_dict.get('ZerodhaPassword')  # Login password

Mins= int(credentials_dict.get('Mins'))
fakey = credentials_dict.get('Zerodha2fa')
twofa = pyotp.TOTP(fakey)
twofa = twofa.now()
kite = Zerodha_Integration.login(user_id, password, twofa)
symbols_list=None
def extract_and_save_symbols_nfo(input_file, output_file):
    global symbols_list
    try:
        monthlyexp = credentials_dict.get('monthlyexp')
        monthlyexp = datetime.strptime(monthlyexp, "%d-%m-%Y")
        monthlyexp = monthlyexp.strftime("%Y-%m-%d")
        df = pd.read_csv(input_file)
        filtered_df = df[(df['expiry'] == monthlyexp) & (df['instrument_type'] == 'FUT')]
        unique_symbols_df = filtered_df.drop_duplicates(subset=['name'], keep='first')
        symbols_df = pd.DataFrame({
            'NFO Trading Symbol': unique_symbols_df['name'],
            'Trading Symbol': unique_symbols_df['tradingsymbol'],
            'Lotsize':unique_symbols_df['lot_size']
        })
        symbols_list = ['NFO: ' + symbol for symbol in symbols_df['Trading Symbol']]
        symbols_df = symbols_df.drop(columns=['Unnamed: 0'], errors='ignore')
        symbols_df.to_csv(output_file)
        # print(symbols_list)
        print(f"Unique symbols extracted and saved to {output_file}")

    except Exception as e:
        print(f"An error occurred: {str(e)}")


def ATM_CE_AND_PE_COMBIMED_10day_ver(ltp, symbol):
    try:
        monthlyexp = credentials_dict.get('monthlyexp')
        monthlyexp = datetime.strptime(monthlyexp, "%d-%m-%Y")
        monthlyexp = monthlyexp.strftime("%Y-%m-%d")
        pf = pd.read_csv("Instruments.csv")
        filtered_df = pf[(pf['expiry'] == monthlyexp) & (pf['instrument_type'] == 'CE') & (pf["name"] == symbol)]
        if not filtered_df.empty:
            filtered_df["strike_diff"] = abs(
                filtered_df["strike"] - ltp)
            min_diff_row = filtered_df.loc[filtered_df['strike_diff'].idxmin()]
            strike = int(min_diff_row["strike"])
            cesymname = min_diff_row["tradingsymbol"]
            pesymname = cesymname.rsplit('CE', 1)[0] + 'PE'

            return cesymname, pesymname
        else:
            return None, None  # Return None if no suitable values are found
    except Exception as e:
        print(f"ATM_CE_AND_PE_COMBIMED error: {e}")
        return None, None

def data_formating():
    gf = pd.read_csv('premium_combined_pivoted_data.csv')
    gf = gf.set_index('Date').T
    gf = gf.sort_index(ascending=False)
    gf = gf.reset_index()
    gf = gf[gf.columns[::-1]]
    gf = gf.rename(columns={'index': 'Symbol'})
    today_date = datetime.today().date()
    formatted_today_date = today_date.strftime('%Y-%m-%d')
    formatted_today_date_string = str(formatted_today_date)
    yesterday_date = today_date - timedelta(days=1)
    formatted_yesterday_date = yesterday_date.strftime('%Y-%m-%d')
    formatted_yesterday_date_string = str(formatted_yesterday_date)
    if formatted_today_date_string in gf.columns:
        gf = gf.drop(columns=formatted_today_date_string)
    if formatted_yesterday_date_string in gf.columns:
        gf = gf.drop(columns=formatted_yesterday_date_string)
    gf.to_csv("premium_combined_pivoted_data.csv", index=False)


def get_atm_combined_10_days():
    df = pd.read_csv("UniqueInstrumentsnfo.csv")
    pf = pd.read_csv("Instruments.csv")
    trading_symbols_dict = {}
    monthlyexp = credentials_dict.get('monthlyexp')
    monthlyexp = datetime.strptime(monthlyexp, "%d-%m-%Y")
    monthlyexp = monthlyexp.strftime("%Y-%m-%d")

    for symbol in df["Trading Symbol"]:
        matching_row = pf[pf["tradingsymbol"] == symbol]
        if not matching_row.empty:
            instrument_token = matching_row.iloc[0]["instrument_token"]
            historical_data = Zerodha_Integration.get_historical_data(instrument_token)

            date_values = historical_data['date'][:10]  # Assuming you want the first 10 dates
            close_prices = historical_data['close'][:10]  # Assuming you want the first 10 close prices

            info = {}
            for idx in range(10):
                try:
                    if idx < len(date_values) and idx < len(close_prices):
                        # Get the date and close price
                        date_value = date_values.iloc[idx]
                        close_price = close_prices.iloc[idx]
                        nfo_trading_symbol_value = df[df["Trading Symbol"] == symbol]["NFO Trading Symbol"].iloc[0]
                        cesymname, pesymname = ATM_CE_AND_PE_COMBIMED_10day_ver(close_price, nfo_trading_symbol_value)
                        ce_row = pf[pf['tradingsymbol'] == cesymname]
                        pe_row = pf[pf['tradingsymbol'] == pesymname]
                        ce_close_price = Zerodha_Integration.get_historical_data_combined(
                            ce_row.iloc[0]['instrument_token'], date_value)
                        pe_close_price = Zerodha_Integration.get_historical_data_combined(
                            pe_row.iloc[0]['instrument_token'], date_value)
                        if ce_close_price is not None and pe_close_price is not None:
                            premium_combined = ce_close_price + pe_close_price
                        else:
                            premium_combined = None
                        # Calculate premium_combined
                        info[date_value] = {
                            "close_price": close_price,
                            "cesymname": cesymname,
                            "pesymname": pesymname,
                            "ce_instrument_token": ce_row.iloc[0]['instrument_token'] if not ce_row.empty else None,
                            "pe_instrument_token": pe_row.iloc[0]['instrument_token'] if not pe_row.empty else None,
                            "cecloseprice": ce_close_price,
                            "peprice": pe_close_price,
                            "premium_combined": premium_combined
                        }
                except IndexError:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    print("*** Traceback ***")
                    traceback.print_tb(exc_traceback)
                    info[date_value] = {"premium_combined": "NA"}
                    continue

            # Store data in 'trading_symbols_dict'
            trading_symbols_dict[symbol] = {
                "instrument_token": instrument_token,
                "monthlyexp": monthlyexp,
                "symbol": nfo_trading_symbol_value,
                "info": info,
            }

    columns = list(trading_symbols_dict.keys())
    date_columns = list(trading_symbols_dict[columns[0]]["info"].keys())
    # Create a DataFrame from 'data' with 'columns' and 'date_columns'
    data = []

    for symbol in columns:
        row = []
        for date in date_columns:
            try:
                premium_combined = trading_symbols_dict[symbol]["info"][date]["premium_combined"]
            except KeyError:
                premium_combined = None
            row.append(premium_combined)
        data.append(row)

    df = pd.DataFrame(data, columns=date_columns, index=columns)

    df = df.T.reset_index()
    df.columns.name = None
    df = df.rename(columns={'index': 'Date'})

    df.to_csv("premium_combined_pivoted_data.csv", index=False)
    data_formating()

get_atm_combined_10_days()