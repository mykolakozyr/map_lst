import streamlit as st
import json
import geojson
import ee
import pandas as pd
import geopandas as gpd
import altair as alt
import folium
from folium.plugins import Draw
from streamlit_folium import st_folium
from streamlit_folium import folium_static 


MAP_EMOJI_URL = "https://em-content.zobj.net/source/apple/354/thermometer_1f321-fe0f.png"

# Set page title and favicon.
st.set_page_config(
    page_title="Land Surface Temperature - Location Input", 
    page_icon=MAP_EMOJI_URL
)

# Display header.
st.markdown("<br>", unsafe_allow_html=True)
st.image(MAP_EMOJI_URL, width=80)
st.markdown("""
    # Land Surface Temperature - Location Input
    [![Follow](https://img.shields.io/twitter/follow/mykolakozyr?style=social)](https://www.twitter.com/mykolakozyr)
    [![Follow](https://img.shields.io/badge/LinkedIn-blue?style=flat&logo=linkedin&labelColor=blue)](https://www.linkedin.com/in/mykolakozyr/)
    [![Buy me a coffee](https://img.shields.io/badge/Buy%20me%20a%20coffee--yellow.svg?logo=buy-me-a-coffee&logoColor=orange&style=social)](https://www.buymeacoffee.com/mykolakozyr)
    
    ## Details

    The app enables discovering land surface temperature data over a custom location input.

    Data details:
    - Temporal extent: 2000-02-18 till today.
    - Spatial resolution: 1000m per pixel.

    App uses [Google Earth Engine](https://earthengine.google.com/) to collect and process land surface temperature data. 
    Here is [the blog post on how to start using Google Earth Engine API within your Streamlit app](https://medium.com/@mykolakozyr/using-google-earth-engine-in-a-streamlit-app-62c729793007).

    ---
    """)

# Main app that collects data in the AOI and returns the chart.
def app(aoi):
    aoi = ee.FeatureCollection(ee.Geometry(aoi_json)).geometry()
    with st.spinner("Collecting data using Google Earth Engine..."):
        # Getting LST data
        lst = ee.ImageCollection('MODIS/061/MOD11A2').filterDate(date_range).select('LST_Day_1km')
        reduce_lst = gee.create_reduce_region_function(
        geometry=aoi, reducer=ee.Reducer.mean(), scale=1000, crs='EPSG:4326')
        lst_stat_fc = ee.FeatureCollection(lst.map(reduce_lst)).filter(ee.Filter.notNull(lst.first().bandNames()))
        try:
            lst_dict = gee.fc_to_dict(lst_stat_fc).getInfo()
        except:
            st.error('Ooops, looks like Google Earth Engine cannot collect data in this area. Please ping me on [Twitter](https://twitter.com/MykolaKozyr) or [LinkedIn](https://www.linkedin.com/in/mykolakozyr/) to debug the issue together.')
            st.stop()
        lst_df = pd.DataFrame(lst_dict)
        lst_df['LST_Day_1km'] = (lst_df['LST_Day_1km'] * 0.02 - 273.5)
        lst_df = gee.add_date_info(lst_df)

        # Creating the Chart
        # Line Chart with Points: https://altair-viz.github.io/gallery/line_chart_with_points.html
        line_layer_chart = alt.layer(
            alt.Chart().mark_line(point=alt.OverlayMarkDef(stroke="white", fill=None)),
            alt.Chart().mark_line(point=alt.OverlayMarkDef(stroke="white", fill=None)).encode(color=alt.Color('good:N', legend=None)),
            data=lst_df
        ).transform_calculate(
            good="datum.LST_Day_1km>0",
        ).encode(
            y=alt.Y('Timestamp:T', impute={'value': None}),
            x=alt.X('LST_Day_1km:Q', impute={'value': None}, axis=alt.Axis(orient="top"), title='Land Surface Temperature, °C'),
            tooltip=[alt.Tooltip('Timestamp', title="Date"), alt.Tooltip('LST_Day_1km', title="Temperature, °C")]
        ).properties(height=8000)

        return line_layer_chart

# Creating map for data input.
m = folium.Map(location=[48.921741, 9.642971], zoom_start=5)
Draw(
    export=False,
    draw_options={'circle':False, 'circlemarker':False, 'polyline':False, 'rectangle':False, 'polygon':False, 'repeatMode':False},
    edit_options={'remove':False, 'edit':False}
    ).add_to(m)

# Creating a form to get data input. App won't update itself while map is in use.
with st.form(key='my_form'):
    output = st_folium(m, width = 700, height=500)
    submit_button = st.form_submit_button(label='Discover the Land Surface Temperature Data!')

# Collecting and visualizing data.
if submit_button:
    try:
        aoi_json = output['last_active_drawing']['geometry']
    except TypeError:
        st.warning('Location is missing. Please draw a point on the map.')
        st.stop()

    # Authenticating and Initializing GEE
    json_data = st.secrets["json_data"]
    service_account = st.secrets["service_account"]
    json_object = json.loads(json_data, strict=False)
    json_object = json.dumps(json_object)
    credentials = ee.ServiceAccountCredentials(service_account, key_data=json_object)
    ee.Initialize(credentials)

    import src.gee as gee

    # Defining the temporal extent of the discovery.
    today = ee.Date(pd.to_datetime('today'))
    date_range = ee.DateRange('2000-02-18', today)

    # Running an app that builds the chart.
    line_layer_chart = app(aoi_json)
    st.altair_chart(line_layer_chart, use_container_width=True)

    st.markdown("""
        ## References
        * Land Surface Temperature - [MODIS via Google Earth Engine.](https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD11A2)
        * Library for visualizations - [Vega-Altair](https://altair-viz.github.io/index.html).
        """
    )
