# simulation.py

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import pygrib
import logging

# Constants
RADIUS_EARTH = 6371009.0  # m
GRAVITY_ACC = 9.80665  # m/s^2
PRESSURE_AT_LAUNCH = 101325  # Pa

# Configure logging
logger = logging.getLogger('simulation')
logger.setLevel(logging.DEBUG)

# Add console handler if not present
if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

def execute_simulation(params):
    """Execute the complete simulation process with the given parameters."""
    logger.info("Starting simulation...")

    # Extract NOAA data using pygrib
    noaa_data = extract_noaa_data(params)

    # Run the balloon simulation with the provided parameters
    results = run_simulation(params, noaa_data)

    # Generate the plot
    fig = plot_results(results)

    logger.info("Simulation completed successfully.")

    return results, fig

def extract_noaa_data(params):
    """Extract NOAA GFS data from GRIB2 file using pygrib."""
    date_entry = params['date_entry']
    cycle_runtime = params['cycle_runtime']
    forecast_hour = params['forecast_hour']
    input_path = params['input_path']

    # The filename should match the GFS forecast files
    filename = f"gfs.t{cycle_runtime}z.pgrb2.0p25.f{forecast_hour:03d}"
    filepath = os.path.join(input_path, filename)

    logger.info(f"Extracting NOAA data from {filepath}...")

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"GRIB file not found: {filepath}")

    try:
        grbs = pygrib.open(filepath)
        data = {
            'tmp': None,
            'ugrd': None,
            'vgrd': None,
            'vvel': None,  # Vertical velocity
            'hgt': None,   # Geopotential Height
        }

        for grb in grbs:
            if grb.name == 'Temperature':
                data['tmp'] = grb.values
                data['lat'], data['lon'] = grb.latlons()
            elif grb.name == 'U component of wind':
                data['ugrd'] = grb.values
            elif grb.name == 'V component of wind':
                data['vgrd'] = grb.values
            elif grb.name == 'Vertical velocity':
                data['vvel'] = grb.values
            elif grb.name == 'Geopotential Height':
                data['hgt'] = grb.values

        grbs.close()

        # Debug logging
        for key, value in data.items():
            if isinstance(value, np.ndarray):
                logger.debug(f"{key} shape: {value.shape}")

    except Exception as e:
        logger.error(f"Error extracting data from GRIB file: {e}")
        raise

    logger.info('NOAA data extraction complete.')

    return data

def run_simulation(params, noaa_data):
    """Run the full balloon simulation with the provided parameters."""
    # Initialize balloon properties
    balloon_props = calculate_initial_balloon_properties(
        gross_mass=params['gross_mass'],
        percent_lift_gas_scalar=params['percent_lift_gas_scalar'],
        lift_gas_type=params['lift_gas_type'],
        max_volume=params['max_volume_HAB_limit']
    )

    # Set initial conditions
    initial_position = lat_lon_to_xyz(params['launch_latitude'], params['launch_longitude'], params['launch_altitude'])
    initial_velocity = np.array([0, 0, params['ascent_rate']])  # Set initial vertical velocity
    initial_state = np.concatenate([initial_position, initial_velocity])

    # Run simulation
    time, state_history = simulate_balloon_flight(
        initial_state,
        balloon_props,
        noaa_data,
        dt=1,
        total_time=params['simulation_duration'],
        params=params
    )

    # Process results
    results = pd.DataFrame({
        'Time': time,
        'X': state_history[:, 0],
        'Y': state_history[:, 1],
        'Z': state_history[:, 2],
        'Vx': state_history[:, 3],
        'Vy': state_history[:, 4],
        'Vz': state_history[:, 5]
    })

    # Convert XYZ to lat/lon/altitude
    lat_lon_alt = np.array([xyz_to_lat_lon(state_history[i, :3]) for i in range(len(time))])
    results['Latitude'] = lat_lon_alt[:, 0]
    results['Longitude'] = lat_lon_alt[:, 1]
    results['Altitude'] = lat_lon_alt[:, 2]

    return results

