# MSB Ingestion Batch Pipeline

A fully reproducible, deterministic, and containerized MLOps batch processing pipeline designed for trading signal analytics and telemetry generation. The system ingests structured tracking data, validates schema integrity, computes rolling-window features, generates signal statistics, and exports operational metrics under strict latency constraints.

The pipeline follows modern MLOps principles including reproducibility, observability, environment isolation, deterministic execution, and automated telemetry collection.

---

# Project Architecture

The pipeline is implemented as a stateless Dockerized workload. Input and output files are stored on the host machine while computation is performed inside an isolated container. A Docker volume mount bridges the host filesystem and the container workspace, allowing seamless data exchange without file duplication.

```text
┌─────────────────────────────────────┐          Volume Mount          ┌─────────────────────────────────────┐
│                                     │◄─────────────────────────────►│                                     │
│         Host Machine Storage        │                               │         Isolated Container          │
│                                     │        Mounted Path           │                                     │
│         (/local/project)            │        (/workspace)           │      python:3.11-slim Runtime      │
│                                     │                               │                                     │
│  Input Files:                       │                               │  Application Files:                │
│  • data.csv                         │                               │  • run.py                          │
│  • config.yaml                      │                               │                                     │
│                                     │                               │  Installed Packages:               │
│  Output Files:                      │                               │  • pandas                          │
│  • metrics.json                     │                               │  • numpy                           │
│  • run.log                          │                               │  • pyyaml                          │
│                                     │                               │                                     │
│  Host directory is directly mapped  │                               │  Container reads and writes files  │
│  into the running container.        │                               │  through the mounted volume.       │
│                                     │                               │                                     │
└─────────────────────────────────────┘                               └─────────────────────────────────────┘
```

---

# End-to-End Pipeline Flow

```text
┌─────────────┐
│  data.csv   │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│   Validation    │
│ (Schema Checks) │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│ Feature Engine  │
│ Rolling Window  │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│ Signal Metrics  │
│ Computation     │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│ Telemetry Export│
└──────┬──────────┘
       │
       ├──────────► metrics.json
       │
       └──────────► run.log
```

---

# Detailed Processing Workflow

## Step 1: Input Data Ingestion

The pipeline begins by loading structured input data from:

```text
data.csv
```

Example:

```csv
| timestamp           | open     | high     | low      | close    | volume_btc | volume_usd |
| ------------------- | -------- | -------- | -------- | -------- | ---------- | ---------- |
| 2024-01-01 00:00:00 | 44910.83 | 45085.78 | 44910.83 | 45024.68 | 3.640837   | 163927.55  |
| 2024-01-01 00:01:00 | 44977.19 | 45045.33 | 44977.19 | 45017.83 | 33.752474  | 1519463.07 |

```

This file contains the raw observations used for downstream signal computation.

---

## Step 2: Configuration Loading

Runtime behavior is controlled through:

```text
config.yaml
```

Example:

```yaml
lookback_window: 5
signal_threshold: 0.75
seed: 42
```

Configuration parameters allow users to modify pipeline behavior without changing source code.

---

## Step 3: Schema Validation

Before any feature computation begins, the pipeline validates the dataset.

Validation checks include:

* Missing required columns
* Invalid data types
* Empty datasets
* Corrupted records
* Configuration consistency

Examples:

```text
✓ timestamp column exists
✓ price column exists
✓ volume column exists
✓ Dataset contains records
✓ Configuration values are valid
```

If validation fails, execution terminates immediately and the failure is logged.

---

## Step 4: Rolling Window Feature Engineering

The pipeline uses a fixed lookback sliding window to compute rolling statistics.

Example:

```yaml
lookback_window: 5
```

Input:

```text
100
101
102
103
104
105
```

Rolling Average at Row 5:

```text
(100 + 101 + 102 + 103 + 104) / 5
```

Since the first four rows do not contain sufficient historical data, they cannot produce valid rolling metrics.

Therefore:

```text
rows_processed = 10000
rows_evaluated = 9996
```

Because:

```text
10000 - (5 - 1) = 9996
```

This prevents mathematically invalid calculations and ensures signal quality.

---

## Step 5: Signal Computation

After feature generation, the pipeline computes trading signals.

Potential examples include:

```text
BUY
SELL
HOLD
```

or binary outputs:

```text
1
0
```

depending on the configured strategy.

Generated signals are used to derive operational statistics and monitoring metrics.

---

## Step 6: Metrics Generation

