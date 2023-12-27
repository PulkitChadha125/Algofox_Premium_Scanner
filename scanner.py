from kite_trade import *
import pyotp
import pandas as pd
from datetime import datetime,timedelta
import Zerodha_Integration
import threading
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, render_template
lock = threading.Lock()
import os
import sys
import traceback

# Determine the path to the templates folder dynamically
if getattr(sys, 'frozen', False):
    # If frozen (e.g., PyInstaller), use the appropriate sys._MEIPASS path
    current_dir = os.path.dirname(sys.executable)
else:
    # If not frozen, get the current working directory
    current_dir = os.path.dirname(os.path.abspath(__file__))

# Define the path to the templates folder based on the above logic
template_folder = os.path.join(current_dir, 'templates')
print(template_folder)

# Initialize Flask app with the dynamically determined template folder path
app = Flask(__name__, template_folder=template_folder)

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

            # Extracting all date and close price pairs from historical data
            date_values = historical_data['date'][:10]  # Assuming you want the first 10 dates
            close_prices = historical_data['close'][:10]  # Assuming you want the first 10 close prices

            # Update the dictionary
            info = {}
            for idx in range(10):
                if idx < len(date_values) and idx < len(close_prices):
                    # Get the date and close price
                    date_value = date_values.iloc[idx]
                    close_price = close_prices.iloc[idx]
                    nfo_trading_symbol_value = df[df["Trading Symbol"] == symbol]["NFO Trading Symbol"].iloc[0]
                    cesymname, pesymname = ATM_CE_AND_PE_COMBIMED_10day_ver(close_price, nfo_trading_symbol_value)
                    ce_row = pf[pf['tradingsymbol'] == cesymname]
                    pe_row = pf[pf['tradingsymbol'] == pesymname]
                    ce_close_price = Zerodha_Integration.get_historical_data_combined(ce_row.iloc[0]['instrument_token'], date_value)
                    pe_close_price = Zerodha_Integration.get_historical_data_combined(pe_row.iloc[0]['instrument_token'], date_value)
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
                else:
                    break
            trading_symbols_dict[symbol] = {
                "instrument_token": instrument_token,
                "monthlyexp": monthlyexp,
                "symbol": nfo_trading_symbol_value,
                "info": info,

            }

    print(trading_symbols_dict)
    return trading_symbols_dict

run_once = False
# get_atm_combined_10_days()
# Zerodha_Integration.get_historical_data_combined(16793602,date="2023-12-11")

def ATM_CE_AND_PE_COMBIMED(ltp,symbol):
    try:
        monthlyexp = credentials_dict.get('monthlyexp')
        monthlyexp = datetime.strptime(monthlyexp, "%d-%m-%Y")
        monthlyexp = monthlyexp.strftime("%Y-%m-%d")
        pf = pd.read_csv("Instruments.csv")
        filtered_df = pf[(pf['expiry'] == monthlyexp) & (pf['instrument_type'] == 'CE') & (pf["name"]==symbol)]
        if not filtered_df.empty:
            filtered_df["strike_diff"] = abs(
                filtered_df["strike"] - ltp)
            min_diff_row = filtered_df.loc[filtered_df['strike_diff'].idxmin()]
        strike=int(min_diff_row["strike"])
        cesymname=min_diff_row["tradingsymbol"]
        pesymname = cesymname.rsplit('CE', 1)[0] + 'PE'

        ce_ltp=Zerodha_Integration.get_ltp_option(cesymname)
        pe_ltp=Zerodha_Integration.get_ltp_option(pesymname)
        com=ce_ltp+pe_ltp

        return int(com)




    except Exception as e:
        print(f"ATM_CE_AND_PE_COMBIMED error : {str(e)}")


def PREMIUM_COLLECTED(lots,combinedpremium):

    return float(lots*combinedpremium)

def calculate_xpercent(ltp, combinedpremium):
    xpercent = (combinedpremium / ltp) * 100
    return xpercent

