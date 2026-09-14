import os
import time
import threading
import requests

from flask import Flask
from playwright.sync_api import sync_playwright
from prometheus_client import (
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST
)


# ============================================================
# FLASK
# ============================================================

app = Flask(__name__)


# ============================================================
# CONFIG
# ============================================================

OMADA_EMAIL = os.getenv("OMADA_EMAIL")
OMADA_PASSWORD = os.getenv("OMADA_PASSWORD")

CONTROLLER_ID = os.getenv("OMADA_CONTROLLER_ID")
SITE_ID = os.getenv("OMADA_SITE_ID")

OMADA_API = os.getenv(
    "OMADA_API",
    "https://aps1-api-omada-essential-controller.tplinkcloud.com"
)

DEVICES = {
    "EAP225": os.getenv("EAP225_MAC"),
    "EAP723": os.getenv("EAP723_MAC")
}

UPDATE_INTERVAL = int(
    os.getenv("UPDATE_INTERVAL", "30")
)

LOGIN_RETRY_INTERVAL = int(
    os.getenv("LOGIN_RETRY_INTERVAL", "60")
)


# ============================================================
# PROMETHEUS METRICS
# ============================================================

ap_up = Gauge(
    "omada_ap_up",
    "AP connection status. 1=Connected, 0=Not Connected",
    ["name", "mac", "model"]
)

ap_status = Gauge(
    "omada_ap_status",
    "Omada AP device status code",
    ["name", "mac", "model"]
)

ap_cpu = Gauge(
    "omada_ap_cpu_percent",
    "AP CPU utilization percentage",
    ["name", "mac", "model"]
)

ap_memory = Gauge(
    "omada_ap_memory_percent",
    "AP memory utilization percentage",
    ["name", "mac", "model"]
)

ap_uptime = Gauge(
    "omada_ap_uptime_seconds",
    "AP uptime in seconds",
    ["name", "mac", "model"]
)

ap_rx_rate = Gauge(
    "omada_ap_rx_rate_bytes",
    "AP RX rate",
    ["name", "mac", "model"]
)

ap_tx_rate = Gauge(
    "omada_ap_tx_rate_bytes",
    "AP TX rate",
    ["name", "mac", "model"]
)

# ============================================================
# DEVICE INFORMATION / NETWORK HEALTH METRICS
# ============================================================

ap_info = Gauge(
    "omada_ap_info",
    "AP device information",
    ["name", "mac", "model", "ip", "public_ip", "firmware"]
)

ap_last_seen = Gauge(
    "omada_ap_last_seen_timestamp_seconds",
    "AP last seen timestamp in Unix seconds"
    , ["name", "mac", "model"]
)

ap_lan_rx_bytes = Gauge(
    "omada_ap_lan_rx_bytes",
    "AP LAN received bytes",
    ["name", "mac", "model"]
)

ap_lan_tx_bytes = Gauge(
    "omada_ap_lan_tx_bytes",
    "AP LAN transmitted bytes",
    ["name", "mac", "model"]
)

ap_lan_rx_drop_packets = Gauge(
    "omada_ap_lan_rx_drop_packets",
    "AP LAN received dropped packets",
    ["name", "mac", "model"]
)

ap_lan_tx_drop_packets = Gauge(
    "omada_ap_lan_tx_drop_packets",
    "AP LAN transmitted dropped packets",
    ["name", "mac", "model"]
)

ap_lan_rx_errors = Gauge(
    "omada_ap_lan_rx_errors",
    "AP LAN received errors",
    ["name", "mac", "model"]
)

ap_lan_tx_errors = Gauge(
    "omada_ap_lan_tx_errors",
    "AP LAN transmitted errors",
    ["name", "mac", "model"]
)

ap_lan_util = Gauge(
    "omada_ap_lan_util_percent",
    "AP LAN/network utilization percentage",
    ["name", "mac", "model"]
)

ap_ssid_download_bytes = Gauge(
    "omada_ap_ssid_download_bytes",
    "AP SSID download bytes",
    ["name", "mac", "model"]
)

ap_ssid_upload_bytes = Gauge(
    "omada_ap_ssid_upload_bytes",
    "AP SSID upload bytes",
    ["name", "mac", "model"]
)

ap_ssid_download_2g_bytes = Gauge(
    "omada_ap_ssid_download_2g_bytes",
    "AP SSID 2.4 GHz download bytes",
    ["name", "mac", "model"]
)

ap_ssid_upload_2g_bytes = Gauge(
    "omada_ap_ssid_upload_2g_bytes",
    "AP SSID 2.4 GHz upload bytes",
    ["name", "mac", "model"]
)

ap_ssid_download_5g_bytes = Gauge(
    "omada_ap_ssid_download_5g_bytes",
    "AP SSID 5 GHz download bytes",
    ["name", "mac", "model"]
)

ap_ssid_upload_5g_bytes = Gauge(
    "omada_ap_ssid_upload_5g_bytes",
    "AP SSID 5 GHz upload bytes",
    ["name", "mac", "model"]
)

# SSID-level metrics from dashboard/activeSsids
ssid_traffic = Gauge("omada_ssid_traffic", "Total traffic per active SSID", ["ssid"])
ssid_client_count = Gauge("omada_ssid_client_count", "Connected clients per active SSID", ["ssid"])
ssid_traffic_total = Gauge("omada_ssid_traffic_total", "Total traffic across active SSIDs")
ssid_clients_total = Gauge("omada_ssid_clients_total", "Total clients across active SSIDs")

ap_client_timeout = Gauge(
    "omada_ap_client_timeout",
    "AP client connection timeout count",
    ["name", "mac", "model"]
)

ap_client_wpa_fail = Gauge(
    "omada_ap_client_wpa_fail",
    "AP client WPA failure count",
    ["name", "mac", "model"]
)

ap_client_block = Gauge(
    "omada_ap_client_block",
    "AP client block count",
    ["name", "mac", "model"]
)

ap_client_count = Gauge(
    "omada_ap_client_count",
    "Number of connected clients per AP",
    ["name", "mac", "model"]
)

ap_client_2g = Gauge(
    "omada_ap_client_2g",
    "Number of connected 2.4 GHz clients per AP",
    ["name", "mac", "model"]
)

ap_client_5g = Gauge(
    "omada_ap_client_5g",
    "Number of connected 5 GHz clients per AP",
    ["name", "mac", "model"]
)

