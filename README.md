# MLOps Batch Job - Trading Signal Pipeline

A minimal, deterministic, and containerized MLOps-style batch job that reads financial OHLCV market data, calculates a rolling average on the close price, and triggers a binary trading signal.

---

## Features

- **Reproducibility**: Completely deterministic executions achieved via random seed seeding and explicit configuration.
- **Observability**: Logs pipeline events to standard error and a file (`run.log`), and prints final metrics as machine-readable JSON to standard output.
- **Robust Validation**: Gracefully handles and reports invalid CSV shapes, missing columns, empty datasets, and config structure errors.
- **Containerized Deployment**: Designed to run cleanly inside a Docker container using `python:3.9-slim`.

---

## Local Setup & Run

### 1. Prerequisites
Ensure Python 3.8+ is installed on your machine.

### 2. Install Dependencies
Install the required dependencies using `pip`:
```bash
pip install -r requirements.txt
```

### 3. Run the Pipeline
Run the script using the required CLI syntax:
```bash
python run.py --input data.csv --config config.yaml --output metrics.json --log-file run.log
```

---

## Docker Build & Run

Ensure the Docker daemon is running on your machine, then execute the following commands:

### 1. Build the Docker Image
```bash
docker build -t mlops-task .
```

### 2. Run the Container (Standard ephemeral execution)
To run the container and output the metrics JSON to standard output (stdout), run:
```bash
docker run --rm mlops-task
```

### 3. Run the Container (Persist outputs to host)
Since running with `--rm` cleans up container files when it exits, `metrics.json` and `run.log` created inside the container will be deleted.

To persist `metrics.json` and `run.log` to your host machine's directory, run the container with a directory bind mount (which maps your current host directory to `/app` inside the container):
```bash
docker run --rm -v "$(pwd)":/app mlops-task
```
Running this will write the output files `metrics.json` and `run.log` directly into your host project directory, while still printing the final metrics JSON to standard output.

---

## Output Formats

### Example `metrics.json` (Success)
```json
{
  "version": "v1",
  "rows_processed": 10000,
  "metric": "signal_rate",
  "value": 0.5076,
  "latency_ms": 25,
  "seed": 42,
  "status": "success"
}
```

### Example `metrics.json` (Error)
```json
{
  "version": "v1",
  "status": "error",
  "error_message": "Dataset file not found: data.csv"
}
```

### Signal Logic Details
- The rolling mean of the `close` column is computed using the `window` size specified in the configuration (e.g., `5`).
- The first `window - 1` rows (4 rows for `window = 5`) do not have sufficient historical data to compute a rolling mean. These are marked as `NaN` and **excluded** from the `signal_rate` calculation to maintain metric accuracy.
- For all valid rows:
  - `signal = 1` if `close > rolling_mean`
  - `signal = 0` if `close <= rolling_mean`
- `signal_rate` is computed as the mean of all valid signals.