def get_symbol_data():
    global run_once
    try:
        today_date = datetime.today().date()
        yesterday_date = today_date - timedelta(days=1)
        formatted_yesterday_date = yesterday_date.strftime('%Y-%m-%d')
        formatted_yesterday_date_string = str(formatted_yesterday_date)
        print("Updating Data...")
        df= pd.read_csv("UniqueInstrumentsnfo.csv")
        df["LTP"] = None
        df["ATM_CE_AND_PE"] = None
        df["PERCENTAGEOF_LTP"] = None
        df["PREMIUM_COLLECTED"] = None
        df[formatted_yesterday_date_string] = None
        for index, row in df.iterrows():
            symbol = row['Trading Symbol']
            ins=row['NFO Trading Symbol']
            lots=row['Lotsize']
            try:
                res = Zerodha_Integration.get_ltp_option(symbol)
                combinedpremium= ATM_CE_AND_PE_COMBIMED(res,ins)
                percentof= calculate_xpercent(res, combinedpremium)
                pes = Zerodha_Integration.get_yesterdayclose(symbol)
                combinedpremium_yes=ATM_CE_AND_PE_COMBIMED(pes,ins)
                df.at[index, 'ATM_CE_AND_PE'] = combinedpremium
                df.at[index, 'LTP'] = res
                df.at[index, 'PREMIUM_COLLECTED']=PREMIUM_COLLECTED(lots,combinedpremium)
                df.at[index, 'PERCENTAGEOF_LTP'] =percentof
                df.at[index, formatted_yesterday_date_string] = combinedpremium_yes
                df = df.drop(columns=['Unnamed: 0'], errors='ignore')
            except Exception as e:
                print(f"An error occurred while getting ltp : {str(e)}")

        if run_once == False:
            run_once=True
            gf = pd.read_csv('premium_combined_pivoted_data.csv')
            columns_to_drop = []
            if len(gf.columns) > 9:
                date_columns = [col for col in gf.columns if col != 'Symbol']

                oldest_date_column = min(date_columns)

                columns_to_drop.append(oldest_date_column)
            if columns_to_drop:
                gf = gf.drop(columns=columns_to_drop)
            #  merging database
            merged_df = pd.merge(df, gf, left_on='Trading Symbol', right_on='Symbol', how='left')
            final_result = pd.concat([merged_df['ATM_CE_AND_PE'], merged_df.drop(columns='ATM_CE_AND_PE')], axis=1)
            tpp = pd.read_csv('premium_combined_pivoted_data.csv')
            merged_df_tom = pd.merge(tpp, df[['Trading Symbol', formatted_yesterday_date_string]], left_on='Symbol',
                                     right_on='Trading Symbol', how='left')

            cols = list(merged_df_tom.columns)
            cols.remove(formatted_yesterday_date_string)
            cols.insert(0, formatted_yesterday_date_string)

            merged_df_tom = merged_df_tom[cols]

            merged_df_tom.to_csv('premium_combined_pivoted_data.csv', index=False)
            
            if 'Unnamed: 0' in df.columns:
                final_result = final_result.drop(columns='Unnamed: 0')

            final_result.to_csv('final_result.csv', index=False)

        final_data = pd.read_csv('final_result.csv')
        column_order = ['NFO Trading Symbol', 'Trading Symbol', 'Lotsize', 'LTP', 'PERCENTAGEOF_LTP',
                        'PREMIUM_COLLECTED', 'ATM_CE_AND_PE']

        remaining_columns = [col for col in final_data.columns if col not in column_order]
        column_order.extend(remaining_columns)
        # Rearrange the columns according to the new order
        today_date = datetime.today().date()
        formatted_date = today_date.strftime('%Y-%m-%d')
        formatted_date_string = str(formatted_date)

        final_data = final_data[column_order]

        final_data.to_csv('UniqueInstrumentsnfo.csv', index=False)

        if 'NFO Trading Symbol' in final_data.columns:
            final_data = final_data.drop(columns='NFO Trading Symbol')
        if 'Symbol' in final_data.columns:
            final_data = final_data.drop(columns='Symbol')
        if formatted_date_string in final_data.columns:
            final_data = final_data.drop(columns=formatted_date_string)



        final_data.to_csv('webdata.csv', index=False)




    except Exception as e:
        print(f"An error occurred: {str(e)}")
        exc_type, exc_value, exc_traceback = sys.exc_info()

        print("*** Traceback ***")

        traceback.print_tb(exc_traceback)