def calculate_initial_balloon_properties(gross_mass, percent_lift_gas_scalar, lift_gas_type, max_volume):
    """Calculate initial balloon properties with volume limits."""
    if lift_gas_type.lower() in ['helium', 'he']:
        molar_mass_gas = 4.0026e-3  # kg/mol for Helium
    elif lift_gas_type.lower() in ['hydrogen', 'h']:
        molar_mass_gas = 2.01588e-3  # kg/mol for Hydrogen
    else:
        raise ValueError("Invalid lift gas type. Choose 'Helium' or 'Hydrogen'.")

    # Calculate the required lift (buoyant force) to overcome gross mass
    total_mass = gross_mass
    total_weight = total_mass * GRAVITY_ACC

    # Estimate required volume using buoyancy equation: F_buoyancy = rho_air * V * g
    # Assume standard air density at sea level (~1.225 kg/m^3)
    rho_air = 1.225  # kg/m^3
    required_volume = total_weight / (rho_air * GRAVITY_ACC)

    # Apply percent lift gas scalar
    required_volume *= (1 + percent_lift_gas_scalar / 100)

    # Ensure the volume does not exceed max_volume_HAB_limit
    initial_volume = min(required_volume, max_volume)

    # Calculate the number of moles of lift gas needed
    T_launch = 273.15 + 15  # Assume 15°C at launch
    P_launch = PRESSURE_AT_LAUNCH  # Pa
    R = 8.3144621  # J/(mol·K)
    n_gas = (P_launch * initial_volume) / (R * T_launch)

    # Mass of the lift gas
    mass_lift_gas = n_gas * molar_mass_gas  # kg

    # Update total mass to include lift gas
    mass_structure = gross_mass + mass_lift_gas

    # Calculate radius and cross-sectional area
    radius = ((3 * initial_volume) / (4 * np.pi))**(1/3)
    cross_sectional_area = np.pi * radius**2

    return {
        'mass_structure': mass_structure,
        'mass_lift_gas': mass_lift_gas,
        'volume': initial_volume,
        'radius': radius,
        'cross_sectional_area': cross_sectional_area,
        'n_gas': n_gas,
        'lift_gas_type': lift_gas_type,
        'max_volume_HAB_limit': max_volume
    }

def lat_lon_to_xyz(lat, lon, altitude):
    """Convert latitude, longitude, and altitude to XYZ coordinates."""
    lat_rad = np.radians(lat)
    lon_rad = np.radians(lon)
    r = RADIUS_EARTH + altitude
    x = r * np.cos(lat_rad) * np.cos(lon_rad)
    y = r * np.cos(lat_rad) * np.sin(lon_rad)
    z = r * np.sin(lat_rad)
    return np.array([x, y, z])

def xyz_to_lat_lon(position):
    """Convert XYZ coordinates to latitude, longitude, and altitude."""
    x, y, z = position
    r = np.linalg.norm(position)
    lat_rad = np.arcsin(z / r)
    lon_rad = np.arctan2(y, x)
    lat = np.degrees(lat_rad)
    lon = np.degrees(lon_rad)
    altitude = r - RADIUS_EARTH
    return lat, lon, altitude

