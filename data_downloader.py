# data_downloader.py

import os
import requests
import logging
from logging.handlers import RotatingFileHandler
import pygrib  # Ensure pygrib is installed: pip install pygrib
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Constants for required GRIB2 variables
REQUIRED_GRIB_VARIABLES = ['Temperature', 'Geopotential height', 'Relative humidity',
                           'Specific humidity', 'U component of wind', 'V component of wind']

# ----------------------------
# 1. Configuration and Setup
# ----------------------------

# Configure logging
logger = logging.getLogger('data_downloader')
logger.setLevel(logging.DEBUG)

# Create logs directory if it doesn't exist
logs_dir = 'logs'
os.makedirs(logs_dir, exist_ok=True)

# Create RotatingFileHandler for log file
file_handler = RotatingFileHandler(
    os.path.join(logs_dir, "data_downloader.log"),
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


def list_grib_variables(file_path):
    """
    Lists all variables present in the GRIB2 file for debugging purposes.

    Parameters:
        file_path (str): Path to the GRIB2 file.
    """
    try:
        grbs = pygrib.open(file_path)
        variables = sorted(set(grb.name for grb in grbs))
        grbs.close()
        logger.debug(f"Variables in '{file_path}': {variables}")
    except Exception as e:
        logger.error(f"Failed to list variables in GRIB2 file '{file_path}': {e}")


def validate_grib_file(file_path, required_variables=REQUIRED_GRIB_VARIABLES):
    """
    Validates that the downloaded GRIB2 file contains all required variables.

    Parameters:
        file_path (str): Path to the GRIB2 file.
        required_variables (list): List of variable names required for the simulation.

    Returns:
        bool: True if all required variables are present, False otherwise.
    """
    try:
        logger.debug(f"Validating GRIB2 file: {file_path}")
        grbs = pygrib.open(file_path)
        variables_in_file = set(grb.name for grb in grbs)
        grbs.close()

        missing_vars = [var for var in required_variables if var not in variables_in_file]
        if missing_vars:
            logger.warning(f"Missing variables in GRIB2 file '{file_path}': {missing_vars}")
            list_grib_variables(file_path)  # Log all available variables for debugging
            return False
        else:
            logger.info(f"All required variables are present in '{file_path}'.")
            return True
    except Exception as e:
        logger.error(f"Failed to validate GRIB2 file '{file_path}': {e}")
        return False


def download_gfs_data(date_entry, cycle_runtime, forecast_hour, save_path):
    """
    Downloads the specified GRIB2 file from NOAA's NOMADS server with enhanced error handling,
    retry mechanisms, and validation of the downloaded data.

    Parameters:
        date_entry (str): Date in 'YYYYMMDD' format.
        cycle_runtime (str): Cycle runtime in 'HH' format (e.g., '00', '06', '12', '18').
        forecast_hour (int): Forecast hour (e.g., 24, 48).
        save_path (str): Directory path where the GRIB2 file will be saved.

    Returns:
        str: Path to the downloaded GRIB2 file.

    Raises:
        Exception: If the download fails or the file does not contain required variables.
    """
    forecast_hour_str = str(forecast_hour).zfill(3)
    filename = f"gfs.t{cycle_runtime}z.pgrb2.0p25.f{forecast_hour_str}"  # Removed '.grib2' extension
    url = f"https://nomads.ncep.noaa.gov/pub/data/nccf/com/gfs/prod/gfs.{date_entry}/{cycle_runtime}/atmos/pgrb2/0p25/{filename}"
    file_path = os.path.abspath(os.path.join(save_path, filename))  # Removed '.grib2'

    logger.debug(f"Constructed URL: {url}")
    logger.debug(f"File will be saved to: {file_path}")

    # Setup retry strategy
    retry_strategy = Retry(
        total=5,  # Total number of retries
        status_forcelist=[429, 500, 502, 503, 504],  # Retry on these HTTP status codes
        allowed_methods=["GET"],  # Retry for GET requests
        backoff_factor=1  # Wait time between retries: {backoff factor} * (2 ** (retry number))
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    logger.debug("Initialized HTTP session with retry strategy.")

    try:
        logger.info(f"Starting download of {filename} from {url}")
        response = session.get(url, stream=True, timeout=60)  # 60 seconds timeout

        if response.status_code == 200:
            os.makedirs(save_path, exist_ok=True)
            logger.debug(f"Created directory: {save_path}")

            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            logger.info(f"Downloaded {filename} successfully.")

            # Validate the downloaded GRIB2 file
            if validate_grib_file(file_path):
                return file_path
            else:
                # Remove invalid file to prevent using incomplete data
                os.remove(file_path)
                raise Exception(f"Downloaded GRIB2 file '{filename}' is missing required variables.")
        else:
            raise Exception(f"Failed to download {filename}. HTTP Status Code: {response.status_code}")
    except requests.exceptions.RequestException as req_err:
        logger.error(f"Request exception occurred while downloading {filename}: {req_err}")
        raise
    except Exception as e:
        logger.error(f"An error occurred while downloading {filename}: {e}")
        raise
    finally:
        session.close()
        logger.debug("HTTP session closed.")


def ensure_grib_file_exists(date_entry, cycle_runtime, forecast_hour, atmospheric_data_dir='data/atmospheric_data'):
    """
    Ensures that the required GRIB2 file exists. If not, attempts to download it.

    Parameters:
        date_entry (str): Date in 'YYYYMMDD' format.
        cycle_runtime (str): Cycle runtime in 'HH' format (e.g., '00', '06', '12', '18').
        forecast_hour (int): Forecast hour (e.g., 24, 48).
        atmospheric_data_dir (str): Directory path where GRIB2 files are stored.

    Returns:
        str: Path to the GRIB2 file if it exists or was downloaded successfully.

    Raises:
        Exception: If the GRIB2 file could not be found or downloaded.
    """
    forecast_hour_str = str(forecast_hour).zfill(3)
    filename = f"gfs.t{cycle_runtime}z.pgrb2.0p25.f{forecast_hour_str}"  # Removed '.grib2'
    file_path = os.path.abspath(os.path.join(atmospheric_data_dir, filename))

    logger.debug(f"Checking existence of GRIB2 file: {file_path}")

    if os.path.exists(file_path):
        logger.info(f"GRIB2 file '{filename}' already exists.")
        return file_path
    else:
        logger.warning(f"GRIB2 file '{file_path}' does not exist. Initiating download.")
        try:
            downloaded_file = download_gfs_data(
                date_entry=date_entry,
                cycle_runtime=cycle_runtime,
                forecast_hour=forecast_hour,
                save_path=atmospheric_data_dir
            )
            return downloaded_file
        except Exception as e:
            logger.error(f"Failed to download GRIB2 file: {e}")
            return None


if __name__ == "__main__":
    # Example usage of the download_gfs_data function
    import argparse

    # Setup command-line argument parsing
    parser = argparse.ArgumentParser(description="Download GRIB2 data from NOAA's NOMADS server.")
    parser.add_argument("--date", required=True, help="Date in 'YYYYMMDD' format.")
    parser.add_argument("--cycle", required=True, help="Cycle runtime in 'HH' format (e.g., '00', '06', '12', '18').")
    parser.add_argument("--forecast", type=int, required=True, help="Forecast hour (e.g., 24, 48).")
    parser.add_argument("--save_dir", required=True, help="Directory path to save the downloaded GRIB2 file.")

    args = parser.parse_args()

    try:
        downloaded_file = download_gfs_data(
            date_entry=args.date,
            cycle_runtime=args.cycle,
            forecast_hour=args.forecast,
            save_path=args.save_dir
        )
        logger.info(f"GRIB2 data downloaded and validated: {downloaded_file}")
    except Exception as e:
        logger.critical(f"Failed to download and validate GRIB2 data: {e}")
