import streamlit as st
import folium
import pandas as pd
import altair as alt
from streamlit_folium import st_folium

from data_loader import (
    load_all_data,
    load_raw_confirmed,
    load_raw_deaths,
    load_location_data
)

st.set_page_config(layout="wide", page_title="COVID-19 Dashboard")

#####################################
# 1. Load Data
#####################################
@st.cache_data
def get_country_level_data():
    data_confirmed, data_deaths = load_all_data()
    return data_confirmed, data_deaths

data_confirmed, data_deaths = get_country_level_data()
raw_confirmed = load_raw_confirmed()
raw_deaths = load_raw_deaths()
df_locations = load_location_data()

#####################################
# 2. Helper Functions
#####################################
def extract_time_series(raw_df, country, province="All"):
    subset = raw_df[raw_df["Country/Region"] == country]
    if province != "All":
        subset = subset[subset["Province/State"] == province]
    if subset.empty:
        return pd.Series(dtype=float)
    date_cols = subset.columns[4:]
    ts = subset[date_cols].sum(axis=0)
    ts.index = pd.to_datetime(ts.index, format="%m/%d/%y")
    return ts

def get_lat_long(country, province):
    subset = df_locations[df_locations["Country/Region"] == country]
    if subset.empty:
        return None, None
    if province == "All":
        row = subset[subset["Province/State"] == ""]
        if not row.empty:
            lat = float(row["Lat"].iloc[0])
            lon = float(row["Long"].iloc[0])
            return lat, lon
        else:
            lat = float(subset["Lat"].iloc[0])
            lon = float(subset["Long"].iloc[0])
            return lat, lon
    else:
        row = subset[subset["Province/State"] == province]
        if row.empty:
            return None, None
        lat = float(row["Lat"].iloc[0])
        lon = float(row["Long"].iloc[0])
        return lat, lon

