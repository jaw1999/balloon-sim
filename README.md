# High Altitude Balloon (HAB) Simulation

## Table of Contents
1. [Project Overview](#project-overview)
2. [Installation](#installation)
3. [Usage](#usage)
4. [Mathematical Models](#mathematical-models)
5. [Input Parameters](#input-parameters)
6. [Output](#output)
7. [File Structure](#file-structure)
8. [Limitations and Future Improvements](#limitations-and-future-improvements)
9. [Contributing](#contributing)
10. [License](#license)

## Project Overview

This High Altitude Balloon (HAB) Simulation project is designed to model the flight path and behavior of a high-altitude balloon based on various input parameters and atmospheric conditions. The simulation takes into account factors such as wind speed, air density, temperature, and balloon characteristics to predict the balloon's trajectory, altitude, and velocity over time.

The primary goals of this simulation are:
1. To predict the flight path of a high-altitude balloon
2. To estimate maximum altitude and flight duration
3. To assist in planning HAB launches by providing insight into expected balloon behavior

## Installation

### Prerequisites
- Python 3.7 or higher
- pip (Python package installer)

### Steps
1. Clone the repository:
   ```
   git clone https://github.com/yourusername/hab-simulation.git
   cd hab-simulation
   ```

2. Install required packages:
   ```
   pip install -r requirements.txt
   ```

   The `requirements.txt` file should include:
   ```
   numpy
   pandas
   pygrib
   requests
   ```

## Usage

Run the simulation using the command line interface:

```
python simulation.py --date_entry YYYYMMDD --cycle_runtime HH --forecast_hour NN --launch_latitude XX.XXXX --launch_longitude YY.YYYY [additional options]
```

Example:
```
python simulation.py --date_entry 20241001 --cycle_runtime 00 --forecast_hour 24 --launch_latitude 40.7128 --launch_longitude -74.0060 --gross_mass 14.0 --lift_gas_type Helium --max_volume_HAB_limit 6.0 --percent_lift_gas_scalar 23.0 --buoyant_force_scalar 1.0 --drag_coefficient_z 0.47 --alt_chosen 10.0 --number_forecasts 24
```

## Mathematical Models

The simulation uses several mathematical models to calculate the balloon's behavior:

### 1. Air Density Calculation
Air density is calculated using the ideal gas law:
```
ρ = P / (R_specific * T)
```
Where:
- ρ is air density (kg/m³)
- P is pressure (Pa)
- R_specific is the specific gas constant for dry air (287.058 J/(kg·K))
- T is temperature (K)

### 2. Buoyant Force
The buoyant force is calculated using Archimedes' principle:
```
F_buoyant = (ρ_air - ρ_gas) * V_gas * g * buoyant_force_scalar
```
Where:
- ρ_air is air density
- ρ_gas is lifting gas density
- V_gas is the volume of the lifting gas
- g is the acceleration due to gravity
- buoyant_force_scalar is an adjustment factor

### 3. Drag Force
Drag force is calculated using the drag equation:
```
F_drag = 0.5 * C_d * ρ_air * A * v²
```
Where:
- C_d is the drag coefficient
- A is the cross-sectional area of the balloon
- v is the relative velocity of the balloon to the air

### 4. Vertical Acceleration
The net vertical acceleration is calculated by:
```
a = (F_buoyant - F_drag - m * g) / m
```
Where:
- m is the total mass of the balloon system

### 5. Position Update
The balloon's position is updated using simple kinematics equations:
```
Δx = v_x * Δt
Δy = v_y * Δt
Δz = v_z * Δt + 0.5 * a * Δt²
```

### 6. Wind Effect
The horizontal velocity components of the balloon are assumed to match the wind velocity at the current altitude.

### 7. Latitude and Longitude Update
Changes in latitude and longitude are calculated considering the Earth's curvature:
```
Δlat = (Δy / R_earth) * (180 / π)
Δlon = (Δx / (R_earth * cos(lat))) * (180 / π)
```
Where R_earth is the Earth's radius.

## Input Parameters

- `date_entry`: Date of the forecast (YYYYMMDD)
- `cycle_runtime`: Cycle runtime (HH, e.g., "00", "06", "12", "18")
- `forecast_hour`: Forecast hour
- `gross_mass`: Total mass of the balloon system (kg)
- `lift_gas_type`: Type of lifting gas ("Helium" or "Hydrogen")
- `max_volume_HAB_limit`: Maximum volume limit for the balloon (m³)
- `percent_lift_gas_scalar`: Percentage of lifting gas
- `buoyant_force_scalar`: Scalar for buoyant force calculation
- `drag_coefficient_z`: Drag coefficient in the vertical direction
- `launch_latitude`: Latitude of the launch site
- `launch_longitude`: Longitude of the launch site
- `alt_chosen`: Initial altitude (m)
- `number_forecasts`: Number of forecast steps to simulate

## Output

The simulation outputs a CSV file containing the balloon's state at each time step, including:

- Time (s)
- Latitude
- Longitude
- Altitude (m)
- X Velocity (m/s)
- Y Velocity (m/s)
- Z Velocity (m/s)
- Wind Direction (degrees)
- Wind Frequency

## File Structure

```
hab-simulation/
├── simulation.py
├── requirements.txt
├── README.md
├── data/
│   ├── atmospheric_data/
│   └── output/
└── logs/
```

## Limitations and Future Improvements

- The simulation assumes a constant drag coefficient, which may not be accurate for all flight regimes.
- Wind data is currently only used from the launch altitude. Future versions could interpolate wind data for different altitudes.
- The effects of solar radiation and temperature changes on the balloon volume are not modeled.
- The simulation does not account for the curvature of the Earth in its entirety, which may lead to inaccuracies for very long flights.