ap_client_5g2 = Gauge(
    "omada_ap_client_5g2",
    "Number of connected secondary 5 GHz clients per AP",
    ["name", "mac", "model"]
)

ap_client_6g = Gauge(
    "omada_ap_client_6g",
    "Number of connected 6 GHz clients per AP",
    ["name", "mac", "model"]
)


# ============================================================
# WIFI METRICS
# ============================================================

wifi_tx_util = Gauge(
    "omada_wifi_tx_util_percent",
    "WiFi TX utilization percentage",
    ["name", "mac", "band"]
)

wifi_rx_util = Gauge(
    "omada_wifi_rx_util_percent",
    "WiFi RX utilization percentage",
    ["name", "mac", "band"]
)

wifi_interference = Gauge(
    "omada_wifi_interference_percent",
    "WiFi interference percentage",
    ["name", "mac", "band"]
)

wifi_channel = Gauge(
    "omada_wifi_channel",
    "WiFi channel",
    ["name", "mac", "band"]
)

wifi_tx_power = Gauge(
    "omada_wifi_tx_power_dbm",
    "WiFi TX power",
    ["name", "mac", "band"]
)

wifi_frequency_mhz = Gauge(
    "omada_wifi_frequency_mhz",
    "WiFi center frequency in MHz",
    ["name", "mac", "band"]
)

wifi_channel_width_mhz = Gauge(
    "omada_wifi_channel_width_mhz",
    "WiFi channel width in MHz",
    ["name", "mac", "band"]
)

wifi_max_tx_rate_mbps = Gauge(
    "omada_wifi_max_tx_rate_mbps",
    "WiFi maximum TX rate in Mbps",
    ["name", "mac", "band"]
)


# ============================================================
# CLOUD / EXPORTER STATUS METRICS
# ============================================================

omada_cloud_connected = Gauge(
    "omada_cloud_connected",
    "Omada Cloud API connection status. 1=connected, 0=disconnected"
)

omada_last_success_timestamp = Gauge(
    "omada_last_success_timestamp_seconds",
    "Unix timestamp of last successful Omada API update"
)

omada_device_last_success = Gauge(
    "omada_device_last_success_timestamp_seconds",
    "Unix timestamp of last successful device update",
    ["name", "mac", "model"]
)


# ============================================================
# SESSION / STATE
# ============================================================

session = requests.Session()

login_lock = threading.Lock()

logged_in = False

cloud_connected = False

last_success_time = 0

# Persistent Playwright session.
# The Omada OpenAPI /clients endpoint may reject a plain requests.Session
# even though the authenticated browser session is valid, so keep the
# authenticated browser context alive and call the endpoint from the page.
playwright_instance = None
browser_instance = None
browser_context = None
browser_page = None


def metric_number(data, key, default=0):
    """Safely convert an Omada numeric field to float."""
    try:
        if not isinstance(data, dict):
            return float(default)
        value = data.get(key, default)
        return float(value if value is not None else default)
    except (TypeError, ValueError):
        return float(default)


# ============================================================
# LOGIN OMADA CLOUD
# ============================================================

def login_omada():

    global logged_in
    global cloud_connected
    global playwright_instance
    global browser_instance
    global browser_context
    global browser_page

    print(
        "[LOGIN] Starting Omada Cloud login...",
        flush=True
    )

    with login_lock:

        try:

            print(
                "[LOGIN] Starting Playwright...",
                flush=True
            )

            # Close an old browser session if one exists.
            if browser_page is not None:
                try:
                    browser_page.close()
                except Exception:
                    pass

            if browser_context is not None:
                try:
                    browser_context.close()
                except Exception:
                    pass

            if browser_instance is not None:
                try:
                    browser_instance.close()
                except Exception:
                    pass

            if playwright_instance is not None:
                try:
                    playwright_instance.stop()
                except Exception:
                    pass

            playwright_instance = sync_playwright().start()

            print(
                "[LOGIN] Launching Chromium...",
                flush=True
            )

            browser_instance = playwright_instance.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage"
                ]
            )

            print(
                "[LOGIN] Creating context...",
                flush=True
            )

            browser_context = browser_instance.new_context()
            browser_page = browser_context.new_page()

            print(
                "[LOGIN] Opening Omada...",
                flush=True
            )

            browser_page.goto(
                "https://omada.tplinkcloud.com/",
                wait_until="domcontentloaded",
                timeout=60000
            )

            print(
                "[LOGIN] Page loaded:",
                browser_page.url,
                flush=True
            )

            browser_page.wait_for_timeout(5000)

            # ====================================================
            # EMAIL
            # ====================================================

            print(
                "[LOGIN] Looking for email input...",
                flush=True
            )

            email_input = browser_page.locator(
                'input[placeholder="Email"]:visible'
            )

            if email_input.count() == 0:
                email_input = browser_page.locator(
                    'input[type="text"]:visible'
                )

            if email_input.count() == 0:
                raise Exception("Email input not found")

            email_input.first.fill(OMADA_EMAIL)

            print(
                "[LOGIN] Email entered",
                flush=True
            )

            # ====================================================
            # PASSWORD
            # ====================================================

            print(
                "[LOGIN] Looking for password input...",
                flush=True
            )

            password_input = browser_page.locator(
                'input[type="password"]:visible'
            )

            if password_input.count() == 0:
                raise Exception("Password input not found")

            password_input.first.fill(OMADA_PASSWORD)

            print(
                "[LOGIN] Password entered",
                flush=True
            )

            # ====================================================
            # FIND SIGN IN BUTTON
            # ====================================================

            print(
                "[LOGIN] Looking for Sign In button...",
                flush=True
            )

            submit_button = browser_page.locator(
                'a.s-button-primary:visible'
            )

            if submit_button.count() == 0:
                submit_button = browser_page.locator(
                    'button:has-text("Sign In"):visible, '
                    'a:has-text("Sign In"):visible'
                )

            if submit_button.count() == 0:
                raise Exception("Sign In button not found")

            selected_button = None

            for i in range(submit_button.count()):
                try:
                    candidate = submit_button.nth(i)

                    if candidate.is_visible():
                        selected_button = candidate

                        print(
                            "[LOGIN] Using Sign In element:",
                            i,
                            flush=True
                        )

                        break

                except Exception:
                    pass

            if selected_button is None:
                raise Exception("No visible Sign In button")

            # ====================================================
            # CLICK SIGN IN
            # ====================================================

            print(
                "[LOGIN] Clicking Sign In...",
                flush=True
            )

            selected_button.click(timeout=30000)

            # ====================================================
            # WAIT AFTER LOGIN
            # ====================================================

            print(
                "[LOGIN] Waiting after Sign In...",
                flush=True
            )

            try:
                browser_page.wait_for_url(
                    lambda url:
                    "id.tplinkcloud.com" not in url,
                    timeout=30000
                )

            except Exception as e:
                print(
                    "[LOGIN] Redirect wait:",
                    repr(e),
                    flush=True
                )

            browser_page.wait_for_timeout(5000)

            print(
                "[LOGIN] URL after login:",
                browser_page.url,
                flush=True
            )

            # ====================================================
            # COPY COOKIES TO REQUESTS SESSION
            # ====================================================

            cookies = browser_context.cookies()

            print(
                "[LOGIN] Cookies found:",
                len(cookies),
                flush=True
            )

            for cookie in cookies:

                print(
                    "[COOKIE]",
                    cookie["name"],
                    cookie["domain"],
                    flush=True
                )

                session.cookies.set(
                    cookie["name"],
                    cookie["value"],
                    domain=cookie.get("domain")
                )

            # ====================================================
            # TEST API SESSION
            # ====================================================

            print(
                "[LOGIN] Testing controller session...",
                flush=True
            )

            url = (
                f"{OMADA_API}/"
                f"{CONTROLLER_ID}/api/v2/"
                f"current/login-status?needToken=true"
            )

            response = session.get(
                url,
                timeout=30
            )

            print(
                "[LOGIN TEST] HTTP:",
                response.status_code,
                flush=True
            )

            print(
                "[LOGIN TEST] Response:",
                response.text[:1000],
                flush=True
            )

            response.raise_for_status()

            data = response.json()

            if (
                data.get("errorCode") == 0
                and data.get(
                    "result",
                    {}
                ).get("login") is True
            ):

                token = data.get(
                    "result",
                    {}
                ).get(
                    "csrfToken"
                )

                if token:

                    session.headers.update(
                        {
                            "Csrf-Token": token
                        }
                    )

                    print(
                        f"[LOGIN] CSRF Token set: "
                        f"{token[:8]}...",
                        flush=True
                    )

                print(
                    "[LOGIN] SUCCESS - persistent browser session ready",
                    flush=True
                )

                logged_in = True
                cloud_connected = True
                omada_cloud_connected.set(1)

                return True

            raise Exception(
                "Login session validation failed"
            )

        except Exception as e:

            print(
                "[LOGIN ERROR]",
                repr(e),
                flush=True
            )

            logged_in = False
            cloud_connected = False
            omada_cloud_connected.set(0)

            # Clean up failed browser session.
            try:
                if browser_page is not None:
                    browser_page.close()
            except Exception:
                pass

            try:
                if browser_context is not None:
                    browser_context.close()
            except Exception:
                pass

            try:
                if browser_instance is not None:
                    browser_instance.close()
            except Exception:
                pass

            try:
                if playwright_instance is not None:
                    playwright_instance.stop()
            except Exception:
                pass

            browser_page = None
            browser_context = None
            browser_instance = None
            playwright_instance = None

            return False


