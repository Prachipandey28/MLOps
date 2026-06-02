#!/usr/bin/env python3
"""
MLOps Batch Job Pipeline
Computes a rolling mean on close prices and generates trading signals.
"""

import argparse
import json
import logging
import os
import sys
import time
import yaml
import numpy as np
import pandas as pd

def parse_args():
    parser = argparse.ArgumentParser(description="Run MLOps batch job trading-signal pipeline.")
    parser.add_argument("--input", required=True, help="Path to input data.csv")
    parser.add_argument("--config", required=True, help="Path to config.yaml")
    parser.add_argument("--output", required=True, help="Path to output metrics.json")
    parser.add_argument("--log-file", required=True, help="Path to output run.log")
    return parser.parse_args()

def write_metrics(output_path, metrics):
    """Writes the metrics dict to output_path and prints to stdout."""
    try:
        with open(output_path, "w") as f:
            json.dump(metrics, f, indent=2)
    except Exception as e:
        sys.stderr.write(f"Failed to write metrics file to {output_path}: {e}\n")
    
    # Print final metrics JSON to stdout
    print(json.dumps(metrics, indent=2))

def main():
    start_time = time.time()
    args = parse_args()
    
    # Configure logging
    log_dir = os.path.dirname(args.log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
        
    logger = logging.getLogger("mlops_pipeline")
    logger.setLevel(logging.INFO)
    logger.handlers = []  # Clear default handlers
    
    # File handler
    file_handler = logging.FileHandler(args.log_file, mode='w')
    file_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Stderr handler for console logs (so stdout remains clean for final metrics JSON)
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(file_formatter)
    logger.addHandler(stderr_handler)
    
    logger.info("Job started")
    
    config_version = "unknown"
    seed = None
    
    try:
        # 1) Load and validate config
        logger.info(f"Loading config from {args.config}")
        if not os.path.exists(args.config):
            raise FileNotFoundError(f"Config file not found: {args.config}")
            
        try:
            with open(args.config, 'r') as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML config format: {e}")
            
        if not isinstance(config, dict):
            raise ValueError("Config structure is invalid (must be a YAML dictionary)")
            
        for field in ['seed', 'window', 'version']:
            if field not in config:
                raise ValueError(f"Config is missing required field: '{field}'")
                
        seed = config['seed']
        window = config['window']
        config_version = config['version']
        
        if not isinstance(seed, int):
            raise ValueError("Config field 'seed' must be an integer")
        if not isinstance(window, int) or window <= 0:
            raise ValueError("Config field 'window' must be a positive integer")
        if not isinstance(config_version, str) or not config_version.strip():
            raise ValueError("Config field 'version' must be a non-empty string")
            
        logger.info(f"Config loaded and validated successfully: seed={seed}, window={window}, version={config_version}")
        
        # Set seeds for reproducibility
        np.random.seed(seed)
        logger.info(f"Set numpy random seed to {seed}")
        
        # 2) Load and validate dataset
        logger.info(f"Loading dataset from {args.input}")
        if not os.path.exists(args.input):
            raise FileNotFoundError(f"Dataset file not found: {args.input}")
            
        try:
            df = pd.read_csv(args.input)
        except pd.errors.EmptyDataError:
            raise ValueError("Input CSV file is empty")
        except pd.errors.ParserError as e:
            raise ValueError(f"Invalid CSV format: {e}")
        except Exception as e:
            raise ValueError(f"Error reading CSV file: {e}")
            
        if df.empty:
            raise ValueError("Input CSV file contains no data rows")
            
        logger.info(f"Dataset loaded with {len(df)} rows")
        
        if 'close' not in df.columns:
            raise ValueError("Input CSV file is missing required column: 'close'")
            
        if not pd.api.types.is_numeric_dtype(df['close']):
            raise ValueError("'close' column must contain numeric data")
            
        if df['close'].dropna().empty:
            raise ValueError("'close' column contains only NaNs or empty values")
            
        rows_processed = len(df)
        
        # 3) Compute Rolling Mean
        logger.info(f"Computing rolling mean on close price with window size {window}")
        df['rolling_mean'] = df['close'].rolling(window=window).mean()
        
        # Note on how we handle first window-1 rows:
        # We allow NaNs in rolling_mean for index < window - 1 and exclude these from the signal rate calculation.
        
        # 4) Generate Signals
        logger.info("Generating binary signals")
        df['signal'] = np.nan
        valid_mask = df['rolling_mean'].notna()
        df.loc[valid_mask, 'signal'] = (df.loc[valid_mask, 'close'] > df.loc[valid_mask, 'rolling_mean']).astype(int)
        
        # Calculate signal_rate (mean of signal for valid rolling mean windows)
        valid_signals = df.loc[valid_mask, 'signal']
        if len(valid_signals) > 0:
            signal_rate = float(valid_signals.mean())
        else:
            signal_rate = 0.0
            logger.warning("No rows had valid rolling mean, signal_rate defaults to 0.0")
            
        logger.info(f"Signal rate computed: {signal_rate:.4f} over {len(valid_signals)} valid rows")
        
        # 5) Latency and Success Output
        latency_ms = int((time.time() - start_time) * 1000)
        
        metrics = {
            "version": config_version,
            "rows_processed": rows_processed,
            "metric": "signal_rate",
            "value": round(signal_rate, 4),
            "latency_ms": latency_ms,
            "seed": seed,
            "status": "success"
        }
        
        logger.info(f"Job completed successfully. Metrics: {metrics}")
        logger.info(f"Job ended successfully at {time.strftime('%Y-%m-%dT%H:%M:%S')}")
        write_metrics(args.output, metrics)
        sys.exit(0)
        
    except Exception as e:
        logger.exception(f"Job failed with error: {e}")
        
        # Determine current latency up to failure point
        latency_ms = int((time.time() - start_time) * 1000)
        
        error_metrics = {
            "version": config_version,
            "status": "error",
            "error_message": str(e),
            "latency_ms": latency_ms
        }
        
        logger.info(f"Job ended with failure at {time.strftime('%Y-%m-%dT%H:%M:%S')}")
        write_metrics(args.output, error_metrics)
        sys.exit(1)

if __name__ == "__main__":
    main()
