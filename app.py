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

continents = ['World', 'Asia', 'Oceania', 'Europe', 'Africa', 'North America', 'South America', 'Antarctica']
continents_excl_world = ['Asia', 'Oceania', 'Europe', 'Africa', 'North America', 'South America', 'Antarctica']

# ---------------------------
# 3. CO2 over time by continent
# ---------------------------
st.subheader("CO₂ Emissions over Time by Continent")

# Pretty label → actual df column mapping
co2_label_map = {
    "CO₂": "co2",
    "CO₂/capita": "co2_per_capita",
}

col1, col2 = st.columns([1,4])
with col1:
    pretty_CO2 = st.radio(
        "CO₂ Measure",
        list(co2_label_map.keys()),
        horizontal=True
    )

# Convert pretty label → actual dataframe column
yaxis_CO2 = co2_label_map[pretty_CO2]

CO2_pipeline = (
    df[(df['year'] <= year) & (df['country'].isin(continents))]
      .groupby(['country', 'year'])[yaxis_CO2].mean()
      .reset_index()
      .sort_values('year')
)

fig_CO2 = px.line(
    CO2_pipeline,
    x='year',
    y=yaxis_CO2,
    color='country',
    title=f"{pretty_CO2} over Time by Continent"
)

st.plotly_chart(fig_CO2, use_container_width=True)

# ---------------------------
# 4. CO2 vs GDP scatter
# ---------------------------
st.subheader(f"CO₂ vs GDP per Capita ({year})")

CO2_vs_gdp_pipeline = (
    df[(df['year'] == year) & (~df['country'].isin(continents))]
      .groupby(['country', 'gdp_per_capita'])['co2'].mean()
      .reset_index()
)

fig_scatter = px.scatter(
    CO2_vs_gdp_pipeline,
    x='gdp_per_capita',
    y='co2',
    color='country',
    hover_name='country',
    size=np.ones(len(CO2_vs_gdp_pipeline)) * 10,
    title=f"CO₂ vs GDP per Capita ({year})",
    labels={'gdp_per_capita':'GDP per Capita', 'CO2':'CO₂ Emissions'}
)
st.plotly_chart(fig_scatter, use_container_width=True)

# ---------------------------
# 5. CO2 source bar chart
# ---------------------------
# ---------------------------
# 5. CO₂ Source bar chart (local controls)
# ---------------------------
st.subheader(f"CO₂ Sources by Continent ({year})")

# Map pretty labels → actual dataframe column names
source_label_map = {
    "CO₂ from Coal": "coal_co2",
    "CO₂ from Oil": "oil_co2",
    "CO₂ from Gas": "gas_co2",
}

# Local-only options for source type
pretty_choice = st.radio(
    "Select CO₂ Source:",
    list(source_label_map.keys()),
    horizontal=True,
    key="source_selector"
)

# Convert label → column name
yaxis_CO2_source = source_label_map[pretty_choice]

CO2_source_pipeline = (
    df[(df['year'] == year) & (df['country'].isin(continents_excl_world))]
      .groupby(['country'])[yaxis_CO2_source].sum()
      .reset_index()
      .sort_values(yaxis_CO2_source, ascending=False)
)

fig_bar = px.bar(
    CO2_source_pipeline,
    x='country',
    y=yaxis_CO2_source,
    color='country',
    title=f"{pretty_choice} by Continent ({year})",
    labels={yaxis_CO2_source: pretty_choice}
)

st.plotly_chart(fig_bar, use_container_width=True)


# ---------------------------
# 6. Optional table view
# ---------------------------
st.subheader("CO₂ Data Table")
st.dataframe(CO2_pipeline)

@st.cache_data
def load_country_coords():
    url = "https://raw.githubusercontent.com/johan/world.geo.json/master/countries.geo.json"
    geojson = requests.get(url).json()

    rows = []
    for feat in geojson["features"]:
        props = feat["properties"]
        geometry = feat["geometry"]

        # Extract centroid of polygon
        if geometry["type"] == "Polygon":
            coords = np.array(geometry["coordinates"][0])
        else:  # MultiPolygon
            coords = np.array(geometry["coordinates"][0][0])

        lon = coords[:, 0].mean()
        lat = coords[:, 1].mean()

        rows.append({
            "country": props["name"],
            "latitude": lat,
            "longitude": lon,
        })

    return pd.DataFrame(rows)


coords = load_country_coords()
df = df.merge(coords, on="country", how="left")

st.subheader(f"Global CO₂ Heatmap ({year})")

df_3d = df[df["year"] == year].copy()

fig_globe = px.choropleth(
    df_3d,
    locations="iso_code",      # must be ISO country codes (OWID already has this)
    color="co2",               # heatmap variable
    hover_name="country",
    projection="orthographic", # <-- Makes it a globe
    color_continuous_scale="Reds",
    range_color=(0, 17000)
)

fig_globe.update_geos(
    showcoastlines=True,
    coastlinecolor="black",
    showland=True,
    landcolor="rgb(230,230,230)",
    showocean=True,
    oceancolor="rgb(180,220,250)",
)

fig_globe.update_layout(
    height=700,
    margin=dict(l=0, r=0, t=40, b=0),
    coloraxis_colorbar=dict(
        title="CO₂ (Mt)",
        thicknessmode="pixels", thickness=15,
        lenmode="fraction", len=0.75
    )
)

st.plotly_chart(fig_globe, use_container_width=True)
