import argparse
import json
import logging
import os
import sys
import time
import numpy as np
import pandas as pd
import yaml

# Configure structured logging format to standard output
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("msb-pipeline")


def parse_args():
    parser = argparse.ArgumentParser(
        description="MetaStackerBandit Minimal MLOps Batch Job"
    )
    parser.add_argument(
        "--input", required=True, help="Path to input data.csv"
    )
    parser.add_argument(
        "--config", required=True, help="Path to config.yaml"
    )
    parser.add_argument(
        "--output", required=True, help="Path to output metrics.json"
    )
    parser.add_argument(
        "--log-file", required=True, help="Path to output run.log"
    )
    return parser.parse_args()


def load_config(config_path):
    logger.info(f"Loading configuration from: {config_path}")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r") as f:
        try:
            config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML format: {e}")

    # Explicit MLOps Validation
    required_keys = ["seed", "window", "version"]
    for key in required_keys:
        if not config or key not in config:
            raise KeyError(f"Missing required config key: '{key}'")

    return config


def load_and_validate_data(data_path):
    logger.info(f"Loading dataset from: {data_path}")
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Input data file not found: {data_path}")

    try:
        if os.path.getsize(data_path) == 0:
            raise ValueError("Input data file is completely empty.")

        # Read the dataframe
        df = pd.read_csv(data_path)
        
        # FIX FOR QUOTE-WRAPPED HEADERS:
        # If the entire header row got lumped into a single column because of outer quotes
        if len(df.columns) == 1 and ',' in df.columns[0]:
            logger.info("Detected quote-wrapped layout. Re-parsing with split strategy...")
            raw_col_string = df.columns[0]
            clean_cols = [c.replace('"', '').replace("'", "").strip().lower() for c in raw_col_string.split(',')]
            
            # Split the single text column into multiple columns
            df = df[df.columns[0]].str.split(',', expand=True)
            df.columns = clean_cols
        else:
            # Standard cleanup if columns parsed separately but have stray quotes
            df.columns = df.columns.str.replace('"', '').str.replace("'", "").str.strip().str.lower()
        
    except pd.errors.EmptyDataError:
        raise ValueError("Input CSV is empty or lacks readable columns.")
    except Exception as e:
        raise ValueError(f"Invalid CSV format or parsing error: {e}")

    # Validation check
    if "close" not in df.columns:
        raise KeyError(f"Required column 'close' is missing. Available columns: {list(df.columns)}")

    # Ensure data is numeric (stripping away quotes from data values if present)
    df["close"] = df["close"].astype(str).str.replace('"', '').str.replace("'", "").str.strip()
    df["close"] = pd.to_numeric(df["close"], errors='coerce')
    
    # Drop rows where 'close' couldn't be parsed as a number
    df = df.dropna(subset=["close"])
    
    if len(df) == 0:
        raise ValueError("No valid numerical values found in 'close' column.")

    return df


def main():
    start_time = time.perf_counter()

    # 1. Parse arguments & dynamically attach file logging
    args = parse_args()
    file_handler = logging.FileHandler(args.log_file)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    )
    logger.addHandler(file_handler)

    logger.info("Pipeline execution started.")

    try:
        # 2. Load & Validate Config
        config = load_config(args.config)

        # Enforce Reproducibility via seed
        seed = config["seed"]
        np.random.seed(seed)
        logger.info(f"Deterministic seed set to: {seed}")

        # 3. Load & Validate Data
        df = load_and_validate_data(args.input)
        rows_processed = len(df)
        logger.info(f"Successfully loaded {rows_processed} rows.")

        # 4. Core Transformation: Rolling Mean
        window = config["window"]
        logger.info(f"Computing rolling mean with window size: {window}")

        if len(df) < window:
            raise ValueError(
                f"Dataset size ({len(df)}) is smaller than window size ({window})."
            )

        df["rolling_mean"] = df["close"].rolling(window=window).mean()

        # Consistent handling of window edge-cases: drop first window-1 NaN rows
        df_clean = df.dropna(subset=["rolling_mean"]).copy()

        # 5. Signal Generation
        df_clean["signal"] = (
            df_clean["close"] > df_clean["rolling_mean"]
        ).astype(int)

        # 6. Metrics Calculation & Performance Profiling
        signal_rate = float(df_clean["signal"].mean())
        end_time = time.perf_counter()
        latency_ms = (end_time - start_time) * 1000

        metrics = {
            "pipeline_version": config["version"],
            "seed_applied": seed,
            "rows_processed": rows_processed,
            "rows_evaluated": len(df_clean),
            "signal_rate": round(signal_rate, 4),
            "latency_ms": round(latency_ms, 2),
            "status": "SUCCESS",
        }

        # Export machine-readable metrics JSON
        with open(args.output, "w") as f:
            json.dump(metrics, f, indent=4)

        logger.info(f"Pipeline finished successfully. Metrics exported to {args.output}")

    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}", exc_info=True)

        # Fallback to write machine-readable failure logs
        end_time = time.perf_counter()
        failure_metrics = {
            "status": "FAILED",
            "error_message": str(e),
            "latency_ms": round((end_time - start_time) * 1000, 2),
        }
        try:
            with open(args.output, "w") as f:
                json.dump(failure_metrics, f, indent=4)
        except Exception:
            pass

        sys.exit(1)


if __name__ == "__main__":
    main()