The pipeline calculates telemetry metrics describing execution behavior.

Example metrics:

```json
{
    "rows_processed": 10000,
    "rows_evaluated": 9996,
    "signal_rate": 0.4991,
    "latency_ms": 19.21
}
```

Metric Definitions:

| Metric         | Description                          |
| -------------- | ------------------------------------ |
| rows_processed | Total rows read from input           |
| rows_evaluated | Rows eligible for signal generation  |
| signal_rate    | Percentage of rows producing signals |
| latency_ms     | Total processing latency             |
| status         | Final execution status               |

---

## Step 7: Telemetry Export

Upon successful completion, the pipeline writes machine-readable telemetry data:

```text
metrics.json
```

Example:

```json
{
    "pipeline_version": "v1",
    "seed_applied": 42,
    "rows_processed": 10000,
    "rows_evaluated": 9996,
    "signal_rate": 0.4991,
    "latency_ms": 19.21,
    "status": "SUCCESS"
}
```

This output can be consumed by:

* Monitoring systems
* CI/CD pipelines
* Dashboards
* Alerting frameworks
* Operational analytics tools

---

## Step 8: Structured Logging

Execution events are recorded in:

```text
run.log
```

Example:

```text
[INFO] Loading data.csv
[INFO] Loaded 10000 rows
[INFO] Validation successful
[INFO] Computing rolling features
[INFO] Generating signals
[INFO] Exporting metrics
[INFO] Pipeline completed successfully
```

Logs provide observability and simplify debugging.

---

# Key MLOps Principles Implemented

## Mathematical Data Integrity

A fixed lookback sliding window ensures only statistically valid observations participate in rolling calculations. Initial rows lacking sufficient historical context are automatically excluded.

## Deterministic Reproducibility

All stochastic operations are controlled through a fixed seed:

```json
"seed_applied": 42
```

This guarantees identical results across repeated executions.

## Environment Isolation

The pipeline runs inside a Docker container, eliminating dependency conflicts and ensuring consistent behavior across environments.

## Observability

Structured telemetry and logging provide visibility into pipeline health, performance, and execution outcomes.

## Stateless Execution

Containers are created for execution and destroyed immediately after completion. No persistent application state exists inside the container.

## Portability

The same workload can execute on:

* Developer laptops
* Virtual machines
* CI/CD runners
* Kubernetes clusters
* Cloud environments

without modification.

---

# Quick Start (Local Python Execution)

Install dependencies:

```bash
source myenvironment/bin/activate
pip install -r requirements.txt
```

Run the pipeline:

```bash
python run.py \
  --input data.csv \
  --config config.yaml \
  --output metrics.json \
  --log-file run.log
```

---

# Production Docker Deployment

## Build the Docker Image

```bash
docker build -t msb-batch-job .
```

This creates a portable runtime image containing:

* Python 3.11
* Application source code
* Required dependencies
* Runtime configuration

---

## Execute the Containerized Job

```bash
docker run --rm \
  -v "$(pwd)":/workspace \
  msb-batch-job \
  --input /workspace/data.csv \
  --config /workspace/config.yaml \
  --output /workspace/metrics.json \
  --log-file /workspace/run.log
```

Explanation:

| Parameter  | Purpose                                             |
| ---------- | --------------------------------------------------- |
| --rm       | Automatically removes container after execution     |
| -v         | Mounts host directory into container                |
| /workspace | Shared directory visible to both host and container |
| --input    | Input dataset path                                  |
| --config   | Configuration file path                             |
| --output   | Metrics output file                                 |
| --log-file | Execution log file                                  |

---

# Container Lifecycle

```text
Container Created
        │
        ▼
Input Files Mounted
        │
        ▼
Data Validation
        │
        ▼
Feature Engineering
        │
        ▼
Signal Computation
        │
        ▼
Telemetry Export
        │
        ▼
Logs Generated
        │
        ▼
Container Destroyed
```

Because the container runs with:

```bash
--rm
```

all temporary resources are automatically cleaned up after execution while outputs remain safely stored on the host machine.

---

# Example Telemetry Output

```json
{
    "pipeline_version": "v1",
    "seed_applied": 42,
    "rows_processed": 10000,
    "rows_evaluated": 9996,
    "signal_rate": 0.4991,
    "latency_ms": 19.21,
    "status": "SUCCESS"
}
```

A successful run indicates that data ingestion, validation, feature computation, signal generation, and telemetry export completed without errors.
