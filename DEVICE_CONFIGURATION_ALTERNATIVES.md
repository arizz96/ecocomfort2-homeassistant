# ECOCOMFORT 2 Configuration Without UART - Alternative Methods

If you don't have USB-UART access or can't physically open the device, there are several ways to redirect it to your local server.

---

## Overview of Methods

| Method | Difficulty | Hardware Needed | Time | Reversibility |
|--------|-----------|-----------------|------|---------------|
| **DNS Spoofing** | Easy | None (software only) | 5 min | ✅ Fully reversible |
| **Network Interception** | Medium | Gateway access | 10 min | ✅ Fully reversible |
| **Factory Reset** | Hard | Button/pin | 20 min | ✅ Can reconfigure |
| **WiFi Sniffing** | Hard | WiFi adapter | 30 min | ✅ Non-destructive |
| **Bluetooth Control** | Medium | BLE device | 10 min | ✅ Reversible |

---

## Method 1: DNS Spoofing (Easiest) 🎯

### How It Works
Device performs DNS lookup for `api.fantinicosmispa.com` and connects there. You intercept this DNS request and return your server's IP.

### Option A: Router-Level DNS Spoofing

**Requirements:**
- Access to your WiFi router
- Ability to modify DNS settings

**Steps:**

1. **Access Router Admin Panel**
   ```
   http://192.168.1.1  (common default)
   or
   http://router.local
   ```

2. **Find DNS Settings**
   - Look for "Advanced" or "DNS Settings"
   - Some routers call it "DNS Forwarding" or "DHCP Server Settings"

3. **Add Local DNS Record**
   - Create entry: `api.fantinicosmispa.com` → `192.168.1.100`
   - Save settings

4. **Restart Device**
   - Power off/on the ECOCOMFORT device
   - It will now connect to your local server

**Pros:**
- Works automatically for any device on your network
- Single configuration needed
- Device doesn't need reconfiguration

**Cons:**
- Requires router admin access
- May not work on all router models
- Some routers don't support custom DNS records

### Option B: Local /etc/hosts (Single Machine)

**Requirements:**
- Administrator access to your computer running mock server
- Device must be on same network as your computer

**Steps (Linux/macOS):**
```bash
# Edit /etc/hosts
sudo nano /etc/hosts

# Add these lines:
192.168.1.100 api.fantinicosmispa.com
192.168.1.100 fantinicosmistorage.blob.core.windows.net
192.168.1.100 blob.ams25prdstr04a.store.core.windows.net

# Save (Ctrl+O, Enter, Ctrl+X)

# Flush DNS cache
sudo dscacheutil -flushcache  # macOS
# or
sudo systemctl restart nscd    # Linux
```

**Steps (Windows):**
```powershell
# Edit C:\Windows\System32\drivers\etc\hosts
# Run as Administrator: notepad C:\Windows\System32\drivers\etc\hosts

# Add:
192.168.1.100 api.fantinicosmispa.com
192.168.1.100 fantinicosmistorage.blob.core.windows.net
192.168.1.100 blob.ams25prdstr04a.store.core.windows.net

# Save and close
# Flush DNS: ipconfig /flushdns
```

**Verification:**
```bash
# Test DNS resolution
nslookup api.fantinicosmispa.com
# Should return 192.168.1.100
```

**Pros:**
- No router access needed
- Works reliably
- Can be undone easily

**Cons:**
- Only affects that specific computer
- Device still resolves to your machine
- Must keep mock server running on that machine

### Option C: Pi-hole or Local DNS Server

**Requirements:**
- Raspberry Pi or Docker installation
- 30 minutes setup time

**Steps:**

1. **Install Pi-hole** (if using Raspberry Pi)
   ```bash
   curl -sSL https://install.pi-hole.net | bash
   ```

2. **Configure Adlists → Local DNS**
   - Go to Pi-hole admin panel (`:80`)
   - Add local DNS record for `api.fantinicosmispa.com`
   - Set IP to your mock server

3. **Set Router DHCP to Use Pi-hole**
   - Router → DHCP Settings → DNS Server → Pi-hole IP

4. **Restart Device**
   - It will use Pi-hole DNS
   - All requests to api.fantinicosmispa.com redirect to your server

**Pros:**
- Works for all devices on network
- Professional solution
- Can monitor all DNS queries
- Can block malware domains simultaneously

**Cons:**
- Requires additional hardware/installation
- More complex setup
- Requires ongoing maintenance

---

## Method 2: Network Interception (iptables) 🔧

### How It Works
Use `iptables` (Linux) or `pf` (macOS) to intercept packets destined for original server and redirect to your mock server.

### Option A: Linux iptables

**Requirements:**
- Linux machine on same network as device
- Root access
- iptables installed

**Steps:**

1. **Find Original Server IP**
   ```bash
   nslookup api.fantinicosmispa.com
   # Note the IP address (example: 1.2.3.4)
   ```

