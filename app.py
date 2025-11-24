# app.py
import pandas as pd
import numpy as np
import streamlit as st
import requests
from io import StringIO
import plotly.express as px

# ---------------------------
# 1. Load and cache data
# ---------------------------
@st.cache_data
def load_data():
    url = "https://raw.githubusercontent.com/owid/co2-data/master/owid-co2-data.csv"
    r = requests.get(url)
    r.raise_for_status()
    df = pd.read_csv(StringIO(r.text))
    df = df.fillna(0)
    df['gdp_per_capita'] = np.where(df['population'] != 0, df['gdp'] / df['population'], 0)
    return df

df = load_data()

# ---------------------------
# 2. Sidebar filters
# ---------------------------
st.sidebar.title("CO2 Emissions Dashboard")
st.sidebar.markdown("Adjust filters below:")

year = st.sidebar.slider(
    "Year",
    min_value=int(df['year'].min()),
    max_value=int(df['year'].max()),
    step=5,
    value=2010
)

yaxis_co2 = st.sidebar.radio("CO2 Measure", ['co2', 'co2_per_capita'])
yaxis_co2_source = st.sidebar.radio("CO2 Source", ['coal_co2', 'oil_co2', 'gas_co2'])

continents = ['World', 'Asia', 'Oceania', 'Europe', 'Africa', 'North America', 'South America', 'Antarctica']
continents_excl_world = ['Asia', 'Oceania', 'Europe', 'Africa', 'North America', 'South America', 'Antarctica']

# ---------------------------
# 3. CO2 over time by continent
# ---------------------------
st.subheader("CO2 Emissions by Continent")

co2_pipeline = (
    df[(df['year'] <= year) & (df['country'].isin(continents))]
      .groupby(['country', 'year'])[yaxis_co2].mean()
      .reset_index()
      .sort_values('year')
)

fig_co2 = px.line(
    co2_pipeline,
    x='year',
    y=yaxis_co2,
    color='country',
    title=f"{yaxis_co2} over Time by Continent"
)
st.plotly_chart(fig_co2, use_container_width=True)

# ---------------------------
# 4. CO2 vs GDP scatter
# ---------------------------
st.subheader(f"CO2 vs GDP per Capita ({year})")

co2_vs_gdp_pipeline = (
    df[(df['year'] == year) & (~df['country'].isin(continents))]
      .groupby(['country', 'gdp_per_capita'])['co2'].mean()
      .reset_index()
)

fig_scatter = px.scatter(
    co2_vs_gdp_pipeline,
    x='gdp_per_capita',
    y='co2',
    color='country',
    hover_name='country',
    size=np.ones(len(co2_vs_gdp_pipeline)) * 10,
    title=f"CO2 vs GDP per Capita ({year})",
    labels={'gdp_per_capita':'GDP per Capita', 'co2':'CO2 Emissions'}
)
st.plotly_chart(fig_scatter, use_container_width=True)

# ---------------------------
# 5. CO2 source bar chart
# ---------------------------
st.subheader(f"CO2 Sources by Continent ({year})")

co2_source_pipeline = (
    df[(df['year'] == year) & (df['country'].isin(continents_excl_world))]
      .groupby(['country'])[yaxis_co2_source].sum()
      .reset_index()
      .sort_values(yaxis_co2_source, ascending=False)
)

fig_bar = px.bar(
    co2_source_pipeline,
    x='country',
    y=yaxis_co2_source,
    color='country',
    title=f"{yaxis_co2_source} Emissions by Continent",
    labels={yaxis_co2_source:yaxis_co2_source.capitalize()}
)
st.plotly_chart(fig_bar, use_container_width=True)

# ---------------------------
# 6. Optional table view
# ---------------------------
st.subheader("CO2 Data Table")
st.dataframe(co2_pipeline)