# ============================================================
# GET DEVICE DATA
# ============================================================

def get_device(mac):

    global logged_in

    url = (
        f"{OMADA_API}/"
        f"{CONTROLLER_ID}/api/v2/"
        f"sites/{SITE_ID}/"
        f"eaps/{mac}"
    )

    response = session.get(
        url,
        timeout=30
    )

    print(
        "[API]",
        response.status_code,
        mac,
        flush=True
    )

    if response.status_code in [401, 403]:

        logged_in = False

        raise Exception(
            "Session expired"
        )

    response.raise_for_status()

    data = response.json()

    if data.get("errorCode") != 0:

        raise Exception(
            str(data)
        )

    return data["result"]


# ============================================================
# DEVICE STATUS API
# ============================================================

# Omada's grid/devices endpoint reports the actual controller device
# state. This is different from HTTP 200, which only means the API
# request itself succeeded.
DEVICE_CONNECTED_STATUS = 14


def get_device_statuses():
    """
    Get the real AP status from Omada's grid/devices endpoint.

    The endpoint used by the Omada web UI is:
        GET /{controller}/api/v2/sites/{site}/grid/devices
            ?currentPage=1&currentPageSize=10&asyncColumns=client

    Returns:
        {normalized_mac: status_code}

    Example:
        14 -> Connected
        other values -> Pending / Disconnected / other Omada state
    """

    url = (
        f"{OMADA_API}/"
        f"{CONTROLLER_ID}/api/v2/"
        f"sites/{SITE_ID}/grid/devices"
    )

    params = {
        "currentPage": 1,
        "currentPageSize": 10,
        "asyncColumns": "client"
    }

    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Content-Type": "application/json; charset=UTF-8",
        "Referer": "https://aps1-omada-cloud.tplinkcloud.com/",
        "Request-Config": (
            "%7B%22isSuRequest%22%3Atrue%2C%22preventDefaultFail%22%3Afalse%2C"
            "%22preventDefaultMask%22%3Afalse%2C%22data%22%3A%7B"
            "%22currentPage%22%3A1%2C%22currentPageSize%22%3A10%2C"
            "%22asyncColumns%22%3A%22client%22%7D%7D"
        ),
        "Request-Hash": "#devices",
        "X-Requested-With": "XMLHttpRequest"
    }

    csrf_token = session.headers.get("Csrf-Token", "")
    if csrf_token:
        headers["Csrf-Token"] = csrf_token

    response = session.get(
        url,
        params=params,
        headers=headers,
        timeout=30
    )

    print(
        f"[STATUS API] HTTP {response.status_code}",
        flush=True
    )

    if response.status_code in [401, 403]:
        global logged_in
        logged_in = False
        raise Exception(
            f"Device status API authentication rejected: HTTP {response.status_code}"
        )

    response.raise_for_status()
    payload = response.json()

    if payload.get("errorCode") != 0:
        raise Exception(str(payload))

    result = payload.get("result") or {}

    if isinstance(result, list):
        rows = result
    elif isinstance(result, dict):
        rows = result.get("data") or result.get("rows") or []
    else:
        rows = []

    statuses = {}

    for row in rows:
        if not isinstance(row, dict):
            continue

        row_mac = normalize_mac(
            row.get("mac") or row.get("deviceMac")
        )

        if not row_mac:
            continue

        status = row.get("status")
        if status is None:
            continue

        try:
            status = int(status)
        except (TypeError, ValueError):
            continue

        statuses[row_mac] = status

        print(
            f"[STATUS API] {row.get('name', row_mac)} "
            f"mac={row_mac} status={status} "
            f"connected={1 if status == DEVICE_CONNECTED_STATUS else 0}",
            flush=True
        )

    return statuses