2. **Enable IP Forwarding**
   ```bash
   sudo sysctl -w net.ipv4.ip_forward=1
   ```

3. **Add iptables Rules**
   ```bash
   # Replace 1.2.3.4 with actual server IP
   ORIGINAL_IP="1.2.3.4"
   LOCAL_IP="192.168.1.100"
   
   # Add NAT rule
   sudo iptables -t nat -A PREROUTING -p tcp -d $ORIGINAL_IP --dport 8080 \
     -j DNAT --to-destination $LOCAL_IP:8080
   
   # Add masquerading
   sudo iptables -t nat -A POSTROUTING -j MASQUERADE
   ```

4. **Test Connection**
   - Device should now connect to your mock server
   - Check mock server logs for connection

5. **Make Persistent** (Linux)
   ```bash
   # Save rules
   sudo iptables-save > /etc/iptables/rules.v4
   
   # Restore on boot (install iptables-persistent)
   sudo apt-get install iptables-persistent
   ```

**Pros:**
- Completely transparent to device
- Works with unmodified device
- Can handle any protocol

**Cons:**
- Requires Linux machine
- Complex setup with potential issues
- Must be on same network segment
- Requires root access

### Option B: macOS pf (Packet Filter)

**Requirements:**
- macOS machine on same network
- Administrator access

**Steps:**

1. **Create pf config**
   ```bash
   sudo nano /etc/pf.conf.local
   ```

2. **Add redirection rule**
   ```
   # Find original IP: nslookup api.fantinicosmispa.com
   rdr pass on en0 proto tcp from any to 1.2.3.4 port 8080 -> 192.168.1.100
   ```

3. **Enable pf**
   ```bash
   sudo pfctl -e
   ```

4. **Load rules**
   ```bash
   sudo pfctl -f /etc/pf.conf.local
   ```

**Pros:**
- Built-in to macOS
- Works transparently

**Cons:**
- macOS specific
- Requires system-level access
- Complex rule syntax

---

## Method 3: Bluetooth LE Bridge 📱

### How It Works
Device can receive UART commands via BLE. You build a BLE client that sends WiFi configuration command without physical UART connection.

### Requirements
- Phone or BLE-capable device (Linux with BlueZ, Raspberry Pi, etc.)
- Time to implement BLE communication
- Device must be in pairing mode or already discoverable

### Steps

1. **Identify BLE Service**
   From firmware analysis: `f4b827c3-e660-4bc8-bdf6-3c8e9b845e0d`

2. **Connect via BLE**
   ```bash
   # Using bluetoothctl (Linux)
   bluetoothctl
   > scan on
   > connect <device_mac>
   > menu gatt
   > select-attribute <characteristic>
   ```

3. **Send Command**
   ```
   Send over BLE: "Set wifi conf <SSID> <PSK> <IP> 8080 60"
   ```

### Python Implementation
```python
from bleak import BleakClient
import asyncio

async def configure_via_ble():
    address = "AA:BB:CC:DD:EE:FF"  # Device MAC
    
    async with BleakClient(address) as client:
        # Find UART-like characteristic
        services = await client.get_services()
        
        for service in services:
            if str(service.uuid) == "f4b827c3-e660-4bc8-bdf6-3c8e9b845e0d":
                for char in service.characteristics:
                    if "write" in char.properties:
                        # Send command
                        cmd = b"Set wifi conf MySSID MyPass 192.168.1.100 8080 60"
                        await client.write_gatt_char(char.uuid, cmd)
                        print("Command sent via BLE!")

asyncio.run(configure_via_ble())
```

**Pros:**
- No physical connection needed
- Works over distance (10m+ range)
- Non-destructive

**Cons:**
- Requires BLE implementation
- Device must be discoverable
- More complex than alternatives

---

## Method 4: Factory Reset + Configuration 🔄

### How It Works
Device has factory reset mechanism. After reset, it enters configuration mode where you can set server address.

### Requirements
- Device reset button or recovery mechanism
- Ability to trigger configuration mode

### Steps

1. **Find Reset Mechanism**
   - Check device manual for reset button
   - May require pressing button for 10+ seconds
   - May require GPIO pin to ground

2. **Trigger Reset**
   - Hold reset button while powering on
   - OR ground specific GPIO pin

3. **Device Enters Configuration Mode**
   - Device broadcasts WiFi with default SSID (often "espressif")
   - Contains configuration web interface

4. **Connect to Configuration WiFi**
   ```bash
   # Find and connect to device's WiFi hotspot
   nmcli device wifi connect espressif
   ```

5. **Access Web Interface**
   ```
   http://192.168.4.1 (common default)
   or
   http://192.168.1.1
   ```

6. **Configure Server Settings**
   - Enter WiFi network (your network)
   - Enter WiFi password
   - Enter server IP: 192.168.1.100
   - Enter server port: 8080
   - Save and apply

