from flask import Flask, jsonify, request
import pyodbc
from datetime import datetime
from flask_cors import CORS
import os
from functools import wraps
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app)

# database config (overridable via environment variables)
server = os.getenv('MSSQL_SERVER', 'SERVER_IP')
database = os.getenv('MSSQL_DATABASE', 'central_replica')
username = os.getenv('MSSQL_USERNAME', 'enviro_api')
password = os.getenv('MSSQL_PASSWORD', 'Enviropak123-')

# API authentication
API_KEY = os.getenv('API_KEY', 'your_secret_api_key_here')


def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key != API_KEY:
            return jsonify({"error": "Invalid or missing API key"}), 401
        return f(*args, **kwargs)
    return decorated_function


# station metadata
stations = {
    "001": "Kasur",
    "002": "Narowal",
    "003": "Hafizabad",
    "004": "Gujrat",
    "005": "Chakwal",
    "006": "Khanewal",
    "007": "Muzaffargarh",
    "008": "Rahim Yar Khan",
    "009": "Nankana Sahib",
    "010": "Okara",
    "011": "Sahiwal",
    "012": "Pakpattan",
}

# time intervals and table suffixes
intervals = {
    # "5": "5_min",
    # "15": "15_min",
    "60": "60_min",
    "1440": "1440_min"
}

# pollutant mapping
pollutants = [
    "O3", "CO", "SO2", "NO", "NO2", "NOX",
    "PM10", "PM2.5", "WS", "WD", "Temp", "RH", "BP", "Rain", "SR"
]

# Define breakpoint tables for PM2.5
pm25_breakpoints = [
    {"Ip": 17, "BPLo": 0, "BPHi": 15, "ILo": 0, "IHi": 50},
    {"Ip": 85, "BPLo": 15.1, "BPHi": 35, "ILo": 51, "IHi": 100},
    {"Ip": 150, "BPLo": 35.1, "BPHi": 70, "ILo": 101, "IHi": 150},
    {"Ip": 171, "BPLo": 70.1, "BPHi": 150, "ILo": 151, "IHi": 200},
    {"Ip": 203, "BPLo": 150.1, "BPHi": 250, "ILo": 201, "IHi": 300},
    {"Ip": 321, "BPLo": 250.1, "BPHi": 350, "ILo": 301, "IHi": 400},
    {"Ip": 403, "BPLo": 350.1, "BPHi": 500, "ILo": 401, "IHi": 500}
]

# Define AQI categories
aqi_categories = [
    {"range": [0, 50], "category": "Good"},
    {"range": [51, 100], "category": "Satisfactory"},
    {"range": [101, 150], "category": "Moderate"},
    {"range": [151, 200], "category": "Unhealthy for sensitive group"},
    {"range": [201, 300], "category": "Unhealthy"},
    {"range": [301, 400], "category": "Very Unhealthy"},
    {"range": [401, 500], "category": "Hazardous"}
]


def create_db_connection():
    return pyodbc.connect(
        f'DRIVER={{ODBC Driver 17 for SQL Server}};'
        f'SERVER={server};'
        f'DATABASE={database};'
        f'UID={username};'
        f'PWD={password};'
        f'Trusted_Connection=no;'
    )


def calculate_aqi(pm25_value):
    if pm25_value is None or pm25_value == "" or float(pm25_value) < 0:
        return None, None

    try:
        conc = round(float(pm25_value))
        for bp in pm25_breakpoints:
            if bp["BPLo"] <= conc <= bp["BPHi"]:
                aqi = ((bp["IHi"] - bp["ILo"]) / (bp["BPHi"] -
                       bp["BPLo"])) * (conc - bp["BPLo"]) + bp["ILo"]
                aqi = round(aqi)
                category = None
                for cat in aqi_categories:
                    if cat["range"][0] <= aqi <= cat["range"][1]:
                        category = cat["category"]
                        break
                return aqi, category
    except (ValueError, TypeError):
        # If conversion to float fails, it's not a valid number
        return None, None

    return None, None