# ============================================================
# ACTIVE SSID API
# ============================================================

def get_active_ssids():
    """Fetch SSID traffic/client totals from Omada dashboard API."""
    global logged_in

    url = (
        f"{OMADA_API}/{CONTROLLER_ID}/api/v2/"
        f"sites/{SITE_ID}/dashboard/activeSsids"
    )
    csrf_token = session.headers.get("Csrf-Token", "")

    headers = {
        "Accept": "application/json, text/plain, */*",
        "X-Requested-With": "XMLHttpRequest",
        "Refresh": "manual",
        "Request-Hash": "#dashboard",
        "Request-Config": "%7B%22responseType%22%3A%22json%22%2C%22method%22%3A%22get%22%7D",
    }
    if csrf_token:
        headers["Csrf-Token"] = csrf_token

    response = session.get(
        url,
        params={"deviceNum": 5},
        headers=headers,
        timeout=30,
    )

    print(f"[SSID API] HTTP {response.status_code}", flush=True)

    if response.status_code in [401, 403]:
        logged_in = False
        raise Exception(f"Active SSID API authentication rejected: HTTP {response.status_code}")

    response.raise_for_status()
    payload = response.json()

    if payload.get("errorCode") != 0:
        raise Exception(str(payload))

    result = payload.get("result") or {}
    traffic_rows = result.get("ssidTraffic") or []
    client_rows = result.get("clientsNum") or []

    # Remove old SSIDs before writing the current set.
    ssid_traffic.clear()
    ssid_client_count.clear()

    for row in traffic_rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "").strip()
        if not name:
            continue
        value = metric_number(row, "traffic")
        ssid_traffic.labels(ssid=name).set(value)
        print(f"[SSID] {name} traffic={value}", flush=True)

    for row in client_rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "").strip()
        if not name:
            continue
        value = metric_number(row, "clients")
        ssid_client_count.labels(ssid=name).set(value)
        print(f"[SSID] {name} clients={value}", flush=True)

    try:
        total_traffic = float(result.get("trafficTotal", 0) or 0)
    except (TypeError, ValueError):
        total_traffic = 0

    try:
        total_clients = float(result.get("clientsTotal", 0) or 0)
    except (TypeError, ValueError):
        total_clients = 0

    ssid_traffic_total.set(total_traffic)
    ssid_clients_total.set(total_clients)

    print(
        f"[SSID API] total traffic={total_traffic} clients={total_clients}",
        flush=True,
    )


# Per-client metrics from the Omada OpenAPI /clients endpoint.
# Identity/context labels are kept limited to avoid unnecessary cardinality.
client_up = Gauge(
    "omada_client_up",
    "Current active Omada client. 1=active",
    ["client_mac", "client_name", "ap_mac", "ap_name", "ssid", "band", "channel", "os", "vendor"]
)

# Snapshot metric intended for a single Grafana Client Details table.
# NOTE: Dynamic client values are labels here for dashboard convenience.
# This is acceptable for the current small deployment, but should not be
# used as a high-cardinality pattern for a large fleet.
client_details = Gauge(
    "omada_client_details",
    "Complete current Omada client details for Grafana table",
    [
        "client_mac",
        "client_name",
        "ap_mac",
        "ap_name",
        "ssid",
        "band",
        "channel",
        "ip",
        "os",
        "vendor",
        "rssi",
        "signal",
        "snr",
        "rx_rate",
        "tx_rate",
        "download",
        "upload",
        "uptime",
    ]
)

client_rssi = Gauge(
    "omada_client_rssi_dbm",
    "Client RSSI in dBm",
    ["client_mac", "ap_mac"]
)

client_signal_level = Gauge(
    "omada_client_signal_level_percent",
    "Client signal level percentage",
    ["client_mac", "ap_mac"]
)

client_snr = Gauge(
    "omada_client_snr_db",
    "Client SNR in dB",
    ["client_mac", "ap_mac"]
)

client_rx_rate = Gauge(
    "omada_client_rx_rate_bits_per_second",
    "Client RX rate in bits per second",
    ["client_mac", "ap_mac"]
)

client_tx_rate = Gauge(
    "omada_client_tx_rate_bits_per_second",
    "Client TX rate in bits per second",
    ["client_mac", "ap_mac"]
)

client_traffic_down = Gauge(
    "omada_client_traffic_down_bytes",
    "Client download traffic in bytes",
    ["client_mac", "ap_mac"]
)

client_traffic_up = Gauge(
    "omada_client_traffic_up_bytes",
    "Client upload traffic in bytes",
    ["client_mac", "ap_mac"]
)

client_uptime = Gauge(
    "omada_client_uptime_seconds",
    "Client connection uptime in seconds",
    ["client_mac", "ap_mac"]
)

# ============================================================
# CLIENT COUNT API
# ============================================================

CLIENT_API_HOST = os.getenv(
    "OMADA_CLIENT_API_HOST",
    OMADA_API
).rstrip("/")

client_api_up = Gauge(
    "omada_client_api_up",
    "Omada client list API status. 1=up, 0=down"
)


def normalize_mac(mac):
    """Normalize MAC so AA-BB-CC, AA:BB:CC and AABBCC all match."""
    return str(mac or "").replace(":", "").replace("-", "").replace(".", "").strip().upper()