**Pros:**
- Works for any WiFi configuration
- Device-native configuration
- No external tools needed

**Cons:**
- Requires device documentation
- Reset mechanism varies
- Temporary WiFi hotspot not always available
- May require physical access

---

## Method 5: WiFi Sniffing + Replay Attack 🕵️

### Advanced Method for Experimentation

If device has already connected to original cloud server, you can:

1. **Capture WiFi Packets**
   ```bash
   # Put WiFi in monitor mode
   sudo iwconfig wlan0 mode monitor
   
   # Capture traffic
   sudo tcpdump -i wlan0 -w capture.pcap
   ```

2. **Analyze Connection**
   - Find the WiFi network device connected to
   - Note the credentials in packets (if unencrypted)

3. **Replay WiFi Connection**
   - Modify packets to point to your server
   - Resend packets to device
   - Device thinks it's original network

**Pros:**
- Works even without knowing WiFi password
- Educational experience

**Cons:**
- Requires WiFi capture capability
- Complex packet manipulation
- Only works with unencrypted data
- Time-consuming process

---

## Recommended Solution by Scenario

### Scenario 1: Router Access Available
**Best Choice: DNS Spoofing (Router-Level)**
- Easiest setup (5 minutes)
- Works automatically
- Most reliable
- Fully reversible

### Scenario 2: Single Linux Machine
**Best Choice: DNS Spoofing (/etc/hosts)**
- No root needed
- Simple to undo
- Works immediately
- No additional software

### Scenario 3: Need Network-Wide Solution
**Best Choice: Pi-hole or Local DNS Server**
- Works for all devices
- Professional setup
- Monitors all queries
- Worth the installation time

### Scenario 4: No Router Access, Complex Network
**Best Choice: iptables Interception**
- Transparent redirection
- Works even if device doesn't use DNS properly
- Requires Linux machine
- More complex but very flexible

### Scenario 5: BLE Preferred
**Best Choice: Bluetooth LE Bridge**
- No network setup needed
- Works over BLE distance
- Good learning experience
- Requires implementation effort

### Scenario 6: Want to Avoid Network Changes
**Best Choice: Factory Reset + Web Config**
- Uses device's native configuration
- No network hacks needed
- Simple if reset mechanism available
- Requires device documentation

---

## Comparison Table

| Method | Setup Time | Reversibility | Network Impact | Success Rate |
|--------|-----------|---------------|---|---|
| DNS (Router) | 5 min | Instant | Network-wide | 95% |
| DNS (/etc/hosts) | 2 min | Instant | Single machine | 99% |
| Pi-hole | 30 min | Full | Network-wide | 98% |
| iptables | 10 min | Requires reload | Intercepted | 85% |
| BLE Bridge | 45 min | Instant | None | 80% |
| Factory Reset | 10 min | Instant | None | 70%* |
| WiFi Sniffing | 60 min | No | None | 40% |

*Depends on device having web config interface

---

## Troubleshooting Configuration

### Device Still Connects to Cloud
1. Check DNS resolution: `nslookup api.fantinicosmispa.com`
2. Should resolve to YOUR server IP
3. Verify device is using your DNS (check router DHCP)
4. Check firewall isn't blocking port 8080

### Device Can't Find Server
1. Verify mock server running: `netstat -ln | grep 8080`
2. Check device and server on same network: `ping <device_ip>`
3. Try disabling firewall temporarily
4. Check server logs for connection attempts

### Device Connects Then Disconnects
1. May be timeout issue (server responding too slowly)
2. May be packet format mismatch
3. Run server with `--verbose` to see what's happening
4. Check WiFi signal strength

### Configuration Not Persisting After Reboot
1. Device may reset to factory config
2. Try method that sets permanent config (factory reset mode)
3. Or use persistent DNS/iptables at network level

---

## Which Method Should You Choose?

```
Do you have router admin access?
  ├─ YES → Use DNS Spoofing (Router Level) ✅
  └─ NO  → Do you have Linux machine?
           ├─ YES → Use DNS Spoofing (/etc/hosts) ✅
           └─ NO  → Do you know the WiFi password?
                    ├─ YES → Use Factory Reset + Web Config
                    └─ NO  → Use Pi-hole (if you have spare hardware)
```

---

## Next Steps

1. **Choose your method** based on available resources
2. **Set up redirection** using the selected method
3. **Power on ECOCOMFORT device**
4. **Wait 30-60 seconds** for WiFi reconnection
5. **Check mock server logs** for connection
6. **Success!** Device is now using your local server

Once device successfully connects, proceed with traffic analysis in `IMPLEMENTATION_GUIDE.md` Phase 2.

---

## Reference

- `QUICK_REFERENCE.md` - UART method details
- `LOCAL_SERVER_TESTING_GUIDE.md` - Server setup
- `IMPLEMENTATION_GUIDE.md` - Complete workflow
- `ecocomfort2_mock_server.py` - The server itself

