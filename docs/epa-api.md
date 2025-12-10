# EPD Punjab Air Quality API Documentation

## Overview

The EPD Punjab API provides access to real-time and historical air quality data from monitoring stations across Punjab, Pakistan. This documentation outlines the available endpoints, authentication requirements, and data formats.

**Base URL**: `https://api.epd-punjab-pk.com`

## Authentication

All API endpoints require authentication using an API key. The API key must be included in the HTTP header:

**Header**: `X-API-Key: your_api_key_here`

**Example Usage**:

```javascript
fetch("https://api.epd-punjab-pk.com/latest", {
  headers: {
    "X-API-Key": "your_api_key_here",
  },
});
```

To obtain an API key, please contact the EnviroPak Industrial Solutions administration.

## Monitoring Stations

The API provides data from the following monitoring stations:

| Station Code | Station Name   |
| ------------ | -------------- |
| 001          | Kasur          |
| 002          | Narowal        |
| 003          | Hafizabad      |
| 004          | Gujrat         |
| 005          | Chakwal        |
| 006          | Khanewal       |
| 007          | Muzaffargarh   |
| 008          | Rahim Yar Khan |

## Pollutants Measured

The API provides data for the following pollutants and parameters:

- O3 (Ozone)
- CO (Carbon Monoxide)
- SO2 (Sulfur Dioxide)
- NO (Nitric Oxide)
- NO2 (Nitrogen Dioxide)
- NOX (Nitrogen Oxides)
- PM10 (Particulate Matter ≤10μm)
- PM25 (Particulate Matter ≤2.5μm)
- WS (Wind Speed)
- WD (Wind Direction)
- Temp (Temperature)
- RH (Relative Humidity)
- BP (Barometric Pressure)
- Rain (Precipitation)
- SR (Solar Radiation)

## API Endpoints

### 1. Latest Data

Retrieves the most recent air quality data from all monitoring stations.

- **URL**: `/latest`
- **Method**: `GET`
- **Authentication**: Required
- **Response Format**: JSON

**Response Example**:

```json
{
  "Kasur": {
    "60_min": {
      "Date_Time": "2025-05-15 10:00:00",
      "O3": "25.3",
      "CO": "0.8",
      "SO2": "5.2",
      "NO": "12.7",
      "NO2": "18.3",
      "NOX": "31.0",
      "PM10": "78.5",
      "PM25": "35.6",
      "WS": "2.4",
      "WD": "180",
      "Temp": "32.1",
      "RH": "45",
      "BP": "1013.2",
      "Rain": "0.0",
      "SR": "850.5",
      "PM25_AQI": 101,
      "AQI_category": "Moderate"
    },
    "1440_min": {
      "Date_Time": "2025-05-15 00:00:00",
      "O3": "22.1",
      "CO": "0.7",
      "SO2": "4.8",
      "NO": "10.5",
      "NO2": "15.2",
      "NOX": "25.7",
      "PM10": "65.3",
      "PM25": "28.9",
      "WS": "1.8",
      "WD": "175",
      "Temp": "29.8",
      "RH": "48",
      "BP": "1012.5",
      "Rain": "0.0",
      "SR": "720.3",
      "PM25_AQI": 85,
      "AQI_category": "Satisfactory"
    }
  }
  // Other stations follow the same format
}
```

### 2. Daily Data (Hourly Readings)

Retrieves hourly air quality data for the past 24 hours from all monitoring stations.

- **URL**: `/daily`
- **Method**: `GET`
- **Authentication**: Required
- **Response Format**: JSON

**Response Example**:

```json
{
  "Kasur": [
    {
      "Date_Time": "2025-05-14 11:00:00",
      "O3": "22.4",
      "CO": "0.6",
      "SO2": "4.5",
      "NO": "9.8",
      "NO2": "14.6",
      "NOX": "24.4",
      "PM10": "62.7",
      "PM25": "27.3",
      "WS": "1.9",
      "WD": "170",
      "Temp": "28.5",
      "RH": "50",
      "BP": "1012.8",
      "Rain": "0.0",
      "SR": "780.2",
      "PM25_AQI": 82,
      "AQI_category": "Satisfactory"
    }
    // 23 more hourly entries...
  ]
  // Other stations follow the same format
}
```

### 3. Monthly Data (Daily Readings)

Retrieves daily air quality data for the past 30 days from all monitoring stations.

