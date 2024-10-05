import os
import logging
import math
import pygrib
import pandas as pd
import numpy as np
import requests
from datetime import datetime

# Constants
GRAVITY_ACC = 9.80665  # Acceleration due to gravity (m/s²)
R_SPECIFIC = 287.058    # Specific gas constant for dry air (J/(kg·K))
MOLAR_MASS_AIR = 0.0289644  # kg/mol
MOLAR_MASS_HE = 0.004002602  # kg/mol
MOLAR_MASS_H2 = 0.002016  # kg/mol for Hydrogen
GAS_CONSTANT_R = 8.314462618  # Universal gas constant (J/(mol·K))
EARTH_RADIUS = 6371000  # Earth's radius in meters

# Configure Logging
def configure_logging(log_file='simulation.log'):
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    logger.addHandler(fh)
    logger.addHandler(ch)

# Variable Extraction Function
def extract_variable_pygrib(filepath, type_of_level, step_type, short_name, latitude, longitude, level=None):
    try:
        grbs = pygrib.open(filepath)
        for grb in grbs:
            if (grb.typeOfLevel == type_of_level and 
                grb.stepType == step_type and 
                grb.shortName == short_name and 
                grb.name.lower() != 'unknown'):
                if level is not None and grb.level != level:
                    continue
                data, lats, lons = grb.data(lat1=latitude, lat2=latitude, lon1=longitude, lon2=longitude)
                grbs.close()
                return data[0][0]
        grbs.close()
        logging.error(f"Variable '{short_name}' not found for TypeOfLevel='{type_of_level}', StepType='{step_type}', Level='{level}'.")
        raise ValueError(f"Variable '{short_name}' not found.")
    except Exception as e:
        logging.error(f"Error extracting variable '{short_name}': {e}")
        raise

# Initial Parameters Calculation Function
def calculate_initial_parameters(params):
    gross_mass = params.get('gross_mass', 14.0)
    lift_gas_type = params.get('lift_gas_type', 'Helium')
    max_volume_HAB_limit = params.get('max_volume_HAB_limit', 6.0)
    percent_lift_gas_scalar = params.get('percent_lift_gas_scalar', 23.0)
    buoyant_force_scalar = params.get('buoyant_force_scalar', 1.0)

    gas_properties = {
        'Helium': {'molar_mass': MOLAR_MASS_HE, 'density': 0.1786},
        'Hydrogen': {'molar_mass': MOLAR_MASS_H2, 'density': 0.08988}
    }

    lift_gas_type_capitalized = lift_gas_type.capitalize()
    gas = gas_properties.get(lift_gas_type_capitalized, gas_properties['Helium'])
    molar_mass_gas = gas['molar_mass']
    rho_gas = gas['density']

    lift_capacity = 1.02 if lift_gas_type_capitalized == 'Helium' else 1.10

    total_lift_needed_liters = (gross_mass * 1000) / lift_capacity * (1 + percent_lift_gas_scalar / 100)
    volume_gas = total_lift_needed_liters / 1000
    n_gas = (volume_gas * 1000) / 22.4
    mass_gas = n_gas * molar_mass_gas
    mass_structure = gross_mass - mass_gas

    if mass_structure < 0:
        logging.error("Mass of structure is negative. Check gross mass and gas properties.")
        raise ValueError("Mass of structure cannot be negative.")

    logging.debug(f"Calculated initial parameters: n_gas={n_gas}, mass_structure={mass_structure}, volume_gas={volume_gas}, rho_gas={rho_gas}, lift_capacity={lift_capacity}")
    return n_gas, mass_structure, volume_gas, rho_gas, lift_capacity

# Wind Calculations
def calculate_wind_direction(u, v):
    wind_dir_rad = math.atan2(u, v)
    wind_dir_deg = (wind_dir_rad * (180 / math.pi)) % 360
    return wind_dir_deg

