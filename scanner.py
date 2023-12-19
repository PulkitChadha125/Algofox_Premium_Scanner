from kite_trade import *
import pyotp
import pandas as pd
from datetime import datetime
import Zerodha_Integration
import threading
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, render_template
lock = threading.Lock()
import os
import sys

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
    try:
        print("Updating Data...")
        df= pd.read_csv("UniqueInstrumentsnfo.csv")
        df["LTP"] = None
        df["ATM_CE_AND_PE"] = None
        df["PERCENTAGEOF_LTP"] = None
        df["PREMIUM_COLLECTED"] = None
        for index, row in df.iterrows():
            symbol = row['Trading Symbol']
            ins=row['NFO Trading Symbol']
            lots=row['Lotsize']
            try:
                res = Zerodha_Integration.get_ltp_option(symbol)
                combinedpremium= ATM_CE_AND_PE_COMBIMED(res,ins)
                percentof= calculate_xpercent(res, combinedpremium)
                df.at[index, 'ATM_CE_AND_PE'] = combinedpremium
                df.at[index, 'LTP'] = res
                df.at[index, 'PREMIUM_COLLECTED']=PREMIUM_COLLECTED(lots,combinedpremium)
                df.at[index, 'PERCENTAGEOF_LTP'] =percentof
                df = df.drop(columns=['Unnamed: 0'], errors='ignore')




            except Exception as e:
                print(f"An error occurred while getting ltp : {str(e)}")

        df.to_csv("UniqueInstrumentsnfo.csv")
        df.to_csv("webdata.csv")



    except Exception as e:
        print(f"An error occurred: {str(e)}")



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




# @app.route('/')
# def index():
#     global current_time
#     html_table = None
#     try:
#         df = pd.read_csv("webdata.csv")
#
#         # Drop specific columns, ensuring they exist before dropping
#         if 'Unnamed: 0' in df.columns:
#             df = df.drop(columns=['Unnamed: 0'], errors='ignore')
#         if 'Unnamed: 0.1' in df.columns:
#             df = df.drop(columns=['Unnamed: 0.1'], errors='ignore')
#
#         # Check if the DataFrame has any rows
#         if not df.empty:
#             html_table = df.to_html(index=False)
#
#     except Exception as e:
#         print(f"Error happened in rendering: {str(e)}")
#
#     return render_template('index.html', html_table=html_table, last_updated=current_time)


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