def get_all_clients_via_browser():
    """
    Fetch all clients using the authenticated persistent Playwright page.

    IMPORTANT:
    The Omada web UI uses POST /openapi/v2/.../clients with a JSON body.
    It also sends the CSRF token returned by login-status and several
    Omada-specific request headers.  Reproduce that browser request here.
    """

    global logged_in
    global browser_page

    if browser_page is None:
        raise Exception("Persistent browser session is not available")

    url = (
        f"{CLIENT_API_HOST}/openapi/v2/"
        f"{CONTROLLER_ID}/sites/{SITE_ID}/clients"
    )

    # login_omada() stores the current controller CSRF token here.
    csrf_token = session.headers.get("Csrf-Token", "")

    all_clients = []
    page = 1
    page_size = 100
    total_rows = None
    max_pages = 100

    while page <= max_pages:

        print(
            f"[CLIENT API BROWSER] Fetching page={page}",
            flush=True
        )

        result = browser_page.evaluate(
            """
            async ({url, page, pageSize, csrfToken}) => {

                const headers = {
                    "Accept": "application/json, text/plain, */*",
                    "Content-Type": "application/json;charset=UTF-8",
                    "X-Requested-With": "XMLHttpRequest",
                    "Omada-Request-Source": "web-local",
                    "Refresh": "manual",
                    "Request-Hash": "1",
                    "Request-Config":
                        "%7B%22preventSuccess%22%3Atrue%2C%22responseType%22%3A%22json%22%2C%22method%22%3A%22post%22%7D"
                };

                if (csrfToken) {
                    headers["Csrf-Token"] = csrfToken;
                }

                const body = {
                    filters: {
                        active: true
                    },
                    sorts: {},
                    hideHealthUnsupported: true,
                    page: page,
                    pageSize: pageSize,
                    scope: 1
                };

                const response = await fetch(url, {
                    method: "POST",
                    credentials: "include",
                    headers: headers,
                    body: JSON.stringify(body)
                });

                const text = await response.text();

                return {
                    status: response.status,
                    text: text
                };
            }
            """,
            {
                "url": url,
                "page": page,
                "pageSize": page_size,
                "csrfToken": csrf_token
            }
        )

        status = int(result.get("status", 0))
        text = result.get("text", "")

        print(
            f"[CLIENT API BROWSER] HTTP {status} page={page}",
            flush=True
        )

        if status in [401, 403]:
            logged_in = False
            raise Exception(
                f"Client API authentication rejected: HTTP {status}"
            )

        if status < 200 or status >= 300:
            raise Exception(
                f"Client API HTTP {status}: {text[:500]}"
            )

        try:
            payload = __import__("json").loads(text)
        except Exception:
            raise Exception(
                f"Client API returned non-JSON: {text[:500]}"
            )

        if payload.get("errorCode") != 0:
            raise Exception(str(payload))

        result_data = payload.get("result") or {}
        data = result_data.get("data") or []

        if not isinstance(data, list):
            raise Exception(
                f"Unexpected clients data: {data}"
            )

        all_clients.extend(
            item for item in data
            if isinstance(item, dict)
        )

        try:
            total_rows = int(result_data.get("totalRows"))
        except (TypeError, ValueError):
            total_rows = None

        try:
            current_page = int(
                result_data.get("currentPage", page)
            )
        except (TypeError, ValueError):
            current_page = page

        try:
            current_size = int(
                result_data.get("currentSize", len(data))
            )
        except (TypeError, ValueError):
            current_size = len(data)

        print(
            f"[CLIENT API BROWSER] page={current_page} "
            f"rows={len(data)} totalRows={total_rows}",
            flush=True
        )

        if not data:
            break

        if total_rows is not None and len(all_clients) >= total_rows:
            break

        if len(data) < max(current_size, 1):
            break

        page += 1

    if total_rows is not None and len(all_clients) < total_rows:
        raise Exception(
            f"Incomplete client pagination: "
            f"got {len(all_clients)} of {total_rows}"
        )

    return all_clients


def get_all_clients():
    """
    Get all current clients from Omada Cloud OpenAPI.

    Primary method: authenticated persistent Playwright browser.
    A plain requests.Session is deliberately not used here because
    the endpoint can return HTTP 401 despite a valid controller session.
    """

    return get_all_clients_via_browser()


def update_client_metrics(clients):
    """Export detailed metrics for active clients from /clients."""
    client_up.clear()
    client_details.clear()
    client_rssi.clear()
    client_signal_level.clear()
    client_snr.clear()
    client_rx_rate.clear()
    client_tx_rate.clear()
    client_traffic_down.clear()
    client_traffic_up.clear()
    client_uptime.clear()

    exported = 0

    for client in clients:
        if not isinstance(client, dict) or client.get("active") is False:
            continue

        client_mac = normalize_mac(client.get("mac"))
        ap_mac = normalize_mac(client.get("apMac"))
        if not client_mac or not ap_mac:
            continue

        client_name = str(client.get("name") or client_mac)
        ap_name = str(client.get("apName") or ap_mac)
        ssid = str(client.get("ssid") or "")
        ip = str(client.get("ip") or "")
        os_name = str(client.get("osName") or "Unknown")
        vendor = str(client.get("vendor") or "Unknown")

        try:
            channel = int(client.get("channel"))
        except (TypeError, ValueError):
            channel = 0

        if 1 <= channel <= 14:
            band = "2.4G"
        elif channel > 14:
            band = "5G"
        else:
            band = "Unknown"

        identity = {
            "client_mac": client_mac,
            "client_name": client_name,
            "ap_mac": ap_mac,
            "ap_name": ap_name,
            "ssid": ssid,
            "band": band,
            "channel": str(channel),
            "os": os_name,
            "vendor": vendor,
        }
        pair = {"client_mac": client_mac, "ap_mac": ap_mac}

        rssi = metric_number(client, "rssi")
        signal = metric_number(client, "signalLevel")
        snr = metric_number(client, "snr")
        rx_rate = metric_number(client, "rxRate") * 1000
        tx_rate = metric_number(client, "txRate") * 1000
        download = metric_number(client, "trafficDown")
        upload = metric_number(client, "trafficUp")
        uptime = metric_number(client, "uptime")

        client_up.labels(**identity).set(1)
        client_rssi.labels(**pair).set(rssi)
        client_signal_level.labels(**pair).set(signal)
        client_snr.labels(**pair).set(snr)

        # Captured Omada client payload reports rxRate/txRate as Kbps.
        client_rx_rate.labels(**pair).set(rx_rate)
        client_tx_rate.labels(**pair).set(tx_rate)
        client_traffic_down.labels(**pair).set(download)
        client_traffic_up.labels(**pair).set(upload)
        client_uptime.labels(**pair).set(uptime)

        client_details.labels(
            client_mac=client_mac,
            client_name=client_name,
            ap_mac=ap_mac,
            ap_name=ap_name,
            ssid=ssid,
            band=band,
            channel=str(channel),
            ip=ip,
            os=os_name,
            vendor=vendor,
            rssi=str(rssi),
            signal=str(signal),
            snr=str(snr),
            rx_rate=str(rx_rate),
            tx_rate=str(tx_rate),
            download=str(download),
            upload=str(upload),
            uptime=str(uptime),
        ).set(1)

        exported += 1

    print(f"[CLIENT METRICS] Exported active clients: {exported}", flush=True)


