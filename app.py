# app.py

from flask import Flask, render_template, request, jsonify
from simulation import run_simulation
import logging
import os

app = Flask(__name__)

# Configure Logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@app.route('/', methods=['GET'])
def index():
    # Extract query parameters if any to pre-fill the form
    data = request.args.to_dict()
    return render_template('index.html', data=data)

@app.route('/predict', methods=['POST'])
def predict():
    data = request.form.to_dict()
    logger.debug(f"Received form data: {data}")

    # Validate and process data
    try:
        # Ensure all required fields are present
        required_fields = [
            'date_entry', 'cycle_runtime', 'forecast_hour', 'gross_mass',
            'lift_gas_type', 'max_volume_HAB_limit', 'percent_lift_gas_scalar',  # Updated field name
            'buoyant_force_scalar', 'drag_coefficient_z', 'launch_latitude',
            'launch_longitude', 'alt_chosen', 'number_forecasts',
            'motion_table_path'
        ]

        missing_fields = [field for field in required_fields if field not in data or data.get(field) == '']
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

        # Parse and validate individual fields
        params = {
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
            'alt_chosen': float(data.get('alt_chosen')),
            'number_forecasts': int(data.get('number_forecasts')),
            'motion_table_path': data.get('motion_table_path')
        }

        logger.debug(f"Parsed parameters: {params}")

    except ValueError as ve:
        logger.error(f"Invalid input: {ve}")
        return jsonify({'error': f'Invalid input: {str(ve)}'}), 400
    except Exception as e:
        logger.error(f"Unexpected error during input parsing: {e}")
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

    # Run simulation
    try:
        simulation_results = run_simulation(params)
    except Exception as e:
        logger.error(f"Simulation failed: {e}")
        return jsonify({'error': f'Simulation failed: {str(e)}'}), 500

    # Process results
    try:
        # Convert DataFrame to list of records for JSON response
        trajectory = simulation_results.to_dict(orient='records')
    except Exception as e:
        logger.error(f"Failed to process simulation results: {e}")
        return jsonify({'error': f'Failed to process results: {str(e)}'}), 500

    return jsonify({'prediction': trajectory}), 200

if __name__ == '__main__':
    app.run(debug=True)