def get_latest_data():
    data = {}
    try:
        conn = create_db_connection()
        cursor = conn.cursor()

        select_cols = ["Date_Time"]
        for i in range(1, len(pollutants) + 1):
            select_cols.append(f"Value{i}")
            select_cols.append(f"Status{i}")
        select_clause = ", ".join(select_cols)

        for station_code, station_name in stations.items():
            station_entry = {}
            for interval_code, label in intervals.items():
                table = f'dbo.S{station_code}T{interval_code}'
                try:
                    cursor.execute(
                        f"SELECT TOP 1 {select_clause} FROM {table} ORDER BY Date_Time DESC")
                    row = cursor.fetchone()
                    if row:
                        columns = [col[0] for col in cursor.description]
                        row_dict = dict(zip(columns, row))
                        latest_datetime = row_dict.get("Date_Time")
                        reading = {
                            "Date_Time": str(latest_datetime),
                        }
                        for i, gas in enumerate(pollutants, start=1):
                            value_col = f"Value{i}"
                            status_col = f"Status{i}"
                            value = row_dict.get(value_col)
                            status = row_dict.get(status_col)

                            # Initial validation check for the latest value
                            is_valid = True
                            if status != 1:
                                is_valid = False
                            elif value is None or value == "" or float(value) < 0:
                                is_valid = False
                            elif gas in ["PM10", "PM2.5"]:
                                try:
                                    if float(value) > 500.0:
                                        is_valid = False
                                except (ValueError, TypeError):
                                    is_valid = False

                            if is_valid:
                                reading[gas] = value
                            else:
                                # Value is invalid, try to find the last valid one by querying previous records
                                found_previous_valid = False
                                query_prev = (
                                    f"SELECT TOP 50 Date_Time, {value_col}, {status_col} FROM {table} "
                                    f"WHERE Date_Time < ? "
                                    f"ORDER BY Date_Time DESC"
                                )
                                try:
                                    cursor.execute(query_prev, latest_datetime)
                                    prev_rows = cursor.fetchall()
                                    for prev_row_tuple in prev_rows:
                                        # Use cursor description to map columns dynamically
                                        prev_columns = [col[0]
                                                        for col in cursor.description]
                                        prev_row = dict(
                                            zip(prev_columns, prev_row_tuple))
                                        prev_value = prev_row.get(value_col)
                                        prev_status = prev_row.get(status_col)

                                        # Validation check for the previous value
                                        prev_is_valid = True
                                        if prev_status != 1:
                                            prev_is_valid = False
                                        elif prev_value is None or prev_value == "" or float(prev_value) < 0:
                                            prev_is_valid = False
                                        elif gas in ["PM10", "PM2.5"]:
                                            try:
                                                if float(prev_value) > 500.0:
                                                    prev_is_valid = False
                                            except (ValueError, TypeError):
                                                prev_is_valid = False

                                        if prev_is_valid:
                                            reading[gas] = prev_value
                                            found_previous_valid = True
                                            break  # Found the first valid previous value, stop searching
                                except pyodbc.Error as db_err:
                                    # Log or handle DB error during previous value fetch if necessary
                                    print(
                                        f"Database error fetching previous value for {gas} in {table}: {db_err}")
                                    # Fallback if query fails
                                    reading[gas] = None

                                # If no previous valid value was found after checking, set to None
                                if not found_previous_valid:
                                    reading[gas] = None

                        # Handle PM2.5 key renaming after potential backfill
                        reading["PM25"] = reading.pop("PM2.5", None)
                        aqi, category = calculate_aqi(reading["PM25"])
                        if aqi is not None:
                            reading["PM25_AQI"] = aqi
                            reading["AQI_category"] = category
                        station_entry[label] = reading
                    else:
                        station_entry[label] = {"error": "no data"}
                except Exception as e:
                    station_entry[label] = {
                        "error": f"Error processing interval {label}: {str(e)}"}
            data[station_name] = station_entry
        conn.close()
    except Exception as e:
        return {"error": f"Database connection or processing failed: {str(e)}"}
    return data


