import streamlit as st
import pandas as pd
import gspread
import googlemaps
import logging
import folium
import numpy as np
import plotly.express as px
from streamlit_folium import folium_static
from gspread_dataframe import get_as_dataframe
from google.oauth2 import service_account
from folium.plugins import MarkerCluster

# Authenticate with Google Sheets using your credentials JSON file
from oauth2client.service_account import ServiceAccountCredentials

# Configure the logging settings
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

st.set_page_config(layout="wide")


# Create a connection object.
credentials = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive", ],
        )
        
gc = gspread.authorize(credentials)

sheet = gc.open('PPR').sheet1

def get_lat_lon(eircode, address, max_retries=3):
    API_KEY = st.secrets["API_KEY"]
    gmaps = googlemaps.Client(key=API_KEY)
    backoff_factor = 1.5  # Determines the backoff period

    for attempt in range(1, max_retries + 1):
        try:
            # If Eircode is missing, try to get it from the address
            if pd.isnull(eircode) or eircode == '':
                eircode_result = gmaps.places(address)
                if eircode_result['results']:
                    eircode_info = eircode_result['results'][0]
                    if 'postcode' in eircode_info:
                        eircode = eircode_info['postcode']

            # Geocode the address to obtain latitude and longitude
            geocode_result = gmaps.geocode(address)
            if geocode_result:
                location = geocode_result[0]['geometry']['location']
                lat, lon = location['lat'], location['lng']
                st.info(f'Geocoding successful for address: {address}')
                return lat, lon, eircode
        except Exception as e:
            error_str = str(e)
            if 'quota exceeded' in error_str.lower() or '429' in error_str:
                wait_time = backoff_factor ** (attempt - 1)
                st.error(f'Attempt {attempt} failed due to rate limit: {e}. Retrying in {wait_time:.2f} seconds.')
                time.sleep(wait_time)
            else:
                st.error(f'Attempt {attempt} failed with error: {e}. No more retries.')
                return None, None, eircode

    # If all retries failed due to rate limit
    st.warning(f'Geocoding failed for address: {address} after {max_retries} attempts due to rate limits.')
    return None, None, eircode



def get_color(price):
    """Determine the color for a property based on its price quantile."""
    for i in range(len(quantiles)-1):
        if quantiles[i] <= price <= quantiles[i+1]:
            return gradient_colors[i]
    return 'gray'  # Default color if something goes wrong

# Create a function to load the data and cache it
@st.cache_data
def load_data():
    # Load the Google Sheet by its URL or title
    data = sheet.get_all_records()
    df = pd.DataFrame(data)

    return df



# Load the data using the cache
data = load_data()

# Create user inputs for filtering by Eircode and Address
eircode_input = st.text_input("Enter Eircode:")
address_input = st.text_input("Enter Address:")

# Extract the first three characters from the full Eircode input
eircode_prefix = eircode_input[:3].upper() if eircode_input else ""

# Filter the data based on user inputs
filtered_data = data.copy()

exact_match = None  # Initialize a flag for exact Eircode match

if eircode_prefix:
    filtered_data = filtered_data[filtered_data['Eircode'].str.startswith(eircode_prefix)]
    exact_match = data[data['Eircode'] == eircode_input]  # Check for an exact match

if address_input:
    filtered_data = filtered_data[filtered_data['Address'].str.contains(address_input, case=False, na=False)]

# Remove duplicate rows based on the whole row
filtered_data = filtered_data.drop_duplicates()



# Display a special message and exact match data if an exact match is found
if exact_match is not None and not exact_match.empty:
    st.subheader("Exact Eircode Match Found:")
    st.write(exact_match)

# Display the filtered data
st.subheader("Filtered Data:")


# Convert the 'Date of Sale (dd/mm/yyyy)' column to datetime
filtered_data['Date of Sale (dd/mm/yyyy)'] = dfiltered_dataf['Date of Sale (dd/mm/yyyy)'].dt.strftime('%Y%m%d')