- **URL**: `/monthly`
- **Method**: `GET`
- **Authentication**: Required
- **Response Format**: JSON

**Response Example**:

```json
{
  "Kasur": [
    {
      "Date_Time": "2025-04-15 00:00:00",
      "O3": "20.1",
      "CO": "0.5",
      "SO2": "4.2",
      "NO": "8.7",
      "NO2": "13.5",
      "NOX": "22.2",
      "PM10": "58.4",
      "PM25": "24.8",
      "WS": "2.0",
      "WD": "165",
      "Temp": "27.0",
      "RH": "52",
      "BP": "1011.9",
      "Rain": "0.0",
      "SR": "650.8",
      "PM25_AQI": 78,
      "AQI_category": "Satisfactory"
    }
    // 29 more daily entries...
  ]
  // Other stations follow the same format
}
```

### 4. Periodic Data

Retrieves air quality data for a custom time period from all monitoring stations.

- **URL**: `/periodic`
- **Method**: `GET`
- **Authentication**: Required
- **Parameters**:
  - `start_datetime`: Start date and time (format: 'YYYY-MM-DD HH:MM:SS')
  - `end_datetime`: End date and time (format: 'YYYY-MM-DD HH:MM:SS')
  - `interval`: Data interval (optional, defaults to '60')
    - Use '60' for hourly data
    - Use '1440' for daily data
- **Response Format**: JSON

**Example Request**:

```url
/periodic?api_key=your-api-key-here&start_datetime=2025-04-01 00:00:00&end_datetime=2025-05-03 00:00:00&interval=60
```

**Response Example**:

```json
{
  "Kasur": [
    {
      "Date_Time": "2024-03-01 00:00:00",
      "O3": "22.4",
      "CO": "0.6",
      "SO2": "4.5",
      "NO": "9.8",
      "NO2": "14.6",
      "NOX": "24.4",
      "PM10": "62.7",
      "PM25": "27.3",
      "WS": "1.9",
      "WD": "170",
      "Temp": "28.5",
      "RH": "50",
      "BP": "1012.8",
      "Rain": "0.0",
      "SR": "780.2",
      "PM25_AQI": 82,
      "AQI_category": "Satisfactory"
    }
    // More entries for the specified time period...
  ]
  // Other stations follow the same format
}
```

### 5. Current AQI Data

Retrieves the current Air Quality Index (AQI) data based on PM2.5 readings from all monitoring stations.

- **URL**: `/aqi`
- **Method**: `GET`
- **Authentication**: Required
- **Response Format**: JSON

**Response Example**:

```json
{
  "Kasur": {
    "Date_Time": "2025-05-15 10:00:00",
    "PM25": "35.6",
    "PM25_AQI": 101,
    "AQI_category": "Moderate"
  },
  "Narowal": {
    "Date_Time": "2025-05-15 10:00:00",
    "PM25": "28.3",
    "PM25_AQI": 85,
    "AQI_category": "Satisfactory"
  }
  // Other stations follow the same format
}
```

### 6. Daily AQI Data

Retrieves hourly AQI data for the past 24 hours from all monitoring stations.

- **URL**: `/daily_aqi`
- **Method**: `GET`
- **Authentication**: Required
- **Response Format**: JSON

**Response Example**:

```json
{
  "Kasur": [
    {
      "Date_Time": "2025-05-14 11:00:00",
      "PM25": "27.3",
      "PM25_AQI": 82,
      "AQI_category": "Satisfactory"
    }
    // 23 more hourly entries...
  ]
  // Other stations follow the same format
}
```

### 7. Monthly AQI Data

Retrieves daily AQI data for the past 30 days from all monitoring stations.

- **URL**: `/monthly_aqi`
- **Method**: `GET`
- **Authentication**: Required
- **Response Format**: JSON

**Response Example**:

```json
{
  "Kasur": [
    {
      "Date_Time": "2025-04-15 00:00:00",
      "PM25": "24.8",
      "PM25_AQI": 78,
      "AQI_category": "Satisfactory"
    }
    // 29 more daily entries...
  ]
  // Other stations follow the same format
}
```

### 8. Single Station Daily Data

Retrieves hourly air quality data for the past 24 hours from a specific monitoring station.

- **URL**: `/daily/<station_name>`
- **Method**: `GET`
- **Authentication**: Required (X-API-Key header)
- **Parameters**:
  - `station_name`: Name of the station (e.g., "Kasur", "Narowal", etc.)
- **Response Format**: JSON