def get_historical_data(interval_code, limit):
    data = {}
    try:
        conn = create_db_connection()
        cursor = conn.cursor()
        for station_code, station_name in stations.items():
            station_data = []
            table = f'dbo.S{station_code}T{interval_code}'
            # Initialize last valid values
            last_valid_values = {gas: None for gas in pollutants}
            try:
                cursor.execute(
                    f"SELECT TOP {limit} * FROM {table} ORDER BY Date_Time DESC")
                rows = cursor.fetchall()
                if rows:
                    columns = [col[0] for col in cursor.description]
                    for row in rows:  # Iterating from newest to oldest
                        row_dict = dict(zip(columns, row))
                        current_dt = row_dict.get("Date_Time")
                        reading = {
                            "Date_Time": str(current_dt),
                        }

                        for i, gas in enumerate(pollutants, start=1):
                            value_col = f"Value{i}"
                            status_col = f"Status{i}"
                            value = row_dict.get(value_col)
                            status = row_dict.get(status_col)

                            is_valid = True
                            if status != 1:
                                is_valid = False
                            elif value is None or value == "" or float(value) < 0:
                                is_valid = False
                            elif gas in ["PM10", "PM2.5"]:
                                try:
                                    if float(value) > 500.0:
                                        is_valid = False
                                except (ValueError, TypeError):
                                    is_valid = False

                            if is_valid:
                                reading[gas] = value
                                # Update last known valid value for this pollutant
                                if gas == 'PM2.5':
                                    # Handle PM2.5 mapping
                                    last_valid_values['PM25'] = value
                                else:
                                    last_valid_values[gas] = value
                            else:
                                # Use the last known valid value
                                if gas == 'PM2.5':
                                    reading['PM25'] = last_valid_values.get(
                                        'PM25')
                                    # We don't pop PM2.5 here, handle it after the loop
                                else:
                                    reading[gas] = last_valid_values.get(gas)

                        # Handle PM2.5 specifically after loop (if it wasn't already handled due to invalidity)
                        if 'PM2.5' in reading:
                            reading['PM25'] = reading.pop('PM2.5')
                        elif 'PM25' not in reading:  # Ensure PM25 key exists even if invalid and no prior valid seen
                            reading['PM25'] = None

                        # Calculate AQI based on the potentially backfilled PM25 value
                        aqi, category = calculate_aqi(reading["PM25"])
                        if aqi is not None:
                            reading["PM25_AQI"] = aqi
                            reading["AQI_category"] = category
                        station_data.append(reading)

                    station_data.reverse()  # Reverse to get chronological order
                else:
                    station_data = [{"error": "no data"}]
            except Exception as e:
                station_data = [{"error": str(e)}]
            data[station_name] = station_data
        conn.close()
    except Exception as e:
        return {"error": f"connection failed: {str(e)}"}
    return data


def get_periodic_data(interval_code, start_datetime, end_datetime):
    data = {}
    try:
        conn = create_db_connection()
        cursor = conn.cursor()
        for station_code, station_name in stations.items():
            station_data = []
            table = f'dbo.S{station_code}T{interval_code}'
            last_valid_values = {gas: None for gas in pollutants}
            try:
                query = f"""
                    SELECT * FROM {table}
                    WHERE Date_Time BETWEEN ? AND ?
                    ORDER BY Date_Time ASC
                """
                cursor.execute(query, (start_datetime, end_datetime))
                rows = cursor.fetchall()
                if rows:
                    columns = [col[0] for col in cursor.description]
                    for row in rows:
                        row_dict = dict(zip(columns, row))
                        current_dt = row_dict.get("Date_Time")
                        reading = {
                            "Date_Time": str(current_dt),
                        }

                        for i, gas in enumerate(pollutants, start=1):
                            value_col = f"Value{i}"
                            status_col = f"Status{i}"
                            value = row_dict.get(value_col)
                            status = row_dict.get(status_col)

                            is_valid = True
                            if status != 1:
                                is_valid = False
                            elif value is None or value == "" or float(value) < 0:
                                is_valid = False
                            elif gas in ["PM10", "PM2.5"]:
                                try:
                                    if float(value) > 500.0:
                                        is_valid = False
                                except (ValueError, TypeError):
                                    is_valid = False

                            if is_valid:
                                reading[gas] = value
                                if gas == 'PM2.5':
                                    last_valid_values['PM25'] = value
                                else:
                                    last_valid_values[gas] = value
                            else:
                                if gas == 'PM2.5':
                                    reading['PM25'] = last_valid_values.get(
                                        'PM25')
                                else:
                                    reading[gas] = last_valid_values.get(gas)

                        if 'PM2.5' in reading:
                            reading['PM25'] = reading.pop('PM2.5')
                        elif 'PM25' not in reading:
                            reading['PM25'] = None

                        aqi, category = calculate_aqi(reading["PM25"])
                        if aqi is not None:
                            reading["PM25_AQI"] = aqi
                            reading["AQI_category"] = category
                        station_data.append(reading)
                else:
                    station_data = [{"error": "no data"}]
            except Exception as e:
                station_data = [{"error": str(e)}]
            data[station_name] = station_data
        conn.close()
    except Exception as e:
        return {"error": f"connection failed: {str(e)}"}
    return data