#####################################
# 3. Main App
#####################################
def main():
    st.title("COVID-19 Dashboard")

    # ========== Sidebar Filters ==========
    st.sidebar.header("Filters")

    # Country selection
    countries = sorted(list(data_confirmed.columns))
    country_options = ["Worldwide"] + countries
    selected_country = st.sidebar.selectbox("Select Country", options=country_options)

    # Province/State selection if a specific country is chosen
    if selected_country == "Worldwide":
        selected_province = None
    else:
        subset = df_locations[df_locations["Country/Region"] == selected_country]
        provinces = sorted(subset["Province/State"].unique())
        if len(provinces) > 1:
            province_options = ["All"] + [p for p in provinces if p != ""]
            selected_province = st.sidebar.selectbox("Select Province/State", province_options)
        else:
            selected_province = "All"

    # Date range
    min_date = data_confirmed.index.min().date()
    max_date = data_confirmed.index.max().date()
    start_date = st.sidebar.date_input("Start Date", value=min_date, min_value=min_date, max_value=max_date)
    end_date = st.sidebar.date_input("End Date", value=max_date, min_value=min_date, max_value=max_date)
    st.sidebar.write("Date range:", start_date, "to", end_date)

    # Summary and Map controls
    summary_mode = st.sidebar.radio("Summary Mode", options=["Cumulative", "Daily"], index=0)
    map_option = st.sidebar.selectbox("Map Data", options=["Cases", "Deaths"])
    st.sidebar.subheader("Plot Modes")
    cases_plot_mode = st.sidebar.radio("Cases Plot Mode", options=["Cumulative", "Daily"], index=0)
    deaths_plot_mode = st.sidebar.radio("Deaths Plot Mode", options=["Cumulative", "Daily"], index=0)

    # ========== Time Series Extraction ==========
    if selected_country == "Worldwide":
        ts_confirmed = data_confirmed.sum(axis=1)
        ts_deaths = data_deaths.sum(axis=1)
    else:
        ts_confirmed = extract_time_series(raw_confirmed, selected_country, province=selected_province)
        ts_deaths = extract_time_series(raw_deaths, selected_country, province=selected_province)

    ts_confirmed = ts_confirmed.loc[start_date:end_date]
    ts_deaths = ts_deaths.loc[start_date:end_date]

    if summary_mode == "Daily":
        ts_confirmed = ts_confirmed.diff().fillna(0).clip(lower=0)
        ts_deaths = ts_deaths.diff().fillna(0).clip(lower=0)
        st.write("Note: Daily data is based on the End Date you choose.")

    try:
        latest_confirmed = int(ts_confirmed.iloc[-1])
        latest_deaths = int(ts_deaths.iloc[-1])
    except Exception:
        st.error("No data available for the selected filters.")
        return

    # ========== Summary Boxes ==========
    c1, c2 = st.columns(2)
    c1.metric("Confirmed", f"{latest_confirmed:,}")
    c2.metric("Deaths", f"{latest_deaths:,}")

    # ========== Main Layout: Map + Plots ==========
    left_col, right_col = st.columns([2, 1])
    with left_col:
        st.subheader("Map View")
        m = folium.Map(location=[20, 0], zoom_start=2, world_copy_jump=True)

        if map_option == "Cases":
            map_df = data_confirmed.loc[start_date:end_date]
            color = "red"
        else:
            map_df = data_deaths.loc[start_date:end_date]
            color = "black"

        for country in map_df.columns:
            try:
                value = map_df[country].iloc[-1]
                if value <= 0:
                    continue

                if selected_country == country and selected_country != "Worldwide" and selected_province:
                    lat, lon = get_lat_long(country, selected_province)
                    if lat is None or lon is None:
                        lat, lon = get_lat_long(country, "All")
                else:
                    lat, lon = get_lat_long(country, "All")
                if lat is None or lon is None:
                    continue

                popup_text = f"{country}: {int(value):,}"
                radius = (value ** 0.35) * 0.05
                folium.CircleMarker(
                    location=[lat, lon],
                    radius=radius,
                    color=color,
                    fill=True,
                    fill_color=color,
                    popup=popup_text
                ).add_to(m)
            except Exception:
                continue

        st_folium(m, width=700, height=500)

    with right_col:
        st.subheader("Time Series Plots")

        # Cases Altair Chart
        df_cases = pd.DataFrame({
            "Date": ts_confirmed.index,
            "Case Num": ts_confirmed.values
        })
        if cases_plot_mode == "Daily":
            df_cases["Case Num"] = df_cases["Case Num"].diff().fillna(0).clip(lower=0)
        chart_cases = (
            alt.Chart(df_cases.reset_index(drop=True))
            .mark_line()
            .encode(
                x=alt.X("Date:T", title="Date"),
                y=alt.Y("Case Num:Q", title="Case Num"),
                tooltip=[
                    alt.Tooltip("Date:T", title="Date"),
                    alt.Tooltip("Case Num:Q", title="Case Num", format=",")
                ]
            )
            .interactive()
        )
        st.altair_chart(chart_cases, use_container_width=True)

        # Deaths Altair Chart
        df_deaths_chart = pd.DataFrame({
            "Date": ts_deaths.index,
            "Deaths": ts_deaths.values
        })
        if deaths_plot_mode == "Daily":
            df_deaths_chart["Deaths"] = df_deaths_chart["Deaths"].diff().fillna(0).clip(lower=0)
        chart_deaths = (
            alt.Chart(df_deaths_chart.reset_index(drop=True))
            .mark_line()
            .encode(
                x=alt.X("Date:T", title="Date"),
                y=alt.Y("Deaths:Q", title="Deaths"),
                tooltip=[
                    alt.Tooltip("Date:T", title="Date"),
                    alt.Tooltip("Deaths:Q", title="Deaths", format=",")
                ]
            )
            .interactive()
        )
        st.altair_chart(chart_deaths, use_container_width=True)

if __name__ == "__main__":
    main()