filtered_data = filtered_data.sort_values(by='Date of Sale (dd/mm/yyyy)')
filtered_data['Adjusted_Price'] = pd.to_numeric(filtered_data['Adjusted_Price'], errors='coerce')
formatted_df = filtered_data.style.format({
    'Adjusted_Price': lambda x: '{:,.0f}'.format(x) if pd.notnull(x) else '',
                'Price': lambda x: '{:,.0f}'.format(x) if pd.notnull(x) else ''

})
formatted_df


# Check if the user has inputted data
user_has_input = bool(eircode_input or address_input)


if bool(eircode_input or address_input):
    pass
else:
    st.stop()

if len(filtered_data) < 100:

    for index, row in filtered_data.iterrows():

        if pd.isnull(row['latitude']) or pd.isnull(row['longitude']) or row['latitude'] == '' or row['longitude'] == '':
            address = row['Address']
            eircode = row['Eircode']
            logging.info(f'Geocoding address: {address}')
            lat, lon, updated_eircode = get_lat_lon(eircode, address)
            if lat is not None and lon is not None:
                filtered_data.at[index, 'latitude'] = lat
                filtered_data.at[index, 'longitude'] = lon
                logging.info(f'Updated latitude: {lat}, longitude: {lon}')

                try:
                    # Update the Google Sheet
                    sheet.update_cell(index + 2, filtered_data.columns.get_loc('latitude') + 1, lat)
                    sheet.update_cell(index + 2, filtered_data.columns.get_loc('longitude') + 1, lon)
                    # Update the Eircode in the Google Sheet if it's missing
                    if pd.isnull(row['Eircode']) or row['Eircode'] == '':
                        sheet.update_cell(index + 2, filtered_data.columns.get_loc('Eircode') + 1, eircode)
                        logging.info("Update successful")
                except Exception as e:
                            logging.error(f"Update failed: {str(e)}")
            else:
                logging.warning(f'Geocoding failed for address: {address}')
    load_data.clear()


else:
    st.write("Too many addresses")
    st.stop()        



# Drop rows with NaN or empty string values in 'latitude' or 'longitude' columns
filtered_data = filtered_data.dropna(subset=['latitude', 'longitude'])
filtered_data = filtered_data[filtered_data['latitude'] != '']

st.title('Google Sheet Data on Map')

# Create a map object using folium
m = folium.Map(location=[filtered_data['latitude'].mean(), filtered_data['longitude'].mean()], zoom_start=15)

# Define colors for each quantile
gradient_colors = ['#00FF00', '#FFFF00', '#FFA500', '#FF0000']  # Green to Red gradient

# Calculate quantile values for prices in your dataset
quantiles = list(filtered_data['Price'].quantile(np.linspace(0, 1, len(gradient_colors)+1)))

filtered_data['Adjusted_Price'] = filtered_data['Adjusted_Price'].fillna(filtered_data['Price'])

# Iterate over the DataFrame and add markers with popups

for index, row in filtered_data.iterrows():
    full_address = row['Address']
    original_price = int(row['Price']) / 1000 
    adjusted_price = int(row['Adjusted_Price']) / 1000   # Convert the price to thousands
    popup_text = f"Original Price: €{original_price:.0f}, <br> Adjusted Price: €{adjusted_price:.0f}K, <br> Date: {row['Date of Sale (dd/mm/yyyy)']},<br>Address: {full_address}"
    color = get_color(original_price)
    folium.CircleMarker(
        [row['latitude'], row['longitude']],
        popup=popup_text,
        radius=6,
        tooltip=popup_text,
        color=gradient_colors,
        fill=True,
        fill_color=color,
        fill_opacity=0.6,
    ).add_to(m)

# Display the map in Streamlit with custom width and height
st.markdown(folium_static(m, width=1200, height=800), unsafe_allow_html=True)

# Loop through each color and its corresponding price range to display the legend
for color, price_range in zip(gradient_colors, [f"{quantiles[i]:,.2f} - {quantiles[i+1]:,.2f}" for i in range(len(quantiles)-1)]):
    circle_emoji = f"⬤"  # This is a solid circle emoji
    st.markdown(f"<span style='color: {color}'>{circle_emoji}</span>  {price_range}", unsafe_allow_html=True)