def simulate_balloon_flight(initial_state, balloon_props, noaa_data, dt, total_time, params):
    """Simulate the balloon flight using RK4 integration."""
    num_steps = int(total_time / dt) + 1
    time_array = np.linspace(0, total_time, num_steps)
    state_history = np.zeros((num_steps, 6))
    state_history[0] = initial_state

    drag_coefficient = params['drag_coefficient_z']
    parachute_drag_coefficient = params['parachute_drag_coefficient']
    parachute_area = params['parachute_area']
    descent_rate_parachute = params['descent_rate_parachute']

    ascent = True

    for i in range(1, num_steps):
        t = time_array[i-1]
        current_state = state_history[i-1]

        # Compute next state using RK4
        new_state = rk4_step(
            current_state,
            lambda y, t: balloon_dynamics(y, t, balloon_props, noaa_data, drag_coefficient, ascent),
            dt,
            t
        )

        # Update state history
        state_history[i] = new_state

        # Check for balloon burst
        if ascent and balloon_props['volume'] >= balloon_props['max_volume_HAB_limit']:
            # Balloon bursts
            ascent = False
            logger.info(f"Balloon burst at time {t:.2f}s")

            # Adjust balloon properties for descent
            balloon_props['mass_lift_gas'] = 0  # Gas escapes
            drag_coefficient = parachute_drag_coefficient
            balloon_props['cross_sectional_area'] = parachute_area

            # Adjust vertical velocity to descent rate
            state_history[i, 5] = -descent_rate_parachute

        # Check for landing
        lat, lon, altitude = xyz_to_lat_lon(state_history[i, :3])
        if altitude <= 0:
            state_history[i, 2] = RADIUS_EARTH  # Ensure altitude is not negative
            state_history[i, 3:] = 0  # Stop movement upon landing
            logger.info(f"Balloon landed at time {t:.2f}s")
            time_array = time_array[:i+1]
            state_history = state_history[:i+1]
            break

    return time_array, state_history

def rk4_step(y, dydt_func, dt, t):
    """Perform a single RK4 integration step."""
    k1 = dydt_func(y, t)
    k2 = dydt_func(y + 0.5 * dt * k1, t + 0.5 * dt)
    k3 = dydt_func(y + 0.5 * dt * k2, t + 0.5 * dt)
    k4 = dydt_func(y + dt * k3, t + dt)
    return y + (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)

def balloon_dynamics(state, t, balloon_props, noaa_data, drag_coefficient, ascent):
    """Define the balloon dynamics for integration."""
    position, velocity = state[:3], state[3:]

    lat, lon, altitude = xyz_to_lat_lon(position)
    altitude_above_ground = max(altitude, 0)

    atmos_data = interpolate_atmospheric_data(altitude_above_ground, noaa_data, lat, lon)

    if ascent:
        # Update balloon volume using the ideal gas law
        R = 8.3144621  # J/(mol·K)
        n_gas = balloon_props['n_gas']  # Number of moles of gas (constant)
        T = atmos_data['temperature']  # Temperature in Kelvin
        P = atmos_data['pressure']  # Pressure in Pa
        volume = (n_gas * R * T) / P  # Volume in m^3
        balloon_props['volume'] = min(volume, balloon_props['max_volume_HAB_limit'])

        # Update radius and cross-sectional area
        radius = ((3 * balloon_props['volume']) / (4 * np.pi))**(1/3)
        balloon_props['radius'] = radius
        balloon_props['cross_sectional_area'] = np.pi * radius**2
    else:
        # For descent, volume remains constant or can be adjusted if desired
        pass

    # Calculate forces
    buoyancy_force_vector, drag_force_vector, weight_force_vector = calculate_forces(
        balloon_props, atmos_data, velocity, drag_coefficient
    )

    total_force = buoyancy_force_vector + drag_force_vector + weight_force_vector
    total_mass = balloon_props['mass_structure'] + balloon_props['mass_lift_gas']
    acceleration = total_force / total_mass

    return np.concatenate([velocity, acceleration])

def calculate_forces(balloon_props, atmos_data, velocity, drag_coefficient):
    """Calculate forces acting on the balloon."""
    volume = balloon_props['volume']
    cross_sectional_area = balloon_props['cross_sectional_area']

    # Buoyancy force vector (upward)
    buoyancy_force_magnitude = volume * atmos_data['density'] * GRAVITY_ACC
    buoyancy_force_vector = np.array([0, 0, buoyancy_force_magnitude])

    # Drag force vector
    velocity_rel = velocity - atmos_data['wind']
    velocity_magnitude = np.linalg.norm(velocity_rel)
    if velocity_magnitude > 0:
        drag_force_magnitude = 0.5 * atmos_data['density'] * velocity_magnitude**2 * cross_sectional_area * drag_coefficient
        drag_force_vector = -drag_force_magnitude * (velocity_rel / velocity_magnitude)
    else:
        drag_force_vector = np.zeros(3)

    # Weight force vector (downward)
    total_mass = balloon_props['mass_structure'] + balloon_props['mass_lift_gas']
    weight_force_vector = np.array([0, 0, -total_mass * GRAVITY_ACC])

    return buoyancy_force_vector, drag_force_vector, weight_force_vector