# Single-station data fetching endpoints and helpers


def get_historical_data_for_station(station_name, interval_code, limit):
    """Get historical data for a specific station only."""
    data = {}
    try:
        station_code = None
        for code, name in stations.items():
            if name == station_name:
                station_code = code
                break
        if not station_code:
            return {"error": f"Station '{station_name}' not found"}
        conn = create_db_connection()
        cursor = conn.cursor()
        station_data = []
        table = f'dbo.S{station_code}T{interval_code}'
        try:
            cursor.execute(
                f"SELECT TOP {limit} * FROM {table} ORDER BY Date_Time DESC")
            rows = cursor.fetchall()
            if rows:
                columns = [col[0] for col in cursor.description]
                for row in rows:
                    row_dict = dict(zip(columns, row))
                    current_dt = row_dict.get("Date_Time")
                    reading = {
                        "Date_Time": str(current_dt),
                    }
                    for i, gas in enumerate(pollutants, start=1):
                        value_col = f"Value{i}"
                        status_col = f"Status{i}"
                        value = row_dict.get(value_col)
                        status = row_dict.get(status_col)
                        is_valid = True
                        if status != 1:
                            is_valid = False
                        elif value is None or value == "" or float(value) < 0:
                            is_valid = False
                        elif gas in ["PM10", "PM2.5"]:
                            try:
                                if float(value) > 500.0:
                                    is_valid = False
                            except (ValueError, TypeError):
                                is_valid = False
                        if is_valid:
                            reading[gas] = value
                        else:
                            # Value is invalid, try to find the last valid one by querying previous records
                            found_previous_valid = False
                            query_prev = (
                                f"SELECT TOP 50 Date_Time, {value_col}, {status_col} FROM {table} "
                                f"WHERE Date_Time < ? "
                                f"ORDER BY Date_Time DESC"
                            )
                            try:
                                cursor.execute(query_prev, current_dt)
                                prev_rows = cursor.fetchall()
                                for prev_row_tuple in prev_rows:
                                    # Use cursor description to map columns dynamically
                                    prev_columns = [col[0]
                                                    for col in cursor.description]
                                    prev_row = dict(
                                        zip(prev_columns, prev_row_tuple))
                                    prev_value = prev_row.get(value_col)
                                    prev_status = prev_row.get(status_col)

                                    # Validation check for the previous value
                                    prev_is_valid = True
                                    if prev_status != 1:
                                        prev_is_valid = False
                                    elif prev_value is None or prev_value == "" or float(prev_value) < 0:
                                        prev_is_valid = False
                                    elif gas in ["PM10", "PM2.5"]:
                                        try:
                                            if float(prev_value) > 500.0:
                                                prev_is_valid = False
                                        except (ValueError, TypeError):
                                            prev_is_valid = False

                                    if prev_is_valid:
                                        reading[gas] = prev_value
                                        found_previous_valid = True
                                        break  # Found the first valid previous value, stop searching
                            except pyodbc.Error as db_err:
                                # Log or handle DB error during previous value fetch if necessary
                                print(
                                    f"Database error fetching previous value for {gas} in {table}: {db_err}")
                                reading[gas] = None  # Fallback if query fails

                            # If no previous valid value was found after checking, set to None
                            if not found_previous_valid:
                                reading[gas] = None
                    reading["PM25"] = reading.pop("PM2.5", None)
                    aqi, category = calculate_aqi(reading["PM25"])
                    if aqi is not None:
                        reading["PM25_AQI"] = aqi
                        reading["AQI_category"] = category
                    station_data.append(reading)
                station_data.reverse()
            else:
                station_data = [{"error": "no data"}]
        except Exception as e:
            station_data = [{"error": str(e)}]
        data[station_name] = station_data
        conn.close()
    except Exception as e:
        return {"error": f"connection failed: {str(e)}"}
    return data


