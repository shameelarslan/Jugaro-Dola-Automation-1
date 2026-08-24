"""
Network & Connection Status Widget for Main Window Top Header Bar.
Monitors Online/Offline connectivity, Latency (Ping ms), Connection Speed quality, and Public IP + Geographic Location.
Runs asynchronously in a background thread to ensure zero UI lag.
"""

import socket
import time
import json
import urllib.request
from typing import Dict, Any, Optional
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel
from PyQt6.QtCore import QThread, pyqtSignal, Qt

class NetworkMonitorThread(QThread):
    """Background thread periodically measuring latency, online status, and public IP location."""
    status_updated = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_running = True
        self._cached_ip_data = None
        self._last_ip_lookup_time = 0.0

    def stop(self):
        self._is_running = False

    def _measure_ping(self) -> Optional[int]:
        """Measures TCP handshake ping to Cloudflare / Google DNS."""
        hosts = [("1.1.1.1", 53), ("8.8.8.8", 53), ("www.google.com", 80)]
        for host, port in hosts:
            try:
                t0 = time.perf_counter()
                sock = socket.create_connection((host, port), timeout=2.0)
                sock.close()
                ping_ms = int((time.perf_counter() - t0) * 1000)
                return max(1, ping_ms)
            except Exception:
                continue
        return None

    def _fetch_ip_and_location(self) -> Optional[Dict[str, Any]]:
        """Fetches public IP and city/country information with timeout."""
        apis = [
            "http://ip-api.com/json/?fields=status,country,countryCode,city,query",
            "https://ipwho.is/",
            "https://api.ipify.org?format=json"
        ]
        for url in apis:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                with urllib.request.urlopen(req, timeout=3.0) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    if "query" in data and data.get("status") == "success":
                        return {
                            "ip": data.get("query", ""),
                            "city": data.get("city", ""),
                            "country": data.get("country", ""),
                            "country_code": data.get("countryCode", "")
                        }
                    elif "ip" in data:
                        return {
                            "ip": data.get("ip", ""),
                            "city": data.get("city", ""),
                            "country": data.get("country", ""),
                            "country_code": data.get("country_code", "")
                        }
            except Exception:
                continue
        return None

    def run(self):
        while self._is_running:
            ping_ms = self._measure_ping()
            is_online = ping_ms is not None

            # Refresh IP / Location every 3 minutes or if we don't have it yet
            now = time.time()
            if is_online:
                if not self._cached_ip_data or (now - self._last_ip_lookup_time > 180.0):
                    ip_data = self._fetch_ip_and_location()
                    if ip_data:
                        self._cached_ip_data = ip_data
                        self._last_ip_lookup_time = now
            else:
                self._cached_ip_data = None

            # Determine connection speed / quality based on real latency
            speed_tier = "Offline"
            if is_online:
                if ping_ms < 50:
                    speed_tier = "Ultra Fast"
                elif ping_ms < 100:
                    speed_tier = "Fast"
                elif ping_ms < 200:
                    speed_tier = "Good"
                else:
                    speed_tier = "Moderate"

            payload = {
                "online": is_online,
                "ping_ms": ping_ms if is_online else 0,
                "speed_tier": speed_tier,
                "ip_data": self._cached_ip_data
            }

            self.status_updated.emit(payload)

            # Sleep in small increments for fast shutdown
            for _ in range(50):
                if not self._is_running:
                    break
                time.sleep(0.1)


from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QApplication

