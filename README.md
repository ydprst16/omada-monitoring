# Omada Cloud Exporter

A lightweight Prometheus exporter for **TP-Link Omada Cloud** that collects access point, Wi-Fi, client, SSID, LAN, and cloud connection metrics and exposes them for monitoring with **Prometheus** and **Grafana**.

The exporter authenticates to Omada Cloud using a persistent **Playwright Chromium session**, retrieves device and client information from the Omada Cloud APIs, and exposes the collected metrics through a Prometheus-compatible `/metrics` endpoint.

---

## Architecture

```text
                    ┌──────────────────────┐
                    │    TP-Link Omada     │
                    │        Cloud         │
                    └──────────┬───────────┘
                               │
                               │ HTTPS
                               ▼
                    ┌──────────────────────┐
                    │  Omada Cloud         │
                    │     Exporter         │
                    │                      │
                    │ Python + Flask       │
                    │ Playwright           │
                    │ Prometheus Client    │
                    └──────────┬───────────┘
                               │
                         /metrics
                         Port 9202
                               │
                               ▼
                    ┌──────────────────────┐
                    │     Prometheus       │
                    │      Port 9090       │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │       Grafana        │
                    │      Port 3000       │
                    └──────────────────────┘
```

The included Docker Compose stack runs three services:

* `omada-cloud-exporter`
* `prometheus`
* `grafana`

## Prometheus scrapes the exporter every **30 seconds**.

## Features

### Access Point Monitoring

The exporter provides metrics for:

* AP connection status
* Omada device status code
* CPU utilization
* Memory utilization
* Uptime
* RX rate
* TX rate
* Last seen timestamp
* Device IP address
* Public IP address
* Firmware version

AP status is determined from Omada's device status endpoint rather than assuming that an HTTP `200` response means the AP itself is connected.

The exporter treats Omada status code `14` as **Connected**.

---

### Client Monitoring

Client metrics include:

* Total connected clients per AP
* 2.4 GHz clients
* 5 GHz clients
* Secondary 5 GHz clients
* 6 GHz clients
* Client connection timeout count
* WPA failure count
* Client block count

Client information is collected through the authenticated Omada Cloud browser session.

The exporter automatically paginates through the Omada client API to collect all available clients.
For the current implementation:

* Channels `1–14` are classified as 2.4 GHz.
* Channels above `14` are classified as 5 GHz.
* 6 GHz remains `0` unless an explicit 6 GHz field is provided by the API.

---

### Wi-Fi Monitoring

Per-radio metrics include:

* TX utilization
* RX utilization
* Interference
* Channel
* TX power
* Center frequency
* Channel width
* Maximum TX rate

Metrics are exposed separately by radio band using the `band` label.

Example:

```text
omada_wifi_tx_util_percent{name="AP-Office",mac="...",band="2g"}
omada_wifi_tx_util_percent{name="AP-Office",mac="...",band="5g"}
```

---

### SSID Monitoring

The exporter collects SSID-level information from the Omada dashboard API:

* Traffic per SSID
* Connected clients per SSID
* Total SSID traffic
* Total SSID clients

It also exposes per-AP SSID traffic metrics for:

* Download
* Upload
* 2.4 GHz download
* 2.4 GHz upload
* 5 GHz download
* 5 GHz upload

---

### LAN / Network Health

The following LAN metrics are available:

* LAN RX bytes
* LAN TX bytes
* RX dropped packets
* TX dropped packets
* RX errors
* TX errors
* Network utilization

These metrics can be used to identify packet drops, interface errors, or abnormal network utilization.

---

### Exporter Health

Exporter-level metrics include:

```text
omada_cloud_connected
omada_last_success_timestamp_seconds
omada_client_api_up
```

`omada_cloud_connected` indicates whether the exporter can successfully communicate with Omada Cloud.

The exporter also keeps the last known Prometheus values when temporary network/API failures occur instead of immediately replacing them with zero values.

---

## Project Structure

```text
omada-monitoring/
│
├── .env
├── docker-compose.yml
│
├── omada-cloud-exporter/
│   ├── app.py
│   ├── Dockerfile
│   └── requirements.txt
│
└── prometheus/
    └── prometheus.yml
```

---

## Requirements

### Software

* Docker
* Docker Compose
* TP-Link Omada Cloud account
* Omada Cloud Controller
* Omada Site
* Access Point MAC addresses

The exporter itself uses:

* Python
* Flask
* Requests
* Prometheus Client
* Playwright `1.62.0`

The Docker image is based on the official Microsoft Playwright Python image:

```text
mcr.microsoft.com/playwright/python:v1.62.0-noble
```

Chromium is therefore available for the Playwright-based Omada Cloud login process.

---

# Configuration

Create a `.env` file in the project root.