#
# def checking_data():
#     gf = pd.read_csv('premium_combined_pivoted_data.csv')
#     first_column_header = gf.columns[1]
#     column_date = datetime.strptime(first_column_header, '%Y-%m-%d').date()
#     today_date = datetime.today().date()
#     difference_in_days = abs((column_date - today_date).days)
#     print(difference_in_days)
#     today_date = datetime.today().date()
#     list_of_dates = [
#         (today_date - timedelta(days=i)).strftime('%Y-%m-%d')
#         for i in range(1, difference_in_days)
#     ]
#
#     print(list_of_dates)
#     df = pd.read_csv("UniqueInstrumentsnfo.csv")
#     pf = pd.read_csv("Instruments.csv")
#     trading_symbols_dict = {}
#
#     monthlyexp = credentials_dict.get('monthlyexp')
#     monthlyexp = datetime.strptime(monthlyexp, "%d-%m-%Y")
#     monthlyexp = monthlyexp.strftime("%Y-%m-%d")
#
#     for symbol in df["Trading Symbol"]:
#         matching_row = pf[pf["tradingsymbol"] == symbol]
#         if not matching_row.empty:
#             instrument_token = matching_row.iloc[0]["instrument_token"]
#             historical_data = Zerodha_Integration.get_historical_data(instrument_token)
#
#             # Extracting all date and close price pairs from historical data
#             date_values = historical_data['date'][:10]  # Assuming you want the first 10 dates
#             close_prices = historical_data['close'][:10]  # Assuming you want the first 10 close prices
#
#             # Update the dictionary
#             info = {}
#             for idx in range(10):
#                 if idx < len(date_values) and idx < len(close_prices):
#                     # Get the date and close price
#                     date_value = date_values.iloc[idx]
#                     close_price = close_prices.iloc[idx]
#                     nfo_trading_symbol_value = df[df["Trading Symbol"] == symbol]["NFO Trading Symbol"].iloc[0]
#                     cesymname, pesymname = ATM_CE_AND_PE_COMBIMED_10day_ver(close_price, nfo_trading_symbol_value)
#                     ce_row = pf[pf['tradingsymbol'] == cesymname]
#                     pe_row = pf[pf['tradingsymbol'] == pesymname]
#                     ce_close_price = Zerodha_Integration.get_historical_data_combined_scanner(
#                         ce_row.iloc[0]['instrument_token'], date_value,difference_in_days)
#                     pe_close_price = Zerodha_Integration.get_historical_data_combined_scanner(
#                         pe_row.iloc[0]['instrument_token'], date_value,difference_in_days)
#                     if ce_close_price is not None and pe_close_price is not None:
#                         premium_combined = ce_close_price + pe_close_price
#                     else:
#                         premium_combined = None
#                     # Calculate premium_combined
#                     info[date_value] = {
#                         "close_price": close_price,
#                         "cesymname": cesymname,
#                         "pesymname": pesymname,
#                         "ce_instrument_token": ce_row.iloc[0]['instrument_token'] if not ce_row.empty else None,
#                         "pe_instrument_token": pe_row.iloc[0]['instrument_token'] if not pe_row.empty else None,
#                         "cecloseprice": ce_close_price,
#                         "peprice": pe_close_price,
#                         "premium_combined": premium_combined
#
#                     }
#                 else:
#                     break
#             trading_symbols_dict[symbol] = {
#                 "instrument_token": instrument_token,
#                 "monthlyexp": monthlyexp,
#                 "symbol": nfo_trading_symbol_value,
#                 "info": info,
#
#             }
#
#     columns = list(trading_symbols_dict.keys())
#     date_columns = list(trading_symbols_dict[columns[0]]["info"].keys())
#     # Create a DataFrame from 'data' with 'columns' and 'date_columns'
#     data = []
#
#     for symbol in columns:
#         row = [trading_symbols_dict[symbol]["info"][date]["premium_combined"] for date in date_columns]
#         data.append(row)
#
#     # Create the DataFrame
#     df = pd.DataFrame(data, columns=date_columns, index=columns)
#
#     # Pivot the DataFrame
#     df = df.T.reset_index()
#     df.columns.name = None  # Remove the columns' name
#     df = df.rename(columns={'index': 'Date'})  # Rename 'index' to 'Date'
#     # Save to CSV
#     df.to_csv("merger.csv", index=False)
#     data_formating_scanner()
#
#
#
# # checking_data()
#

@app.route('/')
def index():
    try:
        df = pd.read_csv("webdata.csv")
        df = df.drop(columns=['Unnamed: 0', 'Unnamed: 0.1','NFO Trading Symbol'], errors='ignore')
        html_table = df.to_html(index=False, classes='sortable')  # Add 'sortable' class

    except Exception as e:
        print(f"Error happened in rendering: {str(e)}")
        html_table = "<p>Error occurred while rendering the table.</p>"

    return render_template('index.html', html_table=html_table)







current_time=None
if __name__ == '__main__':
    kite = Zerodha_Integration.login(user_id, password, twofa)
    instruments = kite.instruments("NFO")
    df = pd.DataFrame(instruments)
    df.to_csv("Instruments.csv")
    extract_and_save_symbols_nfo(input_file="Instruments.csv", output_file="UniqueInstrumentsnfo.csv")
    get_symbol_data()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Create a scheduler and add the job
    scheduler = BackgroundScheduler()
    scheduler.add_job(get_symbol_data, 'interval', minutes=Mins)
    scheduler.start()

    # Start the Flask app
    app.run()