def get_periodic_data_for_station(station_name, interval_code, start_datetime, end_datetime):
    """Get periodic data for a specific station only."""
    data = {}
    try:
        station_code = None
        for code, name in stations.items():
            if name == station_name:
                station_code = code
                break
        if not station_code:
            return {"error": f"Station '{station_name}' not found"}
        conn = create_db_connection()
        cursor = conn.cursor()
        station_data = []
        table = f'dbo.S{station_code}T{interval_code}'
        try:
            query = f"""
                SELECT * FROM {table}
                WHERE Date_Time BETWEEN ? AND ?
                ORDER BY Date_Time ASC
            """
            cursor.execute(query, (start_datetime, end_datetime))
            rows = cursor.fetchall()
            if rows:
                columns = [col[0] for col in cursor.description]
                for row in rows:
                    row_dict = dict(zip(columns, row))
                    current_dt = row_dict.get("Date_Time")
                    reading = {
                        "Date_Time": str(current_dt),
                    }
                    for i, gas in enumerate(pollutants, start=1):
                        value_col = f"Value{i}"
                        status_col = f"Status{i}"
                        value = row_dict.get(value_col)
                        status = row_dict.get(status_col)
                        is_valid = True
                        if status != 1:
                            is_valid = False
                        elif value is None or value == "" or float(value) < 0:
                            is_valid = False
                        elif gas in ["PM10", "PM2.5"]:
                            try:
                                if float(value) > 500.0:
                                    is_valid = False
                            except (ValueError, TypeError):
                                is_valid = False
                        if is_valid:
                            reading[gas] = value
                        else:
                            # Value is invalid, try to find the last valid one by querying previous records
                            found_previous_valid = False
                            query_prev = (
                                f"SELECT TOP 50 Date_Time, {value_col}, {status_col} FROM {table} "
                                f"WHERE Date_Time < ? "
                                f"ORDER BY Date_Time DESC"
                            )
                            try:
                                cursor.execute(query_prev, current_dt)
                                prev_rows = cursor.fetchall()
                                for prev_row_tuple in prev_rows:
                                    # Use cursor description to map columns dynamically
                                    prev_columns = [col[0]
                                                    for col in cursor.description]
                                    prev_row = dict(
                                        zip(prev_columns, prev_row_tuple))
                                    prev_value = prev_row.get(value_col)
                                    prev_status = prev_row.get(status_col)

                                    # Validation check for the previous value
                                    prev_is_valid = True
                                    if prev_status != 1:
                                        prev_is_valid = False
                                    elif prev_value is None or prev_value == "" or float(prev_value) < 0:
                                        prev_is_valid = False
                                    elif gas in ["PM10", "PM2.5"]:
                                        try:
                                            if float(prev_value) > 500.0:
                                                prev_is_valid = False
                                        except (ValueError, TypeError):
                                            prev_is_valid = False

                                    if prev_is_valid:
                                        reading[gas] = prev_value
                                        found_previous_valid = True
                                        break  # Found the first valid previous value, stop searching
                            except pyodbc.Error as db_err:
                                # Log or handle DB error during previous value fetch if necessary
                                print(
                                    f"Database error fetching previous value for {gas} in {table}: {db_err}")
                                reading[gas] = None  # Fallback if query fails

                            # If no previous valid value was found after checking, set to None
                            if not found_previous_valid:
                                reading[gas] = None
                    reading["PM25"] = reading.pop("PM2.5", None)
                    aqi, category = calculate_aqi(reading["PM25"])
                    if aqi is not None:
                        reading["PM25_AQI"] = aqi
                        reading["AQI_category"] = category
                    station_data.append(reading)
            else:
                station_data = [{"error": "no data"}]
        except Exception as e:
            station_data = [{"error": str(e)}]
        data[station_name] = station_data
        conn.close()
    except Exception as e:
        return {"error": f"connection failed: {str(e)}"}
    return data

# --- Single-station endpoints ---


@app.route('/daily/<station_name>', methods=['GET'])
@require_api_key
def daily_data_for_station(station_name):
    return jsonify(get_historical_data_for_station(station_name, "60", 24))


@app.route('/monthly/<station_name>', methods=['GET'])
@require_api_key
def monthly_data_for_station(station_name):
    return jsonify(get_historical_data_for_station(station_name, "1440", 30))


