#!/usr/bin/env python3
"""
ECOCOMFORT 2 Packet Analyzer & Debugger

Analyzes captured network traffic and packet logs to reverse-engineer
the exact protocol structure.

Usage:
    # Analyze hex packet
    python3 ecocomfort2_packet_analyzer.py --hex "FEED0102001C00000001AABBCCDDEE..."

    # Analyze tcpdump capture
    python3 ecocomfort2_packet_analyzer.py --pcap ecocomfort_traffic.pcap

    # Analyze server logs
    python3 ecocomfort2_packet_analyzer.py --logs server.log

    # Interactive mode
    python3 ecocomfort2_packet_analyzer.py --interactive
"""

import struct
import argparse
import sys
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import json
from datetime import datetime


@dataclass
class PacketInfo:
    """Parsed packet information"""
    offset: int = 0
    magic: int = 0
    command_type: int = 0
    payload_length: int = 0
    sequence: int = 0
    payload: bytes = b''
    timestamp: Optional[float] = None

    def __str__(self) -> str:
        return (
            f"Magic: 0x{self.magic:04X} | "
            f"Cmd: 0x{self.command_type:02X} | "
            f"PayLen: {self.payload_length:4d} | "
            f"Seq: {self.sequence:5d} | "
            f"Payload: {self.payload.hex()[:32]}{'...' if len(self.payload) > 16 else ''}"
        )