```env
OMADA_EMAIL=your-omada-email
OMADA_PASSWORD=your-omada-password

OMADA_CONTROLLER_ID=your-controller-id
OMADA_SITE_ID=your-site-id

OMADA_API=https://aps1-api-omada-essential-controller.tplinkcloud.com

EAP225_MAC=AA:BB:CC:DD:EE:FF
EAP723_MAC=11:22:33:44:55:66

UPDATE_INTERVAL=30
LOGIN_RETRY_INTERVAL=60
```

The exporter reads the Omada credentials, controller ID, site ID, API endpoint, AP MAC addresses, update interval, and login retry interval from environment variables.

### Environment Variables

| Variable                | Description                        |                                                       Default |
| ----------------------- | ---------------------------------- | ------------------------------------------------------------: |
| `OMADA_EMAIL`           | Omada Cloud email address          |                                                             — |
| `OMADA_PASSWORD`        | Omada Cloud password               |                                                             — |
| `OMADA_CONTROLLER_ID`   | Omada controller ID                |                                                             — |
| `OMADA_SITE_ID`         | Omada site ID                      |                                                             — |
| `OMADA_API`             | Omada Cloud API endpoint           | `https://aps1-api-omada-essential-controller.tplinkcloud.com` |
| `EAP225_MAC`            | MAC address of the EAP225          |                                                             — |
| `EAP723_MAC`            | MAC address of the EAP723          |                                                             — |
| `UPDATE_INTERVAL`       | Metrics update interval in seconds |                                                          `30` |
| `LOGIN_RETRY_INTERVAL`  | Login retry interval in seconds    |                                                          `60` |
| `OMADA_CLIENT_API_HOST` | Optional client API host override  |                                          Value of `OMADA_API` |

> **Important:** Never commit `.env` to GitHub. Add `.env` to `.gitignore`.

Example:

```gitignore
.env
```

---

# Running with Docker Compose

From the project directory:

```powershell
docker compose up -d --build
```

Check the containers:

```powershell
docker compose ps
```

Expected services:

```text
omada-cloud-exporter
prometheus
grafana
```

The Compose configuration uses persistent Docker volumes for Prometheus and Grafana data.

---

## Check Container Logs

Exporter:

```powershell
docker compose logs -f omada-cloud-exporter
```

Prometheus:

```powershell
docker compose logs -f prometheus
```

Grafana:

```powershell
docker compose logs -f grafana
```

---

# Endpoints

After starting the stack:

| Service            | URL                           |
| ------------------ | ----------------------------- |
| Omada Exporter     | http://localhost:9202         |
| Prometheus Metrics | http://localhost:9202/metrics |
| Prometheus         | http://localhost:9090         |
| Grafana            | http://localhost:3000         |

## The Flask application listens on `0.0.0.0:9202` and exposes `/metrics` for Prometheus scraping.

# Verify the Exporter

Open:

```text
http://localhost:9202/
```

A successful exporter response looks similar to:

```json
{
  "status": "running",
  "logged_in": true,
  "cloud_connected": true,
  "last_success_timestamp": 1788950000,
  "devices": [
    "EAP225",
    "EAP723"
  ]
}
```

You can also check the Prometheus endpoint:

```text
http://localhost:9202/metrics
```

Example:

```text
omada_ap_up
omada_ap_cpu_percent
omada_ap_memory_percent
omada_ap_uptime_seconds
omada_ap_client_count
omada_ap_client_2g
omada_ap_client_5g
omada_wifi_tx_util_percent
omada_wifi_rx_util_percent
omada_wifi_interference_percent
omada_wifi_channel
omada_wifi_tx_power_dbm
```

---

# Prometheus

The included Prometheus configuration uses a `30s` scrape interval:

```yaml
global:
  scrape_interval: 30s

scrape_configs:
  - job_name: "omada-cloud"
    static_configs:
      - targets:
          - "omada-cloud-exporter:9202"
```

Because Prometheus runs in the same Docker Compose network, the exporter is referenced using its Docker service name:

```text
omada-cloud-exporter:9202
```

---

# Grafana

Open:

```text
http://localhost:3000
```

Add Prometheus as a Grafana data source:

```text
http://prometheus:9090
```

Do not use:

```text
http://localhost:9090
```

when configuring the Prometheus data source from inside the Grafana container.

---

# Example PromQL Queries

## AP Availability

```promql
omada_ap_up
```

Only connected APs:

```promql
omada_ap_up == 1
```

Disconnected APs:

```promql
omada_ap_up == 0
```

---

## AP CPU Usage

```promql
omada_ap_cpu_percent
```

Average CPU usage:

```promql
avg(omada_ap_cpu_percent)
```

---

## AP Memory Usage