**Example Request**:

```
/daily/Kasur
```

**Response Example**:

```json
{
  "Kasur": [
    {
      "Date_Time": "2025-05-14 11:00:00",
      "O3": "22.4",
      "CO": "0.6",
      "SO2": "4.5",
      "NO": "9.8",
      "NO2": "14.6",
      "NOX": "24.4",
      "PM10": "62.7",
      "PM25": "27.3",
      "WS": "1.9",
      "WD": "170",
      "Temp": "28.5",
      "RH": "50",
      "BP": "1012.8",
      "Rain": "0.0",
      "SR": "780.2",
      "PM25_AQI": 82,
      "AQI_category": "Satisfactory"
    }
    // 23 more hourly entries...
  ]
}
```

### 9. Single Station Monthly Data

Retrieves daily air quality data for the past 30 days from a specific monitoring station.

- **URL**: `/monthly/<station_name>`
- **Method**: `GET`
- **Authentication**: Required (X-API-Key header)
- **Parameters**:
  - `station_name`: Name of the station (e.g., "Kasur", "Narowal", etc.)
- **Response Format**: JSON

**Example Request**:

```
/monthly/Kasur
```

**Response Example**:

```json
{
  "Kasur": [
    {
      "Date_Time": "2025-04-15 00:00:00",
      "O3": "20.1",
      "CO": "0.5",
      "SO2": "4.2",
      "NO": "8.7",
      "NO2": "13.5",
      "NOX": "22.2",
      "PM10": "58.4",
      "PM25": "24.8",
      "WS": "2.0",
      "WD": "165",
      "Temp": "27.0",
      "RH": "52",
      "BP": "1011.9",
      "Rain": "0.0",
      "SR": "650.8",
      "PM25_AQI": 78,
      "AQI_category": "Satisfactory"
    }
    // 29 more daily entries...
  ]
}
```

### 10. Single Station Periodic Data

Retrieves air quality data for a custom time period from a specific monitoring station.

- **URL**: `/periodic/<station_name>`
- **Method**: `GET`
- **Authentication**: Required (X-API-Key header)
- **Parameters**:
  - `station_name`: Name of the station (e.g., "Kasur", "Narowal", etc.)
  - `start_datetime`: Start date and time (format: 'YYYY-MM-DD HH:MM:SS')
  - `end_datetime`: End date and time (format: 'YYYY-MM-DD HH:MM:SS')
  - `interval`: Data interval (optional, defaults to '60')
    - Use '60' for hourly data
    - Use '1440' for daily data
- **Response Format**: JSON

**Example Request**:

```
/periodic/Kasur?start_datetime=2025-04-01 00:00:00&end_datetime=2025-05-03 00:00:00&interval=60
```

**Response Example**:

```json
{
  "Kasur": [
    {
      "Date_Time": "2025-04-01 00:00:00",
      "O3": "22.4",
      "CO": "0.6",
      "SO2": "4.5",
      "NO": "9.8",
      "NO2": "14.6",
      "NOX": "24.4",
      "PM10": "62.7",
      "PM25": "27.3",
      "WS": "1.9",
      "WD": "170",
      "Temp": "28.5",
      "RH": "50",
      "BP": "1012.8",
      "Rain": "0.0",
      "SR": "780.2",
      "PM25_AQI": 82,
      "AQI_category": "Satisfactory"
    }
    // More entries for the specified time period...
  ]
}
```

## AQI Categories

The API calculates AQI based on PM2.5 concentrations using the following categories:

| AQI Range |           Category            |
| :-------: | :---------------------------: |
|   0-50    |             Good              |
|  51-100   |         Satisfactory          |
|  101-150  |           Moderate            |
|  151-200  | Unhealthy for sensitive group |
|  201-300  |           Unhealthy           |
|  301-400  |        Very Unhealthy         |
|  401-500  |           Hazardous           |

## Error Handling

The API will return appropriate HTTP status codes along with error messages in the following format:

```json
{
  "error": "Error message describing the issue"
}
```

Common error codes:

- `401`: Authentication failed (Invalid or missing API key)
- `400`: Bad request (Invalid parameters)
- `500`: Server error (Database connection issues, processing errors)

## Notes

- PM2.5 is referenced as "PM25" in the API responses for consistency
- The API calculates AQI based on US EPA standards for PM2.5
- For the periodic endpoint, ensure datetime values are in the correct format (YYYY-MM-DD HH:MM:SS)