class ECOCOMFORTPacketAnalyzer:
    """Packet analysis and reverse engineering tool"""

    # Known protocol constants
    PROTOCOL_MAGIC = 0xFEED

    # Command type names
    COMMAND_NAMES = {
        0x01: "DEVICE_INFO",
        0x02: "SENSOR_DATA",
        0x03: "STATUS_REPORT",
        0x04: "PING",
        0x05: "ACK",
        0x80: "RSP_OK",
        0x81: "RSP_COMMAND",
        0x82: "RSP_CONFIG",
        0x83: "RSP_TIME_SYNC",
        0x84: "RSP_FIRMWARE_UPDATE",
        0xFF: "RSP_ERROR",
    }

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.packets: List[PacketInfo] = []

    def parse_hex_packet(self, hex_string: str) -> Optional[PacketInfo]:
        """Parse a single hex packet string"""
        try:
            # Remove spaces and common prefixes
            hex_clean = hex_string.replace(' ', '').replace('0x', '').replace(':', '')

            if len(hex_clean) < 16:  # Minimum header size
                print(f"Error: Hex string too short (need ≥16 chars, got {len(hex_clean)})")
                return None

            data = bytes.fromhex(hex_clean)
            return self.parse_binary_packet(data)

        except ValueError as e:
            print(f"Error parsing hex: {e}")
            return None

    def parse_binary_packet(self, data: bytes, offset: int = 0) -> Optional[PacketInfo]:
        """Parse a binary packet from bytes"""
        if len(data) < 8:
            return None

        try:
            magic, cmd, payload_len, seq = struct.unpack('>HHHI', data[0:8])

            packet = PacketInfo(
                offset=offset,
                magic=magic,
                command_type=cmd,
                payload_length=payload_len,
                sequence=seq,
                payload=data[8:8+payload_len] if payload_len > 0 else b''
            )

            return packet

        except struct.error as e:
            print(f"Error unpacking packet: {e}")
            return None

    def analyze_packet(self, packet: PacketInfo) -> Dict:
        """Detailed analysis of packet contents"""
        analysis = {
            "header": {
                "magic": f"0x{packet.magic:04X}",
                "magic_valid": packet.magic == self.PROTOCOL_MAGIC,
                "command_type": f"0x{packet.command_type:02X}",
                "command_name": self.COMMAND_NAMES.get(packet.command_type, "UNKNOWN"),
                "payload_length": packet.payload_length,
                "sequence": packet.sequence,
            },
            "payload": {
                "hex": packet.payload.hex(),
                "length": len(packet.payload),
                "bytes": list(packet.payload),
            }
        }

        # Try to parse known payload structures
        if packet.command_type == 0x01:  # DEVICE_INFO
            analysis["decoded"] = self._parse_device_info(packet.payload)
        elif packet.command_type == 0x02:  # SENSOR_DATA
            analysis["decoded"] = self._parse_sensor_data(packet.payload)
        elif packet.command_type == 0x03:  # STATUS_REPORT
            analysis["decoded"] = self._parse_status_report(packet.payload)
        elif packet.command_type == 0x83:  # TIME_SYNC
            analysis["decoded"] = self._parse_time_sync(packet.payload)

        return analysis

    def _parse_device_info(self, payload: bytes) -> Dict:
        """Parse DEVICE_INFO payload"""
        result = {"type": "DEVICE_INFO"}

        if len(payload) >= 6:
            mac = ':'.join(f"{b:02X}" for b in payload[0:6])
            result["mac_address"] = mac

        if len(payload) >= 22:
            device_id = payload[6:22].decode('utf-8', errors='ignore').strip('\x00')
            result["device_id"] = device_id

        if len(payload) >= 26:
            version = struct.unpack('>I', payload[22:26])[0]
            result["firmware_version"] = f"{(version >> 16) & 0xFF}.{(version >> 8) & 0xFF}.{version & 0xFF}"

        return result

    def _parse_sensor_data(self, payload: bytes) -> Dict:
        """Parse SENSOR_DATA payload"""
        result = {"type": "SENSOR_DATA"}

        if len(payload) >= 8:
            try:
                temp_raw = struct.unpack('>h', payload[0:2])[0]
                humidity = payload[2]
                voc = struct.unpack('>H', payload[3:5])[0]
                light = struct.unpack('>H', payload[5:7])[0]

                result["temperature_raw"] = temp_raw
                result["temperature_celsius"] = temp_raw / 100.0
                result["humidity_percent"] = humidity
                result["voc_ppb"] = voc
                result["ambient_light_lux"] = light

            except Exception as e:
                result["parse_error"] = str(e)

        return result

    def _parse_status_report(self, payload: bytes) -> Dict:
        """Parse STATUS_REPORT payload"""
        result = {"type": "STATUS_REPORT"}

        if len(payload) >= 7:
            try:
                control_byte = payload[0]
                fan_speed = control_byte & 0x0F
                fan_mode = (control_byte >> 4) & 0x0F
                uptime = struct.unpack('>I', payload[1:5])[0]
                signal = struct.unpack('>b', payload[5:6])[0]

                mode_map = {0: "OFF", 1: "MANUAL", 2: "AUTO"}
                result["fan_speed"] = fan_speed
                result["fan_mode"] = mode_map.get(fan_mode, f"UNKNOWN({fan_mode})")
                result["uptime_seconds"] = uptime
                result["signal_strength_dbm"] = signal

            except Exception as e:
                result["parse_error"] = str(e)

        return result

    def _parse_time_sync(self, payload: bytes) -> Dict:
        """Parse TIME_SYNC payload"""
        result = {"type": "TIME_SYNC"}

        if len(payload) >= 4:
            try:
                timestamp = struct.unpack('>I', payload[0:4])[0]
                result["server_timestamp"] = timestamp
                result["datetime"] = datetime.fromtimestamp(timestamp).isoformat()
            except Exception as e:
                result["parse_error"] = str(e)

        return result

    def analyze_stream(self, data: bytes) -> List[PacketInfo]:
        """Find and analyze all packets in a binary stream"""
        packets = []
        i = 0

        while i < len(data) - 8:
            # Look for magic bytes
            if data[i:i+2] == b'\xFE\xED':
                packet = self.parse_binary_packet(data[i:], offset=i)
                if packet:
                    packets.append(packet)
                    # Skip past this packet
                    i += 8 + packet.payload_length
                else:
                    i += 1
            else:
                i += 1

        return packets

    def print_summary(self, packets: List[PacketInfo]):
        """Print summary statistics of packets"""
        if not packets:
            print("No packets found")
            return

        print(f"\n{'='*80}")
        print(f"Packet Analysis Summary: {len(packets)} packets")
        print(f"{'='*80}\n")

        # Command frequency
        cmd_counts = {}
        for p in packets:
            cmd_name = self.COMMAND_NAMES.get(p.command_type, f"0x{p.command_type:02X}")
            cmd_counts[cmd_name] = cmd_counts.get(cmd_name, 0) + 1

        print("Command Frequency:")
        for cmd, count in sorted(cmd_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {cmd:20} : {count:4d} ({count*100//len(packets):3d}%)")

        # Payload size statistics
        payload_sizes = [p.payload_length for p in packets]
        print(f"\nPayload Size Statistics:")
        print(f"  Min:     {min(payload_sizes):4d} bytes")
        print(f"  Max:     {max(payload_sizes):4d} bytes")
        print(f"  Average: {sum(payload_sizes)//len(payload_sizes):4d} bytes")

        # Sequence analysis
        sequences = [p.sequence for p in packets]
        print(f"\nSequence Analysis:")
        print(f"  Min: {min(sequences)}")
        print(f"  Max: {max(sequences)}")

        print(f"\n{'='*80}\n")

    def print_detailed(self, packets: List[PacketInfo]):
        """Print detailed analysis of each packet"""
        for i, packet in enumerate(packets):
            cmd_name = self.COMMAND_NAMES.get(packet.command_type, "UNKNOWN")
            print(f"\nPacket {i+1}: {cmd_name}")
            print(f"  {packet}")

            if self.verbose:
                analysis = self.analyze_packet(packet)
                print(f"\n  Detailed Analysis:")

                if "decoded" in analysis:
                    for key, value in analysis["decoded"].items():
                        if key != "type":
                            print(f"    {key}: {value}")

    def export_json(self, packets: List[PacketInfo], filename: str):
        """Export analysis to JSON"""
        export_data = []

        for packet in packets:
            analysis = self.analyze_packet(packet)
            analysis["offset"] = packet.offset
            export_data.append(analysis)

        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)

        print(f"Exported {len(export_data)} packets to {filename}")


def main():
    parser = argparse.ArgumentParser(
        description="ECOCOMFORT 2 Packet Analyzer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze a single hex packet
  python3 ecocomfort2_packet_analyzer.py --hex "FEED0102001C00000001..."

  # Analyze server logs
  python3 ecocomfort2_packet_analyzer.py --logs server.log --summary

  # Interactive mode
  python3 ecocomfort2_packet_analyzer.py --interactive
        """
    )

    parser.add_argument("--hex", help="Analyze hex packet string")
    parser.add_argument("--logs", help="Analyze server log file")
    parser.add_argument("--pcap", help="Analyze tcpdump PCAP file (requires scapy)")
    parser.add_argument("--summary", "-s", action="store_true", help="Print summary statistics")
    parser.add_argument("--detailed", "-d", action="store_true", help="Print detailed analysis")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--export", "-e", help="Export analysis to JSON file")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")

    args = parser.parse_args()

    analyzer = ECOCOMFORTPacketAnalyzer(verbose=args.verbose)

    # Hex packet analysis
    if args.hex:
        packet = analyzer.parse_hex_packet(args.hex)
        if packet:
            print("Parsed Packet:")
            print(f"  {packet}\n")
            analysis = analyzer.analyze_packet(packet)
            print("Analysis:")
            print(json.dumps(analysis, indent=2))

    # Log file analysis
    elif args.logs:
        try:
            import re
            with open(args.logs, 'r') as f:
                content = f.read()

            # Extract hex packets from log format: "Received: magic=0xFEED, cmd=0x01, len=28, seq=1"
            hex_packets = re.findall(r'Received: (.*)', content)

            if hex_packets:
                # Try to reconstruct full hex from log format
                print(f"Found {len(hex_packets)} packet references in log")
                analyzer.print_summary(analyzer.packets)
            else:
                print("No packets found in log format")

        except FileNotFoundError:
            print(f"File not found: {args.logs}")

    # Interactive mode
    elif args.interactive:
        print("ECOCOMFORT 2 Packet Analyzer - Interactive Mode")
        print("Commands: hex, log, quit, help")
        print()

        while True:
            try:
                user_input = input("analyzer> ").strip()

                if not user_input:
                    continue
                elif user_input == "quit":
                    break
                elif user_input == "help":
                    print("hex <hex_string>  - Analyze hex packet")
                    print("log <file>        - Analyze log file")
                    print("quit              - Exit")
                elif user_input.startswith("hex "):
                    hex_str = user_input[4:].strip()
                    packet = analyzer.parse_hex_packet(hex_str)
                    if packet:
                        analysis = analyzer.analyze_packet(packet)
                        print(json.dumps(analysis, indent=2))
                elif user_input.startswith("log "):
                    filename = user_input[4:].strip()
                    try:
                        with open(filename, 'r') as f:
                            data = bytes.fromhex(f.read())
                        packets = analyzer.analyze_stream(data)
                        print(f"Found {len(packets)} packets")
                        analyzer.print_summary(packets)
                    except Exception as e:
                        print(f"Error: {e}")

            except KeyboardInterrupt:
                print("\nQuit")
                break
            except Exception as e:
                print(f"Error: {e}")

    else:
        if args.summary or args.detailed or args.export:
            print("Error: --summary/--detailed/--export require --hex or --logs")
        else:
            parser.print_help()


if __name__ == "__main__":
    main()
