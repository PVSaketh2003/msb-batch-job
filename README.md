```markdown
# MSB Ingestion Batch Pipeline

A fully reproducible, deterministic, and containerized MLOps batch processing job for trading signal pipelines. This project ingests tracking data, validates data layouts against schema anomalies, processes mathematical rolling features, and exports telemetry metrics under strict latency constraints.

---

## 🏗️ Project Architecture

This pipeline is built as a stateless, isolated compute unit using Docker. Instead of storing data inside the container, it utilizes a decoupled volume-mounting strategy to process data and save telemetry logs back to the host machine.


```

+--------------------------+          Volume Mount          +--------------------------+
|                          | <----------------------------> |                          |
|    Host Machine Storage  |                                |   Isolated Container     |
|                          |          ( /workspace )        |                          |
|   - data.csv             |                                |   - run.py               |
|   - config.yaml          |   Maps host folder directly    |   - python:3.11-slim OS  |
|   - metrics.json (output)|   into the active container    |   - pandas / pyyaml / np  |
|   - run.log      (output)|                                |                          |
+--------------------------+                                +--------------------------+

```

### Key MLOps Principles Implemented:
* **Mathematical Data Integrity:** Uses a fixed lookback sliding window. First $N-1$ rows are programmatically filtered out from metrics calculations due to insufficient lookback data, ensuring noise-free rolling evaluation.
* **100% Deterministic Reproducibility:** Pipeline operations are locked down via an environment seed framework (`seed_applied: 42`).
* **Automated Telemetry:** Emits structured console logging alongside machine-readable JSON payloads (`metrics.json`) optimized for Datadog or Prometheus log scrapers.

---

## 🛠️ Quick Start & Local Execution

If you prefer to run the pipeline inside a local Python environment:

1. **Activate your environment and install dependencies:**
   ```bash
   source myenvironment/bin/activate
   pip install -r requirements.txt

```

2. **Execute the batch job CLI:**
```bash
python run.py \
  --input data.csv \
  --config config.yaml \
  --output metrics.json \
  --log-file run.log

```



---

## 🐳 Production Docker Deployment

To bypass local setup and run this workload with complete environment isolation on any architecture (including Apple Silicon M-series chips), use the unified Docker orchestration flow.

### Step 1: Build the Image

Compile the source code, configure the internal working directory, and layer-cache your required libraries:

```bash
docker build -t msb-batch-job .

```

### Step 2: Execute the Containerized Batch Run

Run the container. This automatically destroys the runtime container footprint upon completion (`--rm`) while safely streaming data out to your host files:

```bash
docker run --rm \
  -v "$(pwd)":/workspace \
  msb-batch-job \
  --input /workspace/data.csv \
  --config /workspace/config.yaml \
  --output /workspace/metrics.json \
  --log-file /workspace/run.log

```

---

## 📊 Telemetry Output Structure

Upon a successful batch run, the following system operational signature is saved to `metrics.json`:

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