def calculate_wind_frequency(u, v, threshold=5.0):
    wind_speed = math.sqrt(u**2 + v**2)
    return 1 if wind_speed > threshold else 0

# Balloon Flight Simulation Function
def simulate_balloon_flight_pygrib(temperature, pressure_hpa, u_wind, v_wind, mass_structure, n_gas, volume_gas, rho_gas, lift_capacity, params):
    drag_coefficient_z = params.get('drag_coefficient_z', 0.47)
    alt_chosen = params.get('alt_chosen', 10.0)
    number_forecasts = params.get('number_forecasts', 24)
    buoyant_force_scalar = params.get('buoyant_force_scalar', 1.0)

    motion_data = []
    time_sec = 0
    latitude = params.get('launch_latitude', 0.0)
    longitude = params.get('launch_longitude', 0.0)
    altitude = alt_chosen
    z_vel = 0.0  # Start with zero vertical velocity
    x_vel = u_wind
    y_vel = v_wind

    delta_t = 30  # 30 seconds time step
    max_altitude = 40000
    max_acceleration = 2.0  # Reduced to a more realistic 2 m/s²
    max_velocity = 10.0  # Reduced to a more realistic 10 m/s

    logging.debug("Starting balloon flight simulation with 30-second time steps.")

    for step in range(number_forecasts):
        for _ in range(20):  # 10 minutes with 30-second steps (20 * 30 = 600 seconds)
            time_sec += delta_t

            # Calculate air density using ideal gas law: rho = p / (R_specific * T)
            p = pressure_hpa * 100  # hPa to Pa
            T = temperature  # K
            rho_air = p / (R_SPECIFIC * T)  # kg/m³

            # Calculate gravity at current altitude
            gravity_altitude = GRAVITY_ACC * (EARTH_RADIUS / (EARTH_RADIUS + altitude))**2

            # Calculate buoyant force: F_buoyant = (rho_air - rho_gas) * volume_gas * g * buoyant_force_scalar
            buoyant_force = (rho_air - rho_gas) * volume_gas * gravity_altitude * buoyant_force_scalar

            # Calculate drag force: F_drag = 0.5 * C_d * rho_air * A * v^2
            if volume_gas <= 0:
                logging.error("Volume of gas is non-positive. Cannot calculate cross-sectional area.")
                drag_force = 0.0
            else:
                radius = ((3 * volume_gas) / (4 * np.pi)) ** (1/3)  # meters
                cross_sectional_area = np.pi * radius ** 2  # m²
                velocity_relative = math.sqrt(u_wind**2 + v_wind**2 + z_vel**2)
                drag_force = 0.5 * drag_coefficient_z * rho_air * cross_sectional_area * (velocity_relative ** 2)

            # Net force and acceleration
            net_force = buoyant_force - drag_force - mass_structure * gravity_altitude
            acceleration_z = net_force / mass_structure  # m/s²

            # Implement acceleration cap
            acceleration_z = max(min(acceleration_z, max_acceleration), -max_acceleration)

            # Update vertical velocity and altitude
            z_vel += acceleration_z * delta_t  # m/s
            z_vel = max(min(z_vel, max_velocity), -max_velocity)  # Cap vertical velocity
            altitude += z_vel * delta_t  # m

            # Calculate Wind Direction and Frequency
            wind_direction = calculate_wind_direction(u_wind, v_wind)
            wind_frequency = calculate_wind_frequency(u_wind, v_wind)

            # Update horizontal velocities based on wind
            x_vel = u_wind  # m/s
            y_vel = v_wind  # m/s

            # Update latitude and longitude based on velocities
            distance_x = x_vel * delta_t  # meters
            distance_y = y_vel * delta_t  # meters

            # Calculate change in latitude and longitude
            delta_lat = (distance_y / EARTH_RADIUS) * (180 / math.pi)
            delta_lon = (distance_x / (EARTH_RADIUS * math.cos(math.radians(latitude)))) * (180 / math.pi)

            # Update latitude and longitude
            latitude += delta_lat
            longitude += delta_lon

            # Handle longitude wrap-around
            if longitude > 180:
                longitude -= 360
            elif longitude < -180:
                longitude += 360

            # Append current state to motion data
            current_state = {
                'Time (s)': time_sec,
                'Latitude': latitude,
                'Longitude': longitude,
                'Altitude (m)': max(altitude, 0.0),  # Prevent negative altitude
                'X_Vel (m/s)': x_vel,
                'Y_Vel (m/s)': y_vel,
                'Z_Vel (m/s)': z_vel,
                'Wind Direction (deg)': wind_direction,
                'Wind Frequency': wind_frequency
            }
            motion_data.append(current_state)
            logging.debug(f"Step {step + 1}, Time {time_sec}s: {current_state}")

            # Termination condition
            if altitude <= 0 or altitude > max_altitude:
                logging.info(f"Simulation terminated at step {step + 1}, Time {time_sec}s due to altitude limits.")
                return pd.DataFrame(motion_data)

    return pd.DataFrame(motion_data)

