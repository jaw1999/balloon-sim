# test_download.py

from data_downloader import download_gfs_data

def test_download():
    date_entry = '20241001'         # Example date (YYYYMMDD)
    cycle_runtime = '06'            # Example cycle ('00', '06', '12', '18')
    forecast_hour = 24              # Example forecast hour
    save_path = 'data/atmospheric_data'  # Directory to save the downloaded file

    try:
        file_path = download_gfs_data(date_entry, cycle_runtime, forecast_hour, save_path)
        print(f"Downloaded file to: {file_path}")
    except Exception as e:
        print(f"Download failed: {e}")

if __name__ == '__main__':
    test_download()
