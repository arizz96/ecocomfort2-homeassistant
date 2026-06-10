#!/usr/bin/env python3
"""
ECOCOMFORT 2 Mock Server - Local Cloud Replacement

This server mimics the Fantini Cosmi cloud API to allow local-only device operation.
Based on reverse engineering of the ECOCOMFORT 2 firmware.

Usage:
    python3 ecocomfort2_mock_server.py [--port 8080] [--host 0.0.0.0] [--verbose]

Device redirection:
    Via UART shell: Set wifi conf <SSID> <PSK> <SERVER_IP> 8080 60
    Via DNS spoofing: Point api.fantinicosmispa.com to this server
"""

import socket
import struct
import threading
import time
import json
import logging
import argparse
from datetime import datetime
from typing import Dict, Tuple, Optional
from dataclasses import dataclass, asdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class DeviceStatus:
    """Device state representation"""
    device_id: str = "ecocomfort_device"
    firmware_version: str = "0.6.8"
    mac_address: str = "AA:BB:CC:DD:EE:FF"
    online: bool = False

    # Environmental sensors
    temperature: float = 20.0
    humidity: float = 50.0
    voc: int = 500  # ppb
    ambient_light: int = 100  # lux

    # Fan state
    fan_speed: int = 0  # 0-5 levels
    fan_mode: str = "OFF"  # OFF, MANUAL, AUTO

    # Network
    wifi_ssid: str = ""
    signal_strength: int = -50  # dBm
    ip_address: str = ""

    # Timestamps
    last_seen: float = 0
    last_update: float = 0
    uptime_seconds: int = 0