# Data Downloader Function
def download_gfs_data(date_entry, cycle_runtime, forecast_hour, input_path):
    date_obj = datetime.strptime(date_entry, "%Y%m%d")
    formatted_date = date_obj.strftime("%Y%m%d")
    forecast_hour_str = str(forecast_hour).zfill(3)
    filename = f"gfs.t{cycle_runtime}z.pgrb2.0p25.f{forecast_hour_str}"
    url = f"https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl?file={filename}&lev_10_m_above_ground=on&lev_surface=on&var_TMP=on&var_UGRD=on&var_VGRD=on&leftlon=0&rightlon=360&toplat=90&bottomlat=-90&dir=%2Fgfs.{formatted_date}%2F{cycle_runtime}%2Fatmos"
    
    local_filepath = os.path.join(input_path, filename)
    if not os.path.exists(local_filepath):
        response = requests.get(url)
        if response.status_code == 200:
            with open(local_filepath, 'wb') as file:
                file.write(response.content)
            logging.info(f"Downloaded {filename}")
        else:
            logging.error(f"Failed to download {filename}. Status code: {response.status_code}")
            raise Exception(f"Failed to download {filename}")
    else:
        logging.info(f"{filename} already exists. Skipping download.")
    
    return local_filepath

# Main Simulation Runner Function
def run_simulation(params):
    logging.debug(f"Starting simulation with parameters: {params}")

    input_path = params.get('input_path', 'data/atmospheric_data')
    motion_table_path = params.get('motion_table_path', 'data/output')
    date_entry = params.get('date_entry')
    cycle_runtime = params.get('cycle_runtime')
    forecast_hour = params.get('forecast_hour')

    os.makedirs(input_path, exist_ok=True)
    os.makedirs(motion_table_path, exist_ok=True)

    forecast_hour_str = str(forecast_hour).zfill(3)
    filename = f"gfs.t{cycle_runtime}z.pgrb2.0p25.f{forecast_hour_str}"
    filepath = os.path.join(input_path, filename)

    if not os.path.exists(filepath):
        logging.info(f"Atmospheric data file {filename} not found. Attempting to download...")
        try:
            filepath = download_gfs_data(date_entry, cycle_runtime, forecast_hour, input_path)
            logging.info(f"Downloaded {filepath} successfully.")
        except Exception as e:
            logging.error(f"Failed to download atmospheric data: {e}")
            raise

    latitude = params.get('launch_latitude', 0.0)
    longitude = params.get('launch_longitude', 0.0)

    try:
        temperature = extract_variable_pygrib(filepath, 'surface', 'instant', 't', latitude, longitude, 0)
        pressure = extract_variable_pygrib(filepath, 'surface', 'instant', 'sp', latitude, longitude, 0)
        pressure_hpa = pressure / 100
        u_wind = extract_variable_pygrib(filepath, 'heightAboveGround', 'instant', '10u', latitude, longitude, 10)
        v_wind = extract_variable_pygrib(filepath, 'heightAboveGround', 'instant', '10v', latitude, longitude, 10)
    except Exception as e:
        logging.error(f"Failed to extract required variables: {e}")
        raise

    try:
        n_gas, mass_structure, volume_gas, rho_gas, lift_capacity = calculate_initial_parameters(params)
    except Exception as e:
        logging.error(f"Failed to calculate initial parameters: {e}")
        raise

    try:
        motion_table = simulate_balloon_flight_pygrib(
            temperature, pressure_hpa, u_wind, v_wind,
            mass_structure, n_gas, volume_gas, rho_gas, lift_capacity,
            params
        )
    except Exception as e:
        logging.error(f"Simulation failed: {e}")
        raise

    try:
        output_file = os.path.join(motion_table_path, 'motion_table.csv')
        motion_table.to_csv(output_file, index=False)
        logging.info(f"Saved simulation results to {output_file}")
    except Exception as e:
        logging.error(f"Failed to save simulation results: {e}")
        raise

    return motion_table

