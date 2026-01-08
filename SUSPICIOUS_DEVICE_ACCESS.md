# Suspicious Device Access Control

This document outlines the specific access limitations imposed on devices flagged as "Suspicious" (Trust Score < 50, High-Severity ML Detection, or Critical Anomalies) within the IoT Security Framework.

## 1. What Suspicious Devices CANNOT Access

| Resource/Service | Status | Code Enforcement Mechanism |
| :--- | :--- | :--- |
| **Any Network Traffic** | ❌ BLOCKED | **SDN Packet Drop**: In `sdn_policy_engine.py`, the `packet_in_handler` checks the device's policy. If the action is `deny`, it explicitly refuses to install a forwarding rule, effectively dropping the packet at the switch level. |
| **Sensitive Resources** | ❌ BLOCKED | **Network Isolation**: By default, no flow rules exist to allow traffic to pass from one port to another. The "Allow" rule is only installed if the device is trusted. |
| **Controller Communications** | ❌ BLOCKED | **API Rejection**: In `controller.py`'s `/data` endpoint, the `device_authorized` check fails for revoked/suspicious devices. Additionally, the SDN controller drops the packet before it even reaches the application layer. |
| **Other IoT Devices** | ❌ BLOCKED | **No peer-to-peer flows**: The `allow` policy installs a rule `parser.OFPActionOutput(ofproto.OFPP_FLOOD)`, which enables talking to other devices. The `deny` policy skips this, isolating the device completely. |
| **Internet/External Services** | ❌ BLOCKED | **Gateway Block**: Similar to peer-to-peer blocking, the lack of forwarding rules prevents packets from reaching the gateway port (router). |
| **Management/Admin Interfaces** | ❌ BLOCKED | **Auth Middleware**: Admin interfaces are protected by checks that require valid, active sessions. A suspicious device usually has its session revoked. |
| **Data Submission Endpoints** | ❌ BLOCKED | **Endpoint Logic**: The `data()` function in `controller.py` returns `{'status': 'rejected'}` immediately if the device status is revoked or unauthorized. |
| **Token-Based APIs** | ❌ BLOCKED | **Token Retraction**: When a device is flagged as suspicious, its token is invalidated (often via `device_tokens.pop(device_id)`), causing `403 Forbidden` on all subsequent requests. |

## 2. What Suspicious Devices CAN Access

| Resource/Service | Status | Reason |
| :--- | :--- | :--- |
| **Local Device Resources** | ✅ ALLOWED | **Hardware Reality**: The network controller cannot physically stop the local processor on the ESP32/Pi from running its own firmware code (reading sensors, blinking LEDs, calculating values locally). |
| **Self-Contained Operations** | ✅ ALLOWED | **No Network Dependency**: Logic that doesn't require "calling home" (e.g., a thermostat maintaining temperature locally) continues to function because the block is solely at the **Network Edge**. |

## Summary

The system uses a **Zero Trust** approach where network access is a privilege granted by trust, not a default right. Once trust is lost, the "Network" effectively disappears for that device, isolating it completely from the rest of the infrastructure.