def get_client_counts(clients=None):
    """Count current clients per AP from already-fetched /clients data."""
    if clients is None:
        clients = get_all_clients()

    counts = {}

    for client in clients:
        if client.get("active") is False:
            continue

        ap_mac = normalize_mac(client.get("apMac"))
        if not ap_mac:
            continue

        if ap_mac not in counts:
            counts[ap_mac] = {
                "clientNum": 0,
                "clientNum2g": 0,
                "clientNum5g": 0,
                "clientNum5g2": 0,
                "clientNum6g": 0
            }

        counts[ap_mac]["clientNum"] += 1

        try:
            channel = int(client.get("channel"))
        except (TypeError, ValueError):
            channel = 0

        if 1 <= channel <= 14:
            counts[ap_mac]["clientNum2g"] += 1
        elif channel > 14:
            counts[ap_mac]["clientNum5g"] += 1

    for _, configured_mac in DEVICES.items():
        normalized = normalize_mac(configured_mac)
        if normalized and normalized not in counts:
            counts[normalized] = {
                "clientNum": 0,
                "clientNum2g": 0,
                "clientNum5g": 0,
                "clientNum5g2": 0,
                "clientNum6g": 0
            }

    client_api_up.set(1)
    print(f"[CLIENT API] Total clients collected: {len(clients)}", flush=True)

    for mac, values in counts.items():
        print(
            f"[CLIENTS] {mac} total={values['clientNum']} "
            f"2.4GHz={values['clientNum2g']} 5GHz={values['clientNum5g']} "
            f"5GHz-2={values['clientNum5g2']} 6GHz={values['clientNum6g']}",
            flush=True
        )

    return counts


# ============================================================
# UPDATE DEVICE METRICS
# ============================================================