class ECOCOMFORTMockServer:
    """Mock server for ECOCOMFORT 2 device communication"""

    # Protocol constants (from firmware analysis)
    PROTOCOL_MAGIC = 0xFEED  # Hypothesized protocol magic
    PACKET_HEADER_SIZE = 8
    MAX_PAYLOAD_SIZE = 1024
    KEEPALIVE_INTERVAL = 30  # seconds

    # Command types (client to server)
    CMD_DEVICE_INFO = 0x01
    CMD_SENSOR_DATA = 0x02
    CMD_STATUS_REPORT = 0x03
    CMD_PING = 0x04
    CMD_ACK = 0x05

    # Response types (server to client)
    RSP_OK = 0x80
    RSP_COMMAND = 0x81
    RSP_CONFIG = 0x82
    RSP_TIME_SYNC = 0x83
    RSP_FIRMWARE_UPDATE = 0x84
    RSP_ERROR = 0xFF

    def __init__(self, host: str = "0.0.0.0", port: int = 8080, verbose: bool = False):
        self.host = host
        self.port = port
        self.verbose = verbose
        self.server_socket: Optional[socket.socket] = None
        self.running = False
        self.devices: Dict[str, DeviceStatus] = {}
        self.client_threads: Dict[str, threading.Thread] = {}
        self.lock = threading.Lock()

        if verbose:
            logger.setLevel(logging.DEBUG)

    def start(self):
        """Start the mock server"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
            logger.info(f"ECOCOMFORT 2 Mock Server started on {self.host}:{self.port}")

            while self.running:
                try:
                    self.server_socket.settimeout(1.0)
                    client_socket, client_address = self.server_socket.accept()
                    logger.info(f"New connection from {client_address}")

                    client_id = f"{client_address[0]}:{client_address[1]}"
                    thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, client_id),
                        daemon=True
                    )
                    thread.start()
                    self.client_threads[client_id] = thread

                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        logger.error(f"Accept error: {e}")

        except Exception as e:
            logger.error(f"Server error: {e}")
        finally:
            self.running = False
            if self.server_socket:
                self.server_socket.close()

    def handle_client(self, client_socket: socket.socket, client_id: str):
        """Handle individual client connection"""
        client_socket.settimeout(30.0)
        device_id = None

        try:
            logger.debug(f"[{client_id}] Client handler thread started")

            while self.running:
                try:
                    # Receive packet header
                    header = client_socket.recv(self.PACKET_HEADER_SIZE)
                    if not header or len(header) < self.PACKET_HEADER_SIZE:
                        logger.info(f"[{client_id}] Connection closed by client")
                        break

                    # Parse header (hypothesized format)
                    magic, cmd, payload_len, seq = struct.unpack('>HHHI', header)

                    if self.verbose:
                        logger.debug(f"[{client_id}] Received: magic=0x{magic:04X}, cmd=0x{cmd:02X}, len={payload_len}, seq={seq}")

                    # Receive payload
                    payload = b''
                    if payload_len > 0:
                        payload = client_socket.recv(min(payload_len, self.MAX_PAYLOAD_SIZE))

                    # Process command and generate response
                    response = self.process_command(client_id, cmd, payload)
                    device_id = self.devices.get(client_id, DeviceStatus()).device_id if client_id in self.devices else None

                    if response:
                        client_socket.sendall(response)
                        if self.verbose:
                            logger.debug(f"[{client_id}] Sent response ({len(response)} bytes)")

                except socket.timeout:
                    logger.debug(f"[{client_id}] Keepalive timeout, sending ping")
                    ping_response = self.build_packet(self.RSP_COMMAND, b'\x00', seq=0)
                    if ping_response:
                        client_socket.sendall(ping_response)

                except Exception as e:
                    logger.warning(f"[{client_id}] Error: {e}")
                    break

        except Exception as e:
            logger.error(f"[{client_id}] Handler error: {e}")
        finally:
            client_socket.close()
            with self.lock:
                if client_id in self.devices:
                    self.devices[client_id].online = False
            logger.info(f"[{client_id}] Connection closed (device: {device_id})")

    def process_command(self, client_id: str, cmd: int, payload: bytes) -> Optional[bytes]:
        """Process incoming command and return response"""

        if cmd == self.CMD_DEVICE_INFO:
            return self.handle_device_info(client_id, payload)
        elif cmd == self.CMD_SENSOR_DATA:
            return self.handle_sensor_data(client_id, payload)
        elif cmd == self.CMD_STATUS_REPORT:
            return self.handle_status_report(client_id, payload)
        elif cmd == self.CMD_PING:
            return self.build_packet(self.RSP_OK, b'', seq=0)
        else:
            logger.warning(f"[{client_id}] Unknown command: 0x{cmd:02X}")
            return self.build_packet(self.RSP_ERROR, struct.pack('B', cmd), seq=0)

    def handle_device_info(self, client_id: str, payload: bytes) -> Optional[bytes]:
        """Handle device identification/registration"""
        logger.debug(f"[{client_id}] Device info request (payload: {payload.hex()})")

        with self.lock:
            if client_id not in self.devices:
                self.devices[client_id] = DeviceStatus()

            device = self.devices[client_id]
            device.online = True
            device.last_seen = time.time()

            # Parse device MAC from payload if provided
            if len(payload) >= 6:
                device.mac_address = ':'.join(f"{b:02X}" for b in payload[:6])

        # Response: device accepted + server time
        response_data = struct.pack('>I', int(time.time()))
        logger.info(f"[{client_id}] Device registered: {device.device_id}")
        return self.build_packet(self.RSP_OK, response_data, seq=0)

    def handle_sensor_data(self, client_id: str, payload: bytes) -> Optional[bytes]:
        """Handle sensor data transmission"""
        logger.debug(f"[{client_id}] Sensor data ({len(payload)} bytes)")

        with self.lock:
            if client_id not in self.devices:
                self.devices[client_id] = DeviceStatus()

            device = self.devices[client_id]
            device.last_update = time.time()

            # Parse sensor data (hypothesized format from firmware)
            if len(payload) >= 8:
                try:
                    # Estimated structure: temp(2B), humidity(1B), voc(2B), light(2B), flags(1B)
                    temp_raw = struct.unpack('>h', payload[0:2])[0]
                    humidity = payload[2]
                    voc = struct.unpack('>H', payload[3:5])[0]
                    light = struct.unpack('>H', payload[5:7])[0]

                    device.temperature = temp_raw / 100.0  # Assuming 1/100 degree resolution
                    device.humidity = humidity
                    device.voc = voc
                    device.ambient_light = light

                    if self.verbose:
                        logger.debug(f"[{client_id}] Parsed: T={device.temperature:.2f}°C, H={device.humidity}%, VOC={device.voc}ppb, Light={device.ambient_light}lux")
                except Exception as e:
                    logger.warning(f"[{client_id}] Failed to parse sensor data: {e}")

        # Response: acknowledge + send commands if any
        response_data = b'\x00'  # No commands to send
        return self.build_packet(self.RSP_OK, response_data, seq=0)

    def handle_status_report(self, client_id: str, payload: bytes) -> Optional[bytes]:
        """Handle device status report"""
        logger.debug(f"[{client_id}] Status report ({len(payload)} bytes)")

        with self.lock:
            if client_id not in self.devices:
                self.devices[client_id] = DeviceStatus()

            device = self.devices[client_id]
            device.last_update = time.time()

            # Parse status: fan_speed(1B), fan_mode(1B), uptime(4B), signal(1B)
            if len(payload) >= 7:
                try:
                    device.fan_speed = payload[0] & 0x0F
                    fan_mode_code = (payload[0] >> 4) & 0x0F
                    device.uptime_seconds = struct.unpack('>I', payload[1:5])[0]
                    device.signal_strength = struct.unpack('>b', payload[5:6])[0]

                    mode_map = {0: "OFF", 1: "MANUAL", 2: "AUTO"}
                    device.fan_mode = mode_map.get(fan_mode_code, "UNKNOWN")

                    if self.verbose:
                        logger.debug(f"[{client_id}] Status: fan={device.fan_speed}/5 ({device.fan_mode}), uptime={device.uptime_seconds}s, signal={device.signal_strength}dBm")
                except Exception as e:
                    logger.warning(f"[{client_id}] Failed to parse status: {e}")

        # Response: send time sync and any pending commands
        time_sync = struct.pack('>I', int(time.time()))
        return self.build_packet(self.RSP_TIME_SYNC, time_sync, seq=0)

    def build_packet(self, response_type: int, payload: bytes, seq: int = 0) -> bytes:
        """Build response packet"""
        payload_len = len(payload)
        header = struct.pack('>HHHI',
                            self.PROTOCOL_MAGIC,  # Magic
                            response_type,         # Response type
                            payload_len,          # Payload length
                            seq)                  # Sequence
        return header + payload

    def get_status(self) -> Dict:
        """Get server status"""
        with self.lock:
            online_count = sum(1 for d in self.devices.values() if d.online)
            return {
                "server_time": datetime.now().isoformat(),
                "connected_devices": online_count,
                "total_devices": len(self.devices),
                "devices": [
                    {
                        "client_id": cid,
                        "status": asdict(device)
                    }
                    for cid, device in self.devices.items()
                ]
            }


def main():
    parser = argparse.ArgumentParser(
        description="ECOCOMFORT 2 Mock Server - Local Cloud Replacement"
    )
    parser.add_argument("--host", default="0.0.0.0", help="Server host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8080, help="Server port (default: 8080)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    server = ECOCOMFORTMockServer(
        host=args.host,
        port=args.port,
        verbose=args.verbose
    )

    try:
        server.start()
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
        server.running = False


if __name__ == "__main__":
    main()
