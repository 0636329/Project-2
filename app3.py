from datetime import datetime
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import pytz
import requests

def get_geocoding(location):
    params = {
        "name": location,
        "count": 1,
        "language": "en",
        "format": "json"
    }

    response = requests.get("https://geocoding-api.open-meteo.com/v1/search", params=params)
    response.raise_for_status()
    data = response.json()

    if not data.get("results"):
        return None

    result = data["results"][0]
    return {
        "name": result["name"],
        "lat": result["latitude"],
        "lon": result["longitude"],
        "timezone": result["timezone"],
        "country": result["country"]
    }

def get_weather_data(lat, lon, timezone, temperature_unit, forecast_choice):
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,relativehumidity_2m,precipitation_probability,visibility",
        "daily": "weathercode,temperature_2m_max,temperature_2m_min,uv_index_max,precipitation_sum,sunrise,sunset",
        "timezone": timezone,
        "temperature_unit": temperature_unit.lower(),
        "forecast_days": forecast_choice
    }

    response = requests.get("https://api.open-meteo.com/v1/forecast", params=params)
    response.raise_for_status()
    return response.json(), None

def weather_code(code):
    codes = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        56: "Light freezing drizzle",
        57: "Dense freezing drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        66: "Light freezing rain",
        67: "Heavy freezing rain",
        71: "Slight snow fall",
        73: "Moderate snow fall",
        75: "Heavy snow fall",
        77: "Snow grains",
        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        85: "Slight snow showers",
        86: "Heavy snow showers",
        95: "Thunderstorm",
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail"
    }
    return codes.get(code, "Unknown")

with st.sidebar:

    st.title("Setting")
    location = st.text_input("Enter City or Zip Code", placeholder="Miami")
    forecast_choice = st.selectbox(
        "Select Forecast Days",
        ("3","7","14","16"),
        index=1
    )
    temp_unit = st.radio("Select Temperature Unit", ["°F", "°C"])
    st.markdown("Additional Options")
    show_map = st.checkbox("Show Map")
    fetch_button = st.button("Get Weather", type="primary", help="Click to Check Weather")
    status_container = st.empty()

weather_data = None
city_data = None

if fetch_button:
    status_container.info("Fetching weather data...")
    city_data = get_geocoding(location)
    if not city_data:
        status_container.error("Location not found. Verify city/zip code.")
    else:
        weather_data, error = get_weather_data(
            city_data["lat"],
            city_data["lon"],
            city_data["timezone"],
            "celsius" if temp_unit == "°C" else "fahrenheit",
            forecast_choice
        )
        if error:
            status_container.error(f"Failed to fetch weather data : {error}")
        else:
            status_container.success("Weather data loaded.")

if weather_data is not None and city_data:
    st.title(f"{city_data['name']}, {city_data['country']}")
    if show_map:
        map_data = pd.DataFrame({
            "lat": [city_data["lat"]],
            "lon": [city_data["lon"]],
            "city": [city_data["name"]]
        })
        st.map(map_data)
    st.divider()
    st.subheader("Hourly Forecast")
    current_time = datetime.now(pytz.timezone(city_data["timezone"]))
    hourly = weather_data["hourly"]
    current_index = next((i for i, t in enumerate(hourly["time"])
                          if t.startswith(current_time.strftime("%Y-%m-%dT%H"))), None)

    if current_index is not None:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Temperature", f"{hourly['temperature_2m'][current_index]:.1f}{temp_unit}")
        with col2:
            st.metric("Relative Humidity", f"{hourly['relativehumidity_2m'][current_index]}%")
        with col3:
            st.metric("Precipitation Probability", f"{hourly['precipitation_probability'][current_index]}%")
        with col4:
            visibility_mi = hourly['visibility'][current_index] * 0.000621371
            st.metric("Visibility", f"{visibility_mi:.1f} mi")
    st.divider()

    st.subheader("Daily Temperature Trends")
    daily_times = weather_data["daily"]["time"]
    min_temps = weather_data["daily"]["temperature_2m_min"]
    max_temps = weather_data["daily"]["temperature_2m_max"]

    fig, ax = plt.subplots()
    ax.plot(daily_times, min_temps, 'o-', label=f'Low ({temp_unit})')
    ax.plot(daily_times, max_temps, 'o-', label=f'High ({temp_unit})')
    ax.fill_between(daily_times, min_temps, max_temps, color='#bfdfff')

    for i, txt in enumerate(min_temps):
        ax.annotate(f"{txt:.1f}", (daily_times[i], min_temps[i]),
                    textcoords="offset points", xytext=(0, -12),
                    ha='center')

    for i, txt in enumerate(max_temps):
        ax.annotate(f"{txt:.1f}", (daily_times[i], max_temps[i]),
                    textcoords="offset points", xytext=(0, 7),
                    ha='center')

    ax.set_ylabel(f"Temperature ({temp_unit})")
    ax.legend()
    ax.grid()
    plt.xticks(rotation=45)
    plt.tight_layout()
    st.pyplot(fig)
    st.divider()

    st.subheader("Daily Forecast")
    daily_forecast = []
    for i in range(len(weather_data["daily"]["time"])):
        daily_forecast.append({
            "Date": weather_data["daily"]["time"][i],
            "Weather": weather_code(weather_data["daily"]["weathercode"][i]),
            "High": f"{weather_data['daily']['temperature_2m_max'][i]:.1f}{temp_unit}",
            "Low": f"{weather_data['daily']['temperature_2m_min'][i]:.1f}{temp_unit}",
            "UV Index": weather_data["daily"]["uv_index_max"][i],
            "Precipitation": f"{weather_data['daily']['precipitation_sum'][i]} mm",
            "Sunrise": weather_data["daily"]["sunrise"][i].split("T")[1],
            "Sunset": weather_data["daily"]["sunset"][i].split("T")[1]
        })
    st.dataframe(daily_forecast, hide_index=True)