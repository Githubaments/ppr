import streamlit as st
import pandas as pd
import gspread
import googlemaps
import logging
import folium
from gspread_dataframe import get_as_dataframe
from google.oauth2 import service_account

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


def get_lat_lon(address):
    API_KEY = st.secrets["API_KEY"]
    gmaps = googlemaps.Client(key=API_KEY)

    # Geocode the address to obtain latitude and longitude
    geocode_result = gmaps.geocode(address)

    if geocode_result:
        location = geocode_result[0]['geometry']['location']
        lat, lon = location['lat'], location['lng']
        st.info(f'Geocoding successful for address: {address}')
        return lat, lon
    else:
        st.warning(f'Geocoding failed for address: {address}')
        return None, None  # Handle cases where geocoding fails




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
filtered_data


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
            lat, lon = get_lat_lon(address)
            if lat is not None and lon is not None:
                filtered_data.at[index, 'latitude'] = lat
                filtered_data.at[index, 'longitude'] = lon
                logging.info(f'Updated latitude: {lat}, longitude: {lon}')

                try:
                    # Update the Google Sheet
                    sheet.update_cell(index + 2, filtered_data.columns.get_loc('latitude') + 1, lat)
                    sheet.update_cell(index + 2, filtered_data.columns.get_loc('longitude') + 1, lon)
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
m = folium.Map(location=[filtered_data['latitude'].mean(), filtered_data['longitude'].mean()], zoom_start=10)

# Iterate over the DataFrame and add markers with popups
for index, row in filtered_data.iterrows():
    popup_text = f"Price: {row['Price']}, Date: {row['Date of Sale (dd/mm/yyyy)']}"
    folium.Marker([row['latitude'], row['longitude']], popup=popup_text, tooltip=popup_text).add_to(m)

# Display the map in Streamlit
folium_static(m)

filtered_data
