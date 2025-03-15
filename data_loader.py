import pandas as pd
import requests
import io

##############################################################
# 1. LOAD AGGREGATED (COUNTRY-LEVEL) TIME SERIES FOR CASES/DEATHS
##############################################################
def load_time_series(url):
    response = requests.get(url, verify=False)  # SSL verification disabled for debugging
    response.raise_for_status()
    data = pd.read_csv(io.StringIO(response.text))
    date_cols = data.columns[4:]
    data_grouped = data.groupby("Country/Region")[date_cols].sum()
    data_grouped = data_grouped.transpose()
    data_grouped.index = pd.to_datetime(data_grouped.index, format="%m/%d/%y")
    return data_grouped

def load_all_data():
    # Confirmed (Cases) and Deaths only
    confirmed_url = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/refs/heads/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_global.csv"
    deaths_url = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/refs/heads/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv"

    data_confirmed = load_time_series(confirmed_url)
    data_deaths = load_time_series(deaths_url)
    return data_confirmed, data_deaths

##############################################################
# 2. LOAD RAW DATA FOR PROVINCE-LEVEL PROCESSING & MAPPING
#    (CASES & DEATHS ONLY, NO RECOVERED)
##############################################################
def load_raw_confirmed():
    confirmed_url = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/refs/heads/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_global.csv"
    df = pd.read_csv(confirmed_url, keep_default_na=False)
    return df

def load_raw_deaths():
    deaths_url = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/refs/heads/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv"
    df = pd.read_csv(deaths_url, keep_default_na=False)
    return df

##############################################################
# 3. LOAD LOCATION DATA (NO AVERAGING OF LAT & LONG)
##############################################################
def load_location_data():
    """
    Creates a DataFrame with unique (Country/Region, Province/State) -> (Lat, Long)
    If Province/State is empty, that row is the 'country-level' entry.
    """
    confirmed_url = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/refs/heads/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_global.csv"
    response = requests.get(confirmed_url, verify=False)
    response.raise_for_status()
    df = pd.read_csv(io.StringIO(response.text), keep_default_na=False)

    df_loc = df[["Country/Region", "Province/State", "Lat", "Long"]].drop_duplicates()
    return df_loc