def update_device_metrics(
    device,
    fallback_name,
    mac,
    client_data=None,
    status_data=None
):

    global last_success_time

    name = device.get(
        "name",
        fallback_name
    )

    model = device.get(
        "model",
        "unknown"
    )

    labels = {
        "name": name,
        "mac": mac,
        "model": model
    }


    # ========================================================
    # AP STATUS
    # ========================================================

    # IMPORTANT:
    # HTTP 200 from the API does NOT mean the AP is connected.
    # Use the real Omada device status from grid/devices.
    normalized_mac = normalize_mac(mac)

    device_status = None

    if status_data is not None:
        device_status = status_data.get(normalized_mac)

    # Fallback to the device-detail response if grid/devices did not
    # return this AP. This keeps the exporter resilient if the status
    # endpoint temporarily changes/fails.
    if device_status is None:
        device_status = device.get("status")

    try:
        device_status = int(device_status)
    except (TypeError, ValueError):
        device_status = None

    if device_status is not None:
        connected = 1 if device_status == DEVICE_CONNECTED_STATUS else 0

        ap_status.labels(
            **labels
        ).set(device_status)

        ap_up.labels(
            **labels
        ).set(connected)

        print(
            f"[AP STATUS] {name} ({model}) "
            f"status={device_status} "
            f"connected={connected}",
            flush=True
        )


    # ========================================================
    # CPU
    # ========================================================

    ap_cpu.labels(
        **labels
    ).set(
        device.get(
            "cpuUtil",
            0
        )
    )


    # ========================================================
    # MEMORY
    # ========================================================

    ap_memory.labels(
        **labels
    ).set(
        device.get(
            "memUtil",
            0
        )
    )


    # ========================================================
    # UPTIME
    # ========================================================

    ap_uptime.labels(
        **labels
    ).set(
        device.get(
            "uptimeLong",
            0
        )
    )


    # ========================================================
    # RX RATE
    # ========================================================

    ap_rx_rate.labels(
        **labels
    ).set(
        device.get(
            "rxRate",
            0
        )
    )


    # ========================================================
    # TX RATE
    # ========================================================

    ap_tx_rate.labels(
        **labels
    ).set(
        device.get(
            "txRate",
            0
        )
    )


    # ========================================================
    # CLIENT COUNT
    # ========================================================

    if client_data is not None:
        client_count = client_data.get(
            "clientNum",
            0
        )

        ap_client_count.labels(
            **labels
        ).set(
            client_count
        )

        ap_client_2g.labels(
            **labels
        ).set(
            client_data.get(
                "clientNum2g",
                0
            )
        )

        ap_client_5g.labels(
            **labels
        ).set(
            client_data.get(
                "clientNum5g",
                0
            )
        )

        ap_client_5g2.labels(
            **labels
        ).set(
            client_data.get(
                "clientNum5g2",
                0
            )
        )

        ap_client_6g.labels(
            **labels
        ).set(
            client_data.get(
                "clientNum6g",
                0
            )
        )

        print(
            f"[CLIENTS] {name} ({model}) = {client_count}",
            flush=True
        )


    # ========================================================
    # DEVICE LAST SUCCESS TIME
    # ========================================================

    now = time.time()

    omada_device_last_success.labels(
        **labels
    ).set(now)


    # ========================================================
    # RADIO 2G / 5G
    # ========================================================

    for band, key in [

        ("2g", "wp2g"),
        ("5g", "wp5g")

    ]:

        radio = device.get(
            key,
            {}
        )

        if not radio:

            continue


        radio_labels = {
            "name": name,
            "mac": mac,
            "band": band
        }


        # ====================================================
        # TX UTILIZATION
        # ====================================================

        wifi_tx_util.labels(
            **radio_labels
        ).set(
            radio.get(
                "txUtil",
                0
            )
        )


        # ====================================================
        # RX UTILIZATION
        # ====================================================

        wifi_rx_util.labels(
            **radio_labels
        ).set(
            radio.get(
                "rxUtil",
                0
            )
        )


        # ====================================================
        # INTERFERENCE
        # ====================================================

        wifi_interference.labels(
            **radio_labels
        ).set(
            radio.get(
                "interUtil",
                0
            )
        )


        # ====================================================
        # CHANNEL
        # ====================================================

        channel_text = str(
            radio.get(
                "actualChannel",
                "0"
            )
        )

        try:

            channel = int(
                channel_text.split()[0]
            )

        except Exception:

            channel = 0

        wifi_channel.labels(
            **radio_labels
        ).set(
            channel
        )


        # ====================================================
        # TX POWER
        # ====================================================

        wifi_tx_power.labels(
            **radio_labels
        ).set(
            radio.get(
                "txPower",
                0
            )
        )

        # ====================================================
        # FREQUENCY / CHANNEL WIDTH / MAX TX RATE
        # ====================================================

        channel_text = str(radio.get("actualChannel", ""))
        frequency_mhz = 0
        try:
            if "/" in channel_text:
                freq_text = channel_text.split("/", 1)[1]
                frequency_mhz = float(
                    freq_text.lower().replace("mhz", "").strip()
                )
        except (TypeError, ValueError):
            frequency_mhz = 0

        width_text = str(radio.get("bandWidth", "0"))
        channel_width_mhz = 0
        try:
            channel_width_mhz = float(
                width_text.lower().replace("mhz", "").strip()
            )
        except (TypeError, ValueError):
            channel_width_mhz = 0

        wifi_frequency_mhz.labels(
            **radio_labels
        ).set(frequency_mhz)

        wifi_channel_width_mhz.labels(
            **radio_labels
        ).set(channel_width_mhz)

        try:
            max_tx_rate = float(
                radio.get("maxTxRate", 0) or 0
            )
        except (TypeError, ValueError):
            max_tx_rate = 0

        wifi_max_tx_rate_mbps.labels(
            **radio_labels
        ).set(max_tx_rate)


    # ========================================================
    # DEVICE INFORMATION
    # ========================================================

    ip = str(device.get("ip") or "unknown")
    public_ip = str(device.get("publicIp") or "unknown")
    firmware = str(device.get("firmwareVersion") or "unknown")

    ap_info.labels(
        name=name,
        mac=mac,
        model=model,
        ip=ip,
        public_ip=public_ip,
        firmware=firmware
    ).set(1)

    last_seen = device.get("lastSeen")
    try:
        last_seen = float(last_seen)
        if last_seen > 100000000000:
            last_seen /= 1000.0
        ap_last_seen.labels(**labels).set(last_seen)
    except (TypeError, ValueError):
        pass

    # ========================================================
    # LAN TRAFFIC / NETWORK HEALTH
    # ========================================================

    lan_traffic = device.get("lanTraffic") or {}

    ap_lan_rx_bytes.labels(**labels).set(
        metric_number(lan_traffic, "rx")
    )
    ap_lan_tx_bytes.labels(**labels).set(
        metric_number(lan_traffic, "tx")
    )
    ap_lan_rx_drop_packets.labels(**labels).set(
        metric_number(lan_traffic, "rxDropPkts")
    )
    ap_lan_tx_drop_packets.labels(**labels).set(
        metric_number(lan_traffic, "txDropPkts")
    )
    ap_lan_rx_errors.labels(**labels).set(
        metric_number(lan_traffic, "rxErrPkts")
    )
    ap_lan_tx_errors.labels(**labels).set(
        metric_number(lan_traffic, "txErrPkts")
    )
    ap_lan_util.labels(**labels).set(
        metric_number(lan_traffic, "networkUtil")
    )

    # ========================================================
    # SSID TRAFFIC
    # ========================================================

    # Omada returns SSID traffic inside deviceStatus.ssidTraffic.
    # Do not read device["ssidTraffic"] because that path does not exist.
    device_status_data = device.get("deviceStatus") or {}
    ssid_traffic = device_status_data.get("ssidTraffic") or {}

    ap_ssid_download_bytes.labels(**labels).set(
        metric_number(ssid_traffic, "download")
    )
    ap_ssid_upload_bytes.labels(**labels).set(
        metric_number(ssid_traffic, "upload")
    )
    ap_ssid_download_2g_bytes.labels(**labels).set(
        metric_number(ssid_traffic, "download2g")
    )
    ap_ssid_upload_2g_bytes.labels(**labels).set(
        metric_number(ssid_traffic, "upload2g")
    )
    ap_ssid_download_5g_bytes.labels(**labels).set(
        metric_number(ssid_traffic, "download5g")
    )
    ap_ssid_upload_5g_bytes.labels(**labels).set(
        metric_number(ssid_traffic, "upload5g")
    )

    print(
        f"[SSID TRAFFIC] {name} "
        f"download={metric_number(ssid_traffic, 'download')} "
        f"upload={metric_number(ssid_traffic, 'upload')} "
        f"download2g={metric_number(ssid_traffic, 'download2g')} "
        f"upload2g={metric_number(ssid_traffic, 'upload2g')} "
        f"download5g={metric_number(ssid_traffic, 'download5g')} "
        f"upload5g={metric_number(ssid_traffic, 'upload5g')}",
        flush=True
    )

    # ========================================================
    # CLIENT CONNECTION HEALTH
    # ========================================================

    client_connection = device.get("clientConnection") or {}

    ap_client_timeout.labels(**labels).set(
        metric_number(client_connection, "timeout")
    )
    ap_client_wpa_fail.labels(**labels).set(
        metric_number(client_connection, "wpaFail")
    )
    ap_client_block.labels(**labels).set(
        metric_number(client_connection, "block")
    )

    print(
        f"[OK] {name} ({model}) updated",
        flush=True
    )


# ============================================================
# BACKGROUND LOOP
# ============================================================