```promql
omada_ap_memory_percent
```

---

## Connected Clients

Total clients per AP:

```promql
omada_ap_client_count
```

2.4 GHz:

```promql
omada_ap_client_2g
```

5 GHz:

```promql
omada_ap_client_5g
```

---

## Wi-Fi TX Utilization

2.4 GHz:

```promql
omada_wifi_tx_util_percent{band="2g"}
```

5 GHz:

```promql
omada_wifi_tx_util_percent{band="5g"}
```

---

## Wi-Fi RX Utilization

```promql
omada_wifi_rx_util_percent
```

---

## Wi-Fi Interference

```promql
omada_wifi_interference_percent
```

---

## Wi-Fi Channel

```promql
omada_wifi_channel
```

---

## Wi-Fi TX Power

```promql
omada_wifi_tx_power_dbm
```

---

## Channel Width

```promql
omada_wifi_channel_width_mhz
```

---

## Maximum TX Rate

```promql
omada_wifi_max_tx_rate_mbps
```

---

## Cloud Connection

```promql
omada_cloud_connected
```

Expected values:

```text
1 = Connected
0 = Disconnected
```

---

# Troubleshooting

## Exporter container keeps restarting

Check the logs:

```powershell
docker compose logs -f omada-cloud-exporter
```

Look for:

```text
[LOGIN]
[LOGIN ERROR]
[API]
[CLIENT API]
[STATUS API]
[CLOUD]
```

---

## Omada login failed

Verify:

```env
OMADA_EMAIL=...
OMADA_PASSWORD=...
```

The exporter uses Playwright to open Omada Cloud, enter the credentials, and establish the authenticated browser session.

After login, the exporter validates the controller session and retrieves the CSRF token used by subsequent API requests.

---

## Cloud shows disconnected

Check:

```text
http://localhost:9202/
```

and:

```text
http://localhost:9202/metrics
```

Look at:

```promql
omada_cloud_connected
```

A value of:

```text
1
```

means the exporter is connected.

A value of:

```text
0
```

means the exporter currently considers the Omada Cloud connection unavailable.

---

## Prometheus cannot scrape the exporter

Check:

```text
http://localhost:9090/targets
```

The target should be:

```text
omada-cloud-exporter:9202
```

It should show:

```text
UP
```

You can also test the exporter from the host:

```powershell
curl http://localhost:9202/metrics
```

---

## AP shows disconnected even though the API request succeeds

The exporter deliberately does not treat HTTP `200` as proof that an AP is connected.

It queries Omada's device status endpoint and evaluates the actual Omada device status.

The current implementation uses:

```text
14 = Connected
```

Other Omada status values are treated as not connected.

---

# Data Persistence

The Docker Compose configuration creates two named volumes:

```text
prometheus-data
grafana-data
```

Prometheus data is stored in:

```text
/prometheus
```

Grafana data is stored in:

```text
/var/lib/grafana
```

This allows Prometheus historical data and Grafana configuration to survive container recreation.

---

# Updating the Project

Pull the latest source code:

```powershell
git pull
```

Rebuild the exporter:

```powershell
docker compose up -d --build
```

Check the status:

```powershell
docker compose ps
```

---

# Stop the Monitoring Stack

Stop containers:

```powershell
docker compose down
```

This removes the containers but keeps the named Prometheus and Grafana volumes.

To remove containers **and** stored monitoring data:

```powershell
docker compose down -v
```

> Use `-v` carefully because it deletes the Prometheus and Grafana Docker volumes.

---

# Current Device Configuration

The current exporter configuration defines these AP environment variables:

```text
EAP225_MAC
EAP723_MAC
```

which are mapped internally to:

```text
EAP225
EAP723
```

Additional device types can be added to the exporter configuration if required.

---

# Technology Stack

| Component            | Technology        |
| -------------------- | ----------------- |
| Exporter             | Python            |
| Web server           | Flask             |
| Omada authentication | Playwright        |
| HTTP/API             | Requests          |
| Metrics              | Prometheus Client |
| Metrics storage      | Prometheus        |
| Visualization        | Grafana           |
| Containerization     | Docker            |
| Orchestration        | Docker Compose    |

---

# Disclaimer

This project is an independent monitoring/exporter implementation and is not affiliated with, endorsed by, or officially supported by TP-Link or Omada.

Omada Cloud APIs and web interfaces may change over time. API behavior, authentication mechanisms, endpoints, and response formats may therefore require future adjustments.

---

## Contributing

Issues, improvements, and pull requests are welcome.

When reporting a problem, please include:

* Docker version
* Docker Compose version
* Omada Controller type/version
* AP model
* Relevant exporter logs
* Prometheus target status

Please remove passwords, tokens, cookies, and other sensitive information before posting logs publicly.