class NetworkStatusWidget(QFrame):
    """Compact, modern widget displaying Online status, Ping (ms), Speed, and Public IP + Location."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("network_status_card")
        self._init_ui()

        self.thread = NetworkMonitorThread(self)
        self.thread.status_updated.connect(self._on_status_updated)
        self.thread.start()

        app = QApplication.instance()
        if app:
            app.aboutToQuit.connect(self.thread.stop)

    def _init_ui(self):
        self.setStyleSheet("""
            QFrame#network_status_card {
                background-color: #090d16;
                border: 1px solid #1e293b;
                border-radius: 8px;
                padding: 2px 10px;
            }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(12)

        # 1. Online / Offline Indicator Badge
        self.lbl_status = QLabel("● Checking...")
        self.lbl_status.setStyleSheet("color: #94a3b8; font-weight: bold; font-size: 11px;")
        layout.addWidget(self.lbl_status)

        # Separator
        layout.addWidget(self._make_separator())

        # 2. Latency / Ping (ms)
        self.lbl_ping = QLabel("⚡ -- ms")
        self.lbl_ping.setStyleSheet("color: #38bdf8; font-weight: 600; font-size: 11px;")
        layout.addWidget(self.lbl_ping)

        # Separator
        layout.addWidget(self._make_separator())

        # 3. Connection Speed / Quality
        self.lbl_speed = QLabel("🚀 --")
        self.lbl_speed.setStyleSheet("color: #a78bfa; font-weight: 600; font-size: 11px;")
        layout.addWidget(self.lbl_speed)

        # Separator
        layout.addWidget(self._make_separator())

        # 4. Public IP & Location
        self.lbl_ip_location = QLabel("🌐 IP: Fetching...")
        self.lbl_ip_location.setStyleSheet("color: #cbd5e1; font-weight: 600; font-size: 11px;")
        layout.addWidget(self.lbl_ip_location)

    def _make_separator(self) -> QLabel:
        sep = QLabel("│")
        sep.setStyleSheet("color: #334155; font-size: 10px; font-weight: bold;")
        return sep

    def _on_status_updated(self, data: dict):
        is_online = data.get("online", False)
        ping_ms = data.get("ping_ms", 0)
        speed = data.get("speed_tier", "--")
        ip_info = data.get("ip_data")

        if is_online:
            self.lbl_status.setText("● Online")
            self.lbl_status.setStyleSheet("color: #10b981; font-weight: bold; font-size: 11px;")

            # Color-code ping
            if ping_ms < 75:
                ping_color = "#10b981"
            elif ping_ms < 160:
                ping_color = "#f59e0b"
            else:
                ping_color = "#f43f5e"

            self.lbl_ping.setText(f"⚡ {ping_ms} ms")
            self.lbl_ping.setStyleSheet(f"color: {ping_color}; font-weight: 600; font-size: 11px;")

            self.lbl_speed.setText(f"🚀 {speed}")
            self.lbl_speed.setStyleSheet("color: #a78bfa; font-weight: 600; font-size: 11px;")

            if ip_info:
                ip = ip_info.get("ip", "")
                city = ip_info.get("city", "")
                cc = ip_info.get("country_code", "")
                loc_str = f"{city}, {cc}" if city and cc else (city or cc or "")
                if loc_str:
                    self.lbl_ip_location.setText(f"🌐 {ip} ({loc_str})")
                else:
                    self.lbl_ip_location.setText(f"🌐 {ip}")
            else:
                self.lbl_ip_location.setText("🌐 IP: Connected")
        else:
            self.lbl_status.setText("○ Offline")
            self.lbl_status.setStyleSheet("color: #ef4444; font-weight: bold; font-size: 11px;")

            self.lbl_ping.setText("⚡ -- ms")
            self.lbl_ping.setStyleSheet("color: #64748b; font-weight: 600; font-size: 11px;")

            self.lbl_speed.setText("🚀 Disconnected")
            self.lbl_speed.setStyleSheet("color: #64748b; font-weight: 600; font-size: 11px;")

            self.lbl_ip_location.setText("🌐 No Internet")
            self.lbl_ip_location.setStyleSheet("color: #ef4444; font-weight: 600; font-size: 11px;")

    def closeEvent(self, event):
        self.thread.stop()
        self.thread.wait(500)
        super().closeEvent(event)