def update_metrics():

    global logged_in
    global cloud_connected
    global last_success_time

    while True:

        try:

            # ========================================================
            # LOGIN IF NEEDED
            # ========================================================

            if not logged_in:

                print(
                    "[LOGIN] Login required...",
                    flush=True
                )

                success = login_omada()

                if not success:

                    cloud_connected = False

                    omada_cloud_connected.set(0)

                    print(
                        "[CLOUD] DISCONNECTED - "
                        "Login failed",
                        flush=True
                    )

                    print(
                        f"[LOGIN] Retry in "
                        f"{LOGIN_RETRY_INTERVAL} seconds...",
                        flush=True
                    )

                    time.sleep(
                        LOGIN_RETRY_INTERVAL
                    )

                    continue


            # ========================================================
            # GET CLIENT COUNTS
            # ========================================================

            # ========================================================
            # GET SSID TRAFFIC
            # ========================================================
            try:
                get_active_ssids()
            except Exception as e:
                print(f"[SSID API ERROR] {repr(e)}", flush=True)

            client_counts = {}
            clients = []

            try:
                clients = get_all_clients()
                update_client_metrics(clients)
                client_counts = get_client_counts(clients)

            except requests.exceptions.ConnectionError as e:
                print(
                    f"[CLIENT API NETWORK ERROR] {repr(e)}",
                    flush=True
                )

            except requests.exceptions.Timeout as e:
                print(
                    f"[CLIENT API TIMEOUT] {repr(e)}",
                    flush=True
                )

            except Exception as e:
                client_api_up.set(0)
                print(
                    f"[CLIENT API ERROR] {repr(e)}",
                    flush=True
                )

            # ========================================================
            # GET REAL AP STATUS
            # ========================================================

            device_statuses = {}

            try:
                device_statuses = get_device_statuses()
            except Exception as e:
                print(
                    f"[STATUS API ERROR] {repr(e)}",
                    flush=True
                )
                # Do not mark the AP disconnected just because the
                # status endpoint failed. update_device_metrics() will
                # fall back to the device-detail status if available.

            # ========================================================
            # UPDATE DEVICES
            # ========================================================

            successful_devices = 0

            total_devices = 0


            for fallback_name, mac in DEVICES.items():

                if not mac:

                    print(
                        f"[WARNING] "
                        f"{fallback_name} "
                        f"MAC not configured",
                        flush=True
                    )

                    continue


                total_devices += 1


                try:

                    device = get_device(
                        mac
                    )

                    client_data = client_counts.get(
                        normalize_mac(mac),
                        None
                    )

                    update_device_metrics(
                        device,
                        fallback_name,
                        mac,
                        client_data,
                        device_statuses
                    )

                    successful_devices += 1


                except requests.exceptions.ConnectionError as e:

                    print(
                        f"[NETWORK ERROR] "
                        f"{fallback_name}: "
                        f"{repr(e)}",
                        flush=True
                    )

                    # IMPORTANT:
                    # Keep all existing Prometheus values.
                    # Do not set metrics to zero.

                    logged_in = False


                except requests.exceptions.Timeout as e:

                    print(
                        f"[TIMEOUT] "
                        f"{fallback_name}: "
                        f"{repr(e)}",
                        flush=True
                    )

                    # Keep last known values

                    logged_in = False


                except requests.exceptions.RequestException as e:

                    print(
                        f"[REQUEST ERROR] "
                        f"{fallback_name}: "
                        f"{repr(e)}",
                        flush=True
                    )

                    # Keep last known values

                    logged_in = False


                except Exception as e:

                    print(
                        f"[ERROR] "
                        f"{fallback_name}: "
                        f"{repr(e)}",
                        flush=True
                    )

                    # Keep last known values

                    logged_in = False


            # ========================================================
            # CLOUD CONNECTION STATUS
            # ========================================================

            if (
                total_devices > 0
                and successful_devices == total_devices
            ):

                cloud_connected = True

                last_success_time = time.time()

                omada_cloud_connected.set(1)

                omada_last_success_timestamp.set(
                    last_success_time
                )

                print(
                    f"[CLOUD] CONNECTED - "
                    f"{successful_devices}/"
                    f"{total_devices} "
                    f"devices updated",
                    flush=True
                )


            elif successful_devices > 0:

                # Partial success:
                # Cloud is reachable, but not all devices
                # returned successfully.

                cloud_connected = True

                last_success_time = time.time()

                omada_cloud_connected.set(1)

                omada_last_success_timestamp.set(
                    last_success_time
                )

                print(
                    f"[CLOUD] PARTIAL - "
                    f"{successful_devices}/"
                    f"{total_devices} "
                    f"devices updated",
                    flush=True
                )


            else:

                cloud_connected = False

                omada_cloud_connected.set(0)

                print(
                    "[CLOUD] DISCONNECTED - "
                    "Keeping last known metrics",
                    flush=True
                )


            # ========================================================
            # WAIT
            # ========================================================

            print(
                f"[UPDATE] Waiting "
                f"{UPDATE_INTERVAL} seconds...",
                flush=True
            )

            time.sleep(
                UPDATE_INTERVAL
            )


        except requests.exceptions.ConnectionError as e:

            cloud_connected = False

            logged_in = False

            omada_cloud_connected.set(0)

            print(
                "[NETWORK ERROR]",
                repr(e),
                flush=True
            )

            print(
                "[STATUS] Keeping last known metrics",
                flush=True
            )

            time.sleep(
                UPDATE_INTERVAL
            )


        except requests.exceptions.Timeout as e:

            cloud_connected = False

            logged_in = False

            omada_cloud_connected.set(0)

            print(
                "[TIMEOUT]",
                repr(e),
                flush=True
            )

            print(
                "[STATUS] Keeping last known metrics",
                flush=True
            )

            time.sleep(
                UPDATE_INTERVAL
            )


        except Exception as e:

            cloud_connected = False

            omada_cloud_connected.set(0)

            print(
                "[LOOP ERROR]",
                repr(e),
                flush=True
            )

            print(
                "[STATUS] Keeping last known metrics",
                flush=True
            )

            time.sleep(
                UPDATE_INTERVAL
            )


# ============================================================
# FLASK
# ============================================================

@app.route("/metrics")
def metrics():

    return (
        generate_latest(),
        200,
        {
            "Content-Type":
                CONTENT_TYPE_LATEST
        }
    )


@app.route("/")
def home():

    return {

        "status": "running",

        "logged_in": logged_in,

        "cloud_connected": cloud_connected,

        "last_success_timestamp": last_success_time,

        "devices": list(
            DEVICES.keys()
        )
    }


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    print(
        "[START] Omada Cloud Exporter starting...",
        flush=True
    )

    print(
        "[CONFIG] Controller:",
        CONTROLLER_ID,
        flush=True
    )

    print(
        "[CONFIG] Site:",
        SITE_ID,
        flush=True
    )

    print(
        "[CONFIG] Devices:",
        DEVICES,
        flush=True
    )

    print(
        "[CONFIG] Update interval:",
        UPDATE_INTERVAL,
        "seconds",
        flush=True
    )


    # ========================================================
    # INITIAL STATUS
    # ========================================================

    omada_cloud_connected.set(0)


    # ========================================================
    # START BACKGROUND THREAD
    # ========================================================

    thread = threading.Thread(
        target=update_metrics,
        daemon=True
    )

    thread.start()


    # ========================================================
    # START FLASK
    # ========================================================

    app.run(
        host="0.0.0.0",
        port=9202
    )