# Main entry point
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="High Altitude Balloon (HAB) Simulation")
    parser.add_argument('--date_entry', type=str, required=True, help='Date of the forecast in YYYYMMDD format')
    parser.add_argument('--cycle_runtime', type=str, required=True, help='Cycle runtime (e.g., "06" for 06Z)')
    parser.add_argument('--forecast_hour', type=int, required=True, help='Forecast hour (e.g., 24)')
    parser.add_argument('--gross_mass', type=float, default=14.0, help='Gross mass of the balloon payload (kg)')
    parser.add_argument('--lift_gas_type', type=str, choices=['Helium', 'Hydrogen'], default='Helium', help='Type of lifting gas')
    parser.add_argument('--max_volume_HAB_limit', type=float, default=6.0, help='Maximum volume limit for HAB (m³)')
    parser.add_argument('--percent_lift_gas_scalar', type=float, default=23.0, help='Percentage of lifting gas (e.g., 23 for 23%)')
    parser.add_argument('--buoyant_force_scalar', type=float, default=1.0, help='Buoyant force scalar')
    parser.add_argument('--drag_coefficient_z', type=float, default=0.47, help='Drag coefficient in the Z direction')
    parser.add_argument('--launch_latitude', type=float, required=True, help='Launch site latitude')
    parser.add_argument('--launch_longitude', type=float, required=True, help='Launch site longitude')
    parser.add_argument('--alt_chosen', type=float, default=10.0, help='Chosen initial altitude (m)')
    parser.add_argument('--number_forecasts', type=int, default=24, help='Number of forecast steps to simulate')
    parser.add_argument('--input_path', type=str, default='data/atmospheric_data', help='Path to atmospheric data files')
    parser.add_argument('--motion_table_path', type=str, default='data/output', help='Path to save motion table')

    args = parser.parse_args()

    # Convert arguments to dictionary
    params = vars(args)

    # Configure logging
    log_file = os.path.join(params['motion_table_path'], 'simulation.log')
    configure_logging(log_file)

    # Run simulation
    try:
        motion_table = run_simulation(params)
        logging.info("Simulation completed successfully.")
        
        # Print summary of results
        print("\nSimulation Results Summary:")
        print(f"Total simulation time: {motion_table['Time (s)'].max()} seconds")
        print(f"Maximum altitude reached: {motion_table['Altitude (m)'].max():.2f} meters")
        print(f"Final latitude: {motion_table['Latitude'].iloc[-1]:.6f}")
        print(f"Final longitude: {motion_table['Longitude'].iloc[-1]:.6f}")
        print(f"Results saved to: {os.path.join(params['motion_table_path'], 'motion_table.csv')}")
    except Exception as e:
        logging.error(f"Simulation encountered an error: {e}")
        exit(1)