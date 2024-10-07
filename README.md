# High-Altitude Balloon Prediction Simulator

A web-based application for simulating and predicting the flight trajectory of high-altitude balloons (HABs). This simulator integrates atmospheric data from NOAA's Global Forecast System (GFS) to provide accurate predictions of balloon ascent, burst, and descent phases.

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [Application Structure](#application-structure)
- [Simulation Parameters](#simulation-parameters)
- [Mathematical Modeling](#mathematical-modeling)
  - [Balloon Dynamics](#balloon-dynamics)
  - [Forces Acting on the Balloon](#forces-acting-on-the-balloon)
  - [Atmospheric Models](#atmospheric-models)
  - [Numerical Integration](#numerical-integration)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Features

- **Interactive Map Interface**: Select launch coordinates by clicking on a map.
- **Customizable Balloon Parameters**: Adjust variables such as gross mass, lift gas type, ascent/descent rates, and more.
- **Real-Time Atmospheric Data**: Downloads and processes GRIB2 files from NOAA's NOMADS server.
- **Visualization**: Generates plots of altitude over time, ground track, and velocity profiles.
- **Data Export**: Provides downloadable CSV files and trajectory plots.
- **Web-Based Interface**: Built with Flask, Bootstrap, and Leaflet for an intuitive user experience.

## Prerequisites

- **Python 3.7 or higher**
- **Anaconda or Virtual Environment** (recommended)
- **Web Browser**: For accessing the web interface.

### Required Python Packages

- Flask
- NumPy
- Pandas
- Matplotlib
- pygrib
- Requests
- Jinja2
- Werkzeug

## Installation

1. **Clone the Repository**

   ```bash
   git clone https://github.com/jaw1999/hab-simulator.git
   cd hab-simulator

2. Set up a virtual environment 
   
   python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

4. Install Dependencies

   pip install -r requirements.txt

# Mathematical Modeling

## Balloon Dynamics

The balloon's motion is governed by Newton's second law:

F_total = m * a

Where:
- `F_total` is the total force acting on the balloon.
- `m` is the mass of the balloon system (payload + balloon envelope + lift gas).
- `a` is the acceleration vector of the balloon.

## Forces Acting on the Balloon

The total force is the sum of the buoyant force, gravitational force (weight), and aerodynamic drag force:

F_total = F_buoyancy + F_drag + F_gravity

### Buoyant Force (`F_buoyancy`)

Buoyant force arises due to the displacement of air by the balloon:

F_buoyancy = rho_air * V_balloon * g


Where:
- `rho_air` is the air density at the balloon's altitude.
- `V_balloon` is the volume of the balloon.
- `g` is the acceleration due to gravity (9.80665 m/s²).

### Gravitational Force (`F_gravity`)

The gravitational force pulls the balloon downward:

F_gravity = - m_total * g


Where:
- `m_total` is the total mass of the balloon system.

### Aerodynamic Drag Force (`F_drag`)

The drag force opposes the balloon's motion through the air:

F_drag = - (1/2) * C_d * rho_air * A_cross * v_rel^2 * (v_rel_unit_vector)


Where:
- `C_d` is the drag coefficient.
- `A_cross` is the cross-sectional area of the balloon.
- `v_rel` is the relative velocity between the balloon and the air.
- `v_rel_unit_vector` is the unit vector in the direction of `v_rel`.

## Balloon Volume Changes

As the balloon ascends, the external pressure decreases, causing the balloon to expand. Assuming the lift gas behaves as an ideal gas, the volume can be calculated using the Ideal Gas Law:

V = (n * R * T) / P


Where:
- `n` is the number of moles of lift gas (constant if no gas leaks).
- `R` is the universal gas constant (8.3144621 J/(mol·K)).
- `T` is the absolute temperature in Kelvin.
- `P` is the atmospheric pressure at the current altitude.

## Atmospheric Models

### Temperature and Pressure Profiles

We use the U.S. Standard Atmosphere model to estimate atmospheric conditions.

**Troposphere (0 ≤ h < 11,000 m):**

Temperature:

T = T0 - L * h


Pressure:

P = P0 * (T / T0)^(g / (L * R_air))


Where:
- `T0` = 288.15 K (Standard temperature at sea level)
- `L` = 0.0065 K/m (Temperature lapse rate)
- `P0` = 101325 Pa (Standard pressure at sea level)
- `g` = 9.80665 m/s² (Acceleration due to gravity)
- `R_air` = 287.05 J/(kg·K) (Specific gas constant for dry air)
- `h` is the altitude in meters.

### Air Density (`rho_air`)

Air density is calculated using the Ideal Gas Law:

rho_air = P / (R_air * T)


## Numerical Integration

The simulation uses the fourth-order Runge-Kutta (RK4) method to integrate the equations of motion over time.

### RK4 Algorithm

Given the differential equation:

dy/dt = f(y, t)


The RK4 method computes the next state `y_{n+1}` as:

k1 = f(y_n, t_n) k2 = f(y_n + (dt/2) * k1, t_n + dt/2) k3 = f(y_n + (dt/2) * k2, t_n + dt/2) k4 = f(y_n + dt * k3, t_n + dt) y_{n+1} = y_n + (dt / 6) * (k1 + 2k2 + 2k3 + k4)


Where:
- `dt` is the time step.
- `k1`, `k2`, `k3`, `k4` are intermediate slopes.

## Coordinate Transformations

### From Latitude, Longitude, Altitude to Cartesian Coordinates

phi = latitude in radians lambda = longitude in radians r = R_earth + h x = r * cos(phi) * cos(lambda) y = r * cos(phi) * sin(lambda) z = r * sin(phi)


Where:
- `R_earth` = 6,371,009 m (Mean Earth radius)
- `h` is the altitude above sea level in meters.

### From Cartesian Coordinates to Latitude, Longitude, Altitude

r = sqrt(x^2 + y^2 + z^2) phi = arcsin(z / r) lambda = arctangent(y / x) h = r - R_earth


## Burst Condition

The balloon is considered to burst when its volume reaches the maximum allowable volume:

V_balloon >= V_max


Upon burst:

- The lift gas escapes, so the buoyant force is eliminated.
- The balloon transitions to descent, deploying the parachute.
- The drag coefficient and cross-sectional area are updated to reflect the parachute's properties.

## Parachute Descent

The descent rate after parachute deployment is controlled by adjusting the drag force to achieve the desired terminal velocity.

Terminal velocity (`v_terminal`) is calculated as:

v_terminal = sqrt((2 * m_total * g) / (C_d_parachute * rho_air * A_parachute))


Where:

- `C_d_parachute` is the drag coefficient of the parachute.
- `A_parachute` is the effective area of the parachute.
- `m_total` is the mass of the payload and parachute.
- `rho_air` is the air density at the descent altitude.
- `g` is the acceleration due to gravity (9.80665 m/s²).
