# Request Flow

This document outlines how client requests are processed by the service.

## Overview
The application is a Flask web server. Users access endpoints through their browser. The main entry point is `webapp.py` and the alerts API in `alerts_api.py`. Helper logic lives in modules under `modules/`.

The application stores configuration in `domain.json` and keeps metric history files in the `history_files/` directory.

## Sequence
```mermaid
sequenceDiagram
    participant Browser
    participant WebApp
    participant AlertsAPI
    participant Utils
    participant Metrics
    participant Budget
    participant HistoryFiles as "history_files/"
    participant DomainConfig as "domain.json"

    Browser->>WebApp: GET /get_stats?domain=...
    WebApp->>Utils: load_domains()
    Utils->>DomainConfig: read
    WebApp->>Metrics: load_history(domain)
    Metrics->>HistoryFiles: read
    WebApp-->>Browser: JSON stats

    Browser->>AlertsAPI: GET /check_metrics
    AlertsAPI->>Budget: load_budget()
    Budget->>DomainConfig: read
    AlertsAPI->>Budget: get_latest_metrics(domain)
    Budget->>HistoryFiles: read
    AlertsAPI-->>Browser: JSON result
```

The same helpers are used by other `webapp.py` routes (e.g., `/reset_history`) to write or remove files in `history_files/`.

