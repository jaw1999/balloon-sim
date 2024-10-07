# app.py

from flask import Flask, render_template, request, jsonify, send_from_directory, url_for
from data_downloader import ensure_grib_file_exists
from simulation import execute_simulation
import logging
import os
from logging.handlers import RotatingFileHandler
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg

app = Flask(__name__)

# Configure logging
logger = logging.getLogger('app')
logger.setLevel(logging.DEBUG)

# Create logs directory if it doesn't exist
logs_dir = 'logs'
os.makedirs(logs_dir, exist_ok=True)

# Create RotatingFileHandler for log file
file_handler = RotatingFileHandler(
    os.path.join(logs_dir, "app.log"),
    maxBytes=5 * 1024 * 1024,  # 5 MB
    backupCount=5
)
file_handler.setLevel(logging.DEBUG)

# Create StreamHandler for console output
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Define log format
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add handlers to logger
if not logger.handlers:
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

@app.route('/', methods=['GET'])
def index():
    """Renders the main page with the simulation form."""
    data = request.args.to_dict()
    logger.debug(f"Rendering index page with data: {data}")
    return render_template('index.html', data=data)

@app.route('/predict', methods=['POST'])
def predict():
    """Handles the simulation request."""
    data = request.form.to_dict()
    logger.debug(f"Received form data: {data}")

    try:
        # Define required fields
        required_fields = [
            'date_entry', 'cycle_runtime', 'forecast_hour', 'gross_mass',
            'lift_gas_type', 'max_volume_HAB_limit', 'percent_lift_gas_scalar',
            'buoyant_force_scalar', 'drag_coefficient_z', 'launch_latitude',
            'launch_longitude', 'alt_chosen', 'number_forecasts',
            'parachute_drag_coefficient', 'parachute_area',
            'ascent_rate', 'descent_rate_parachute'
        ]

        # Check for missing fields
        missing_fields = [field for field in required_fields if field not in data or data.get(field).strip() == '']
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

        # Parse and validate individual fields
        params = {
            'input_path': os.path.abspath('data/atmospheric_data'),
            'output_path': os.path.abspath('data/output'),
            'date_entry': data.get('date_entry'),
            'cycle_runtime': data.get('cycle_runtime'),
            'forecast_hour': int(data.get('forecast_hour')),
            'gross_mass': float(data.get('gross_mass')),
            'lift_gas_type': data.get('lift_gas_type'),
            'max_volume_HAB_limit': float(data.get('max_volume_HAB_limit')),
            'percent_lift_gas_scalar': float(data.get('percent_lift_gas_scalar')),
            'buoyant_force_scalar': float(data.get('buoyant_force_scalar')),
            'drag_coefficient_z': float(data.get('drag_coefficient_z')),
            'launch_latitude': float(data.get('launch_latitude')),
            'launch_longitude': float(data.get('launch_longitude')),
            'launch_altitude': float(data.get('alt_chosen')),
            'simulation_duration': 3600 * int(data.get('number_forecasts')),
            'parachute_drag_coefficient': float(data.get('parachute_drag_coefficient')),
            'parachute_area': float(data.get('parachute_area')),
            'ascent_rate': float(data.get('ascent_rate')),
            'descent_rate_parachute': float(data.get('descent_rate_parachute')),
            'number_forecasts': int(data.get('number_forecasts')),
        }

        logger.debug(f"Parsed parameters: {params}")

        # Ensure GRIB file exists
        grib_path = ensure_grib_file_exists(
            date_entry=params['date_entry'],
            cycle_runtime=params['cycle_runtime'],
            forecast_hour=params['forecast_hour'],
            atmospheric_data_dir=params['input_path']
        )
        if not grib_path:
            raise FileNotFoundError("Required GRIB file could not be found or downloaded.")
        logger.debug(f"GRIB file ensured at path: {grib_path}")

        # Run simulation
        results, fig = execute_simulation(params)
        logger.debug("Simulation run successfully.")

        # Save the figure
        output_plot = os.path.join(params['output_path'], 'flight_trajectory.png')
        canvas = FigureCanvasAgg(fig)
        canvas.print_figure(output_plot)
        plt.close(fig)
        logger.info(f"Saved flight trajectory plot to {output_plot}")

        # Save motion table CSV
        output_csv = os.path.join(params['output_path'], 'motion_table.csv')
        results.to_csv(output_csv, index=False)
        logger.info(f"Saved motion table CSV to {output_csv}")

        # Prepare the response
        trajectory = results.to_dict(orient='records')
        logger.debug(f"Trajectory data prepared for response. Number of points: {len(trajectory)}")

        response = {
            'prediction': trajectory,
            'pop_altitude': results['Altitude'].max(),
            'pop_time': results['Time'][results['Altitude'].idxmax()],
            'landing_time': results['Time'].iloc[-1],
            'summary': {
                'total_simulation_time': results['Time'].max(),
                'max_altitude': results['Altitude'].max(),
                'final_latitude': results['Latitude'].iloc[-1],
                'final_longitude': results['Longitude'].iloc[-1]
            },
            'output_files': {
                'motion_table_csv': url_for('download_file', filename='motion_table.csv'),
                'flight_trajectory_plot': url_for('download_file', filename='flight_trajectory.png')
            }
        }

        logger.debug(f"Response prepared: {response}")
        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Error during simulation: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    """Serves files from the data/output directory."""
    output_dir = os.path.join('data', 'output')
    logger.debug(f"Serving file: {filename} from directory: {output_dir}")
    try:
        return send_from_directory(directory=output_dir, filename=filename, as_attachment=True)
    except FileNotFoundError:
        logger.error(f"File not found: {filename}")
        return jsonify({'error': f'File not found: {filename}'}), 404

if __name__ == '__main__':
    app.run(debug=True)
