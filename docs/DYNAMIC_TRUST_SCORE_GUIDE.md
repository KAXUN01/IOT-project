# Dynamic Trust Score Mechanism Guide

This document provides a comprehensive, end-to-end guide to the **Dynamic Trust Score** mechanism implemented in the Zero Trust SDN Framework. It details how the trust score is calculated, managed, and used to enforce adaptive access control policies.

## 1. System Overview

The **Dynamic Trust Score** is a quantifiable metric (0-100) assigned to every device in the network. Unlike static security models that verify identity only once (at login), this system evaluates trust **continuously** based on:
1.  **Device Integrity**: Is the device still valid and uncompromised? (Attestation)
2.  **Behavioral Analysis**: Is the device acting normally? (Heuristic Analyst)
3.  **Security Events**: Have any threats been detected? (IDS/Honeypot)

This score allows the **Policy Engine** to make fine-grained, adaptive decisions—automatically quarantining suspicious devices or restricting access without human intervention.

---

## 2. Architecture & Components

The mechanism is built upon several integrated components:

### A. Trust Evaluator (`trust_evaluator/`)
*   **`TrustScorer`**: The core engine that calculates and manages scores. It maintains the current score, history, and contributing factors for each device.
*   **`DeviceAttestation`**: Runs background checks to verify device integrity periodically.
*   **`PolicyAdapter`**: Listens for score changes and translates them into network policy actions (Allow/Deny/Redirect).

### B. Integration Points
*   **`IdentityDatabase`**: Persists trust scores and history to disk (`identity.db`), ensuring scores survive system restarts.
*   **`ZeroTrustFramework`**: Orchestrates the threads for attestation, scoring, and policy updates.
*   **`SDNPolicyEngine` (Ryu)**: Enforces the actual network rules (OpenFlow) based on decisions from the `PolicyAdapter`.

---

## 3. Trust Score Calculation

The trust score is an integer ranging from **0 (Untrusted)** to **100 (Fully Trusted)**.

### Initialization
*   **New Devices**: Assigned an initial score of **70** (Monitored/Trusted state).
*   **Existing Devices**: Score is loaded from the `identity.db` database on startup.

### Scoring Factors
The score is dynamic and adjusts based on events:

| Event Category | specific Event | Score Adjustment | Reason |
| :--- | :--- | :--- | :--- |
| **Integrity** | Attestation Failure | **-20** | Device failed periodic check (e.g., missing heartbeat, invalid cert). |
| **Security** | High Severity Alert | **-40** | Critical threat detected (e.g., malware signature). |
| **Security** | Medium Severity Alert | **-20** | Suspicious activity (e.g., port scanning). |
| **Security** | Low Severity Alert | **-10** | Minor anomaly. |
| **Behavior** | Behavioral Anomaly (High) | **-30** | Deviation from established ML baseline. |
| **Behavior** | Behavioral Anomaly (Med) | **-15** | Moderate deviation. |
| **Behavior** | Behavioral Anomaly (Low) | **-5** | Slight deviation. |
| **Positive** | Good Behavior / Time | **+2** | Gradual recovery over time (if implemented) or positive validation. |

### Logic Location
*   **Adjustments**: `TrustScorer.adjust_trust_score(device_id, adjustment, reason)`
*   **Persistence**: Scores are saved immediately to `trust_score_history` in SQLite.

---

## 4. Continuous Device Attestation

The **Device Attestation** module running in a background thread ensures devices remain active and valid.

### Workflow
1.  **Interval**: Runs every **300 seconds** (5 minutes) by default.
2.  **Checks Performed**:
    *   **Certificate Validity**: Verifies the device's mTLS certificate against the CA.
    *   **Heartbeat**: checks if the device has sent a "heartbeat" signal recently (within 2x interval).
    *   **Check Frequency**: Ensures the device hasn't gone "dark" (missing checks).
3.  **Failure Handling**:
    *   If *any* check fails, `TrustScorer.record_attestation_failure(device_id)` is called.
    *   Score drops by **20 points**.
    *   Policy is re-evaluated immediately.

---

## 5. Policy Integration & Thresholds

The **Policy Adapter** monitors trust scores and automatically updates network access rules.

### Trust Levels
| Score Range | Level | Description |
| :--- | :--- | :--- |
| **70 - 100** | **Trusted** | Device is healthy and authenticated. |
| **50 - 69** | **Monitored** | Device is suspicious or new; traffic may be inspected. |
| **30 - 49** | **Suspicious** | Significant issues detected. |
| **0 - 29** | **Untrusted** | Valid threats confirmed. |

### Policies (Actions)
Use `PolicyAdapter.adapt_policy_for_device(device_id)`:

1.  **ALLOW** (Score ≥ 70):
    *   Full network access permitted.
2.  **REDIRECT** (Score 50-69):
    *   Traffic may be redirected to an inspection middlebox or Honeypot.
3.  **DENY** (Score 30-49):
    *   Access to sensitive resources is blocked.
4.  **QUARANTINE** (Score < 30):
    *   Device is isolated completely. Can only communicate with the remediation server (if configured).

---

## 6. End-to-End Workflow Example

1.  **Scenario**: A configured IoT sensor (Score: 75) gets infected and starts port scanning.
2.  **Detection**:
    *   The **Heuristic Analyst (Anomaly Detector)** notices the abnormal traffic pattern (deviation from baseline).
    *   It triggers an alert: `record_security_alert(device_id, 'Port Scan', 'high')`.
3.  **Scoring Update**:
    *   `TrustScorer` receives the alert.
    *   Calculation: $75 - 40 = 35$.
    *   New Score: **35**.
    *   Change is logged to DB.
    *   Callbacks are fired.
4.  **Policy Adaptation**:
    *   `PolicyAdapter` sees score drops below 50.
    *   Determines new action: **DENY/QUARANTINE**.
    *   Calls `SDNPolicyEngine.apply_policy(device_id, 'deny')`.
5.  **Enforcement**:
    *   Ryu Controller installs OpenFlow drop rules for the device's MAC address.
    *   The device is effectively cut off from the network instantly.

---

## 7. Configuration Reference

Configuration is managed in `zero_trust_integration.py` initialization:

```python
# Default Configuration Values
config = {
    'initial_trust_score': 70,       # Starting score
    'attestation_interval': 300,     # Seconds between integrity checks
}
```

### Database Schema (SQLite)
*   **`devices` table**: Stores current `trust_score`.
*   **`trust_score_history` table**:
    *   `device_id`
    *   `trust_score`
    *   `reason` (e.g., "Security alert: anomaly (high)")
    *   `timestamp`