@app.route('/periodic/<station_name>', methods=['GET'])
@require_api_key
def periodic_data_for_station(station_name):
    try:
        start_datetime = request.args.get('start_datetime')
        end_datetime = request.args.get('end_datetime')
        interval = request.args.get('interval', '60')
        if not start_datetime or not end_datetime:
            return jsonify({"error": "start_datetime and end_datetime are required"}), 400
        if interval not in intervals:
            return jsonify({"error": "Invalid interval. Must be either '60' or '1440'"}), 400
        try:
            datetime.strptime(start_datetime, '%Y-%m-%d %H:%M:%S')
            datetime.strptime(end_datetime, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return jsonify({"error": "Invalid datetime format. Use 'YYYY-MM-DD HH:MM:SS'"}), 400
        return jsonify(get_periodic_data_for_station(station_name, interval, start_datetime, end_datetime))
    except Exception as e:
        return jsonify({"error": f"Periodic data retrieval failed: {str(e)}"}), 500

# API Routes


@app.route('/latest', methods=['GET'])
@require_api_key
def latest_data():
    return jsonify(get_latest_data())


@app.route('/daily', methods=['GET'])
@require_api_key
def daily_data():
    return jsonify(get_historical_data("60", 24))


@app.route('/monthly', methods=['GET'])
@require_api_key
def monthly_data():
    return jsonify(get_historical_data("1440", 30))


@app.route('/periodic', methods=['GET'])
@require_api_key
def periodic_data():
    try:
        # Get parameters from query string
        start_datetime = request.args.get('start_datetime')
        end_datetime = request.args.get('end_datetime')
        # Default to 60 minutes if not specified
        interval = request.args.get('interval', '60')

        # Validate parameters
        if not start_datetime or not end_datetime:
            return jsonify({"error": "start_datetime and end_datetime are required"}), 400

        if interval not in intervals:
            return jsonify({"error": "Invalid interval. Must be either '60' or '1440'"}), 400

        try:
            # Validate datetime format
            datetime.strptime(start_datetime, '%Y-%m-%d %H:%M:%S')
            datetime.strptime(end_datetime, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return jsonify({"error": "Invalid datetime format. Use 'YYYY-MM-DD HH:MM:SS'"}), 400

        return jsonify(get_periodic_data(interval, start_datetime, end_datetime))
    except Exception as e:
        return jsonify({"error": f"Periodic data retrieval failed: {str(e)}"}), 500


@app.route('/aqi', methods=['GET'])
@require_api_key
def get_aqi():
    try:
        latest_data = get_latest_data()
        result = {}
        for station_name, station_data in latest_data.items():
            interval_data = station_data.get("60_min", {})
            if "error" in interval_data:
                result[station_name] = {"error": interval_data["error"]}
                continue
            station_result = {
                "Date_Time": interval_data.get("Date_Time"),
                "PM25": interval_data.get("PM25"),
                "PM25_AQI": interval_data.get("PM25_AQI"),
                "AQI_category": interval_data.get("AQI_category")
            }
            result[station_name] = station_result
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"AQI calculation failed: {str(e)}"})


@app.route('/daily_aqi', methods=['GET'])
@require_api_key
def daily_aqi():
    try:
        daily_data = get_historical_data("60", 24)
        result = {}
        for station_name, readings in daily_data.items():
            if isinstance(readings, list) and len(readings) > 0 and "error" not in readings[0]:
                station_results = []
                for reading in readings:
                    entry = {
                        "Date_Time": reading.get("Date_Time"),
                        "PM25": reading.get("PM25"),
                        "PM25_AQI": reading.get("PM25_AQI"),
                        "AQI_category": reading.get("AQI_category")
                    }
                    station_results.append(entry)
                result[station_name] = station_results
            else:
                result[station_name] = [{"error": "no data"}]
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Daily AQI calculation failed: {str(e)}"})


@app.route('/monthly_aqi', methods=['GET'])
@require_api_key
def monthly_aqi():
    try:
        monthly_data = get_historical_data("1440", 30)
        result = {}
        for station_name, readings in monthly_data.items():
            if isinstance(readings, list) and len(readings) > 0 and "error" not in readings[0]:
                station_results = []
                for reading in readings:
                    entry = {
                        "Date_Time": reading.get("Date_Time"),
                        "PM25": reading.get("PM25"),
                        "PM25_AQI": reading.get("PM25_AQI"),
                        "AQI_category": reading.get("AQI_category")
                    }
                    station_results.append(entry)
                result[station_name] = station_results
            else:
                result[station_name] = [{"error": "no data"}]
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Monthly AQI calculation failed: {str(e)}"})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
