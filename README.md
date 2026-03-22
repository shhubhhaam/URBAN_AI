# Ahmedabad Urban Health Dashboard

A Streamlit-based web app for monitoring Ahmedabad's urban environmental health using temperature, vegetation, and air pollution indicators.

## Project Summary

This project helps analyze urban conditions across Ahmedabad sub-areas using:

- LST (Land Surface Temperature)
- NDVI (Normalized Difference Vegetation Index)
- NO2 (Nitrogen Dioxide)

It provides:

- Area-wise risk levels
- Interactive map visualization
- Trend analysis and comparison
- AI-assisted Q&A for planning insights
- IsolationForest-based anomaly detection

## Repository Structure

- `APP/main.py` - Main Streamlit application
- `docker-compose.yml` - PostgreSQL + pgAdmin container setup
- `init.sql` - Database schema initialization
- `requirements.txt` - Python package dependencies
- `datasets/` - Cleaned CSV files and loader scripts
- `JS_Scripts_for_data_gathering/WHOLE_AHMEDABAD.js` - GEE script for city-wide extraction
- `JS_Scripts_for_data_gathering/SUBAREA_WISE.js` - GEE script for sub-area extraction

## Prerequisites

- Python 3.11+ (or compatible)
- Docker Desktop
- Google Earth Engine account
- (Optional) GROQ API key for AI chat feature

## Setup and Run

### 1) Start PostgreSQL and pgAdmin with Docker

From project root:

```powershell
docker compose up -d postgres pgadmin
```

Check status:

```powershell
docker compose ps
```

Services:

- PostgreSQL: `localhost:5432`
- pgAdmin: `http://localhost:5050`

pgAdmin credentials:

- Email: `admin@urban.com`
- Password: `admin123`

### 2) Create and activate Python environment

```powershell
py -m venv myenv
.\myenv\Scripts\Activate.ps1
```

### 3) Install dependencies

```powershell
pip install -r requirements.txt
```

### 4) Run Streamlit app

```powershell
streamlit run .\APP\main.py
```

Open:

- `http://localhost:8501`

## Database Configuration

Current app DB settings in `APP/main.py`:

- Host: `localhost`
- Port: `5432`
- DB: `ahmedabad_urban`
- User: `urban_admin`
- Password: `ahmedabad123`

The schema is auto-initialized on first container startup using `init.sql`.

## Access PostgreSQL from Terminal

Open interactive psql inside Docker container:

```powershell
docker exec -it ahmedabad_urban_db psql -U urban_admin -d ahmedabad_urban
```

Run one query directly:

```powershell
docker exec -it ahmedabad_urban_db psql -U urban_admin -d ahmedabad_urban
```

Useful psql commands:

```sql
\dt
\d areas_lst
SELECT * FROM areas_lst LIMIT 5;
\q
```

## How Data Was Fetched from Google Earth Engine (GEE)

Data collection is done using JavaScript scripts in GEE Code Editor.

### Scripts used

- `JS_Scripts_for_data_gathering/WHOLE_AHMEDABAD.js`
- `JS_Scripts_for_data_gathering/SUBAREA_WISE.js`

### Datasets used in GEE

- LST: `MODIS/061/MOD11A2` (`LST_Day_1km`)
- NDVI: `COPERNICUS/S2_SR_HARMONIZED` (using `B8`, `B4`)
- NO2: `COPERNICUS/S5P/NRTI/L3_NO2` (`NO2_column_number_density`)

### Processing approach

- Time filter applied from configured start date to current date
- Area geometry defined as:
  - whole Ahmedabad AOI (rectangle) in city-wide script
  - 16 sub-areas with 1 km buffers in sub-area script
- LST converted from Kelvin-based scale to Celsius
- NDVI computed using normalized difference of Sentinel-2 bands
- Cloud masking applied for NDVI using `QA60`
- Monsoon months filtered for cleaner NDVI trend quality
- NO2 extracted as mean area concentration values
- Mean values extracted per timestamp and exported as CSV

### Export output from GEE

Export tasks generate CSV files to Google Drive, e.g.:

- `Ahmedabad_Areas_LST`
- `Ahmedabad_Areas_NDVI`
- `Ahmedabad_Areas_NO2`
- `Ahmedabad_LST_TS`
- `Ahmedabad_NDVI_TS`
- `Ahmedabad_NO2_TS`

After download, place CSVs into the `datasets/` directory.

## Loading Data into PostgreSQL

### Load cleaned area-wise tables

```powershell
python .\datasets\csv_to_sql.py
```

### Load unified daily/monthly tables

```powershell
python .\datasets\load_unified_data.py
```

## App Features

- Dashboard:
  - City-level KPI cards
  - Risk table and map visualization
  - Aggregated critical layer
  - IsolationForest anomaly detection
- Compare Areas:
  - Ranking charts for LST, NDVI, NO2
- Ask AI:
  - Context-aware insights from historical trends
- Trends:
  - Year-over-year trend analysis by area

## Troubleshooting

- **Connection refused on 5432**:
  - Ensure DB container is running: `docker compose ps`
- **Virtual environment activation issue**:
  - Recreate venv: `py -m venv --clear .\myenv`
- **Module not found errors**:
  - Reinstall dependencies: `pip install -r requirements.txt`
- **AI response unavailable**:
  - Set `GROQ_API_KEY` in environment or `.env`

## Stop Services

```powershell
docker compose down
```