def interpolate_atmospheric_data(altitude, noaa_data, lat, lon):
    """Interpolate atmospheric data for a given altitude."""
    # Use the US Standard Atmosphere model for simplicity

    # Temperature and pressure
    if altitude < 11000:  # Troposphere
        temperature = 15.04 - 0.00649 * altitude
        pressure = 101.29 * ((temperature + 273.15) / 288.08)**5.256
    elif altitude < 25000:  # Lower Stratosphere
        temperature = -56.46
        pressure = 22.65 * np.exp(1.73 - 0.000157 * altitude)
    else:  # Upper Stratosphere
        temperature = -131.21 + 0.00299 * altitude
        pressure = 2.488 * ((temperature + 273.15) / 216.6)**-11.388

    pressure *= 1000  # Convert kPa to Pa

    # Air density
    air_density = pressure / (287.05 * (temperature + 273.15))  # kg/m^3

    # Wind (set to zero or extract from noaa_data if available)
    wind = np.zeros(3)

    return {
        'pressure': pressure,
        'temperature': temperature + 273.15,  # Convert to Kelvin
        'density': air_density,
        'wind': wind
    }

def plot_results(results):
    """Plot simulation results and return the figure."""
    fig, axs = plt.subplots(2, 2, figsize=(12, 10))
    fig.suptitle('High-Altitude Balloon Simulation Results')

    axs[0, 0].plot(results['Time'], results['Altitude'])
    axs[0, 0].set_xlabel('Time (s)')
    axs[0, 0].set_ylabel('Altitude (m)')
    axs[0, 0].set_title('Altitude vs Time')

    axs[0, 1].plot(results['Longitude'], results['Latitude'])
    axs[0, 1].set_xlabel('Longitude')
    axs[0, 1].set_ylabel('Latitude')
    axs[0, 1].set_title('Ground Track')

    axs[1, 0].plot(results['Time'], results['Vz'])
    axs[1, 0].set_xlabel('Time (s)')
    axs[1, 0].set_ylabel('Vertical Velocity (m/s)')
    axs[1, 0].set_title('Vertical Velocity vs Time')

    axs[1, 1].plot(results['Time'], np.sqrt(results['Vx']**2 + results['Vy']**2))
    axs[1, 1].set_xlabel('Time (s)')
    axs[1, 1].set_ylabel('Horizontal Velocity (m/s)')
    axs[1, 1].set_title('Horizontal Velocity vs Time')

    plt.tight_layout()
    return fig

if __name__ == "__main__":
    # Example parameters for testing
    params = {
        'input_path': os.path.abspath('data/atmospheric_data'),
        'output_path': os.path.abspath('data/output'),
        'date_entry': '20241001',
        'cycle_runtime': '12',
        'forecast_hour': 24,
        'gross_mass': 3.0,
        'lift_gas_type': 'Helium',
        'max_volume_HAB_limit': 2.0,
        'percent_lift_gas_scalar': 15.0,
        'buoyant_force_scalar': 1.0,
        'drag_coefficient_z': 0.47,
        'launch_latitude': 32.0,
        'launch_longitude': 42.0,
        'launch_altitude': 1.0,
        'simulation_duration': 43200,
        'parachute_drag_coefficient': 1.0,
        'parachute_area': 1.0,
        'ascent_rate': 5.0,
        'descent_rate_parachute': 5.0,
        'number_forecasts': 12,
    }
    execute_simulation(params)
