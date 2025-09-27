# NTP Service Metrics Exporter - Output Formats

This document provides comprehensive documentation for the YAML and JSON output formats produced by the NTP Service Metrics Exporter.

## Format Overview

The exporter produces structured data in either YAML (default) or JSON format. Both formats contain identical information with the same structure - JSON simply represents the same data using JSON syntax instead of YAML.

**Output Structure**: Array of target server results, one entry per queried server.

## Top-Level Structure

Each target server produces one result object with the following structure:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `target` | string | The IP address that was queried | `"192.168.1.1"` |
| `resolved_ip` | string/null | The resolved IP address (same as target for IP-only mode) | `"192.168.1.1"` |
| `collected_at_utc` | string | ISO-8601 timestamp when data was collected (UTC) | `"2025-01-15T10:30:45.123456Z"` |
| `success` | boolean | Whether the query was successful | `true` |
| `error` | object/null | Error information if query failed, null if successful | `null` or error object |
| `server` | object | NTP server variables from Mode-6 queries | Server object |
| `peers` | array | List of peer servers from peer table | Array of peer objects |

## Error Object Structure

When `success` is `false`, the `error` object contains:

| Field | Type | Description | Possible Values |
|-------|------|-------------|-----------------|
| `kind` | string | Error category | `"validation"`, `"timeout"`, `"exec"`, `"parse"` |
| `message` | string | Human-readable error message | `"Invalid IP address"` |
| `detail` | string | Detailed error information | `"Invalid IP address: 192.168.1.99"` |

### Error Types

| Error Kind | Description | When It Occurs |
|------------|-------------|----------------|
| `validation` | Invalid input format | IP address format is invalid or wrong IP version for `-4`/`-6` flags |
| `timeout` | Command timeout | Server unreachable or ntpq command times out |
| `exec` | Execution failure | ntpq command fails to execute or returns error |
| `parse` | Parsing error | Unable to parse ntpq output format |

## Server Object Structure

The `server` object contains NTP server variables obtained via `ntpq -c rv` (Mode-6 queries):

| Field | Type | Description | Example | Units/Format |
|-------|------|-------------|---------|--------------|
| `reference_id` | string/null | Reference clock identifier | `"GPS"`, `"216.239.35.8"` | 4-character string or IP |
| `stratum` | integer/null | NTP stratum level (0-15) | `1`, `3` | Integer (0=unspecified, 1=primary, 2-15=secondary) |
| `reftime_utc` | string/null | Reference time in ISO-8601 format | `"2025-01-15T10:30:42Z"` | ISO-8601 UTC timestamp |
| `system_time` | string/null | System clock time in NTP format | `"0xe6c5a8c2.8f5c28f6"` | NTP timestamp (hex.hex format) |
| `last_offset` | float/null | Last measured time offset | `0.123`, `-0.045` | Milliseconds |
| `rms_offset` | float/null | RMS (root mean square) offset | `0.234` | Milliseconds |
| `frequency` | float/null | Clock frequency adjustment | `-15.123`, `2.456` | Parts per million (ppm) |
| `residual_frequency` | float/null | Residual frequency error | `0.001` | Parts per million (ppm) |
| `skew` | float/null | Clock skew measurement | `0.012` | Parts per million (ppm) |
| `root_delay` | float/null | Root delay to primary source | `0.000`, `45.123` | Milliseconds |
| `root_dispersion` | float/null | Root dispersion estimate | `0.001`, `12.345` | Milliseconds |
| `update_interval` | integer/null | Update interval | `4`, `6` | Log₂ seconds (4=16s, 6=64s) |
| `leap_status` | object/null | Leap second status information | Leap status object | See leap status table |
| `source_state` | string/null | Synchronization state | `"sync"`, `"reach"` | NTP state string |

### Leap Status Object

The `leap_status` object contains:

| Field | Type | Description | Possible Values |
|-------|------|-------------|-----------------|
| `code` | string/null | Two-digit leap indicator code | `"00"`, `"01"`, `"10"`, `"11"` |
| `meaning` | string/null | Human-readable leap status | `"none"`, `"add_second"`, `"delete_second"`, `"alarm"` |

#### Leap Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| `"00"` | `"none"` | No leap second warning |
| `"01"` | `"add_second"` | Last minute of day has 61 seconds |
| `"10"` | `"delete_second"` | Last minute of day has 59 seconds |
| `"11"` | `"alarm"` | Clock not synchronized |

## Peers Array Structure

The `peers` array contains peer server information from `ntpq -np`:

| Field | Type | Description | Example | Units/Format |
|-------|------|-------------|---------|--------------|
| `name_or_ip` | string | Peer server IP address | `"216.239.35.0"` | IP address |
| `refid` | string | Peer's reference identifier | `".GOOG."`, `"216.239.35.8"` | 4-char string or IP |
| `source_stratum` | integer | Peer's stratum level | `1`, `2` | Integer (1-15) |
| `type` | string | Peer association type | `"u"`, `"s"`, `"b"` | Single character |
| `poll_interval` | integer | Polling interval | `64`, `1024` | Log₂ seconds |
| `reachability` | integer | Reachability status | `255`, `377` | Octal bitmask (0-377) |
| `last_sample_when` | integer/null | Time since last sample | `64`, `null` | Seconds |
| `offset` | float | Time offset from peer | `-0.123`, `167.814` | Milliseconds |
| `delay` | float | Network round-trip delay | `1.234`, `40.139` | Milliseconds |
| `jitter` | float | Jitter measurement | `0.456`, `15.537` | Milliseconds |
| `selected_marker` | string/null | Peer selection status | `"*"`, `"+"`, `"-"`, `null` | Single character or null |

### Peer Type Codes

| Type | Description |
|------|-------------|
| `"u"` | Unicast association |
| `"s"` | Symmetric active |
| `"S"` | Symmetric passive |
| `"b"` | Broadcast |
| `"B"` | Broadcast client |
| `"l"` | Local clock |
| `"p"` | Pool association |

### Peer Selection Markers

| Marker | Meaning | Description |
|--------|---------|-------------|
| `"*"` | System peer | Currently selected for synchronization |
| `"+"` | Candidate | Suitable for synchronization |
| `"-"` | Outlier | Discarded by clustering algorithm |
| `"#"` | Backup | Backup candidate |
| `"."` | Excess | Discarded by select algorithm |
| `"o"` | PPS peer | Pulse-per-second peer |
| `null` | Unselected | No selection status |

### Reachability Status

The `reachability` field is an octal bitmask (0-377) representing the last 8 polling attempts:
- `377` (binary: 11111111) = All 8 recent polls successful
- `255` (binary: 11111111) = All 8 recent polls successful  
- `0` = All recent polls failed
- Each bit represents one polling interval, with the rightmost bit being the most recent

## Complete Example Output

### YAML Format (Default)

```yaml
- target: "192.168.1.1"
  resolved_ip: "192.168.1.1"
  collected_at_utc: "2025-01-15T10:30:45.123456Z"
  success: true
  error: null
  server:
    reference_id: "GPS"
    stratum: 1
    reftime_utc: "2025-01-15T10:30:42.427Z"
    system_time: "0xe6c5a8c2.8f5c28f6"
    last_offset: 0.123
    rms_offset: 0.234
    frequency: -15.123
    residual_frequency: 0.001
    skew: 0.012
    root_delay: 0.000
    root_dispersion: 0.001
    update_interval: 4
    leap_status:
      code: "00"
      meaning: "none"
    source_state: "sync"
  peers:
    - name_or_ip: "216.239.35.0"
      refid: ".GOOG."
      source_stratum: 1
      type: "u"
      poll_interval: 64
      reachability: 255
      last_sample_when: 64
      offset: -0.123
      delay: 1.234
      jitter: 0.456
      selected_marker: "*"
    - name_or_ip: "216.239.35.4"
      refid: ".GOOG."
      source_stratum: 1
      type: "u"
      poll_interval: 64
      reachability: 377
      last_sample_when: 32
      offset: 0.087
      delay: 2.345
      jitter: 0.234
      selected_marker: "+"
```

### JSON Format

The JSON format contains identical data with JSON syntax:

```json
[
  {
    "target": "192.168.1.1",
    "resolved_ip": "192.168.1.1",
    "collected_at_utc": "2025-01-15T10:30:45.123456Z",
    "success": true,
    "error": null,
    "server": {
      "reference_id": "GPS",
      "stratum": 1,
      "reftime_utc": "2025-01-15T10:30:42.427Z",
      "system_time": "0xe6c5a8c2.8f5c28f6",
      "last_offset": 0.123,
      "rms_offset": 0.234,
      "frequency": -15.123,
      "residual_frequency": 0.001,
      "skew": 0.012,
      "root_delay": 0.000,
      "root_dispersion": 0.001,
      "update_interval": 4,
      "leap_status": {
        "code": "00",
        "meaning": "none"
      },
      "source_state": "sync"
    },
    "peers": [
      {
        "name_or_ip": "216.239.35.0",
        "refid": ".GOOG.",
        "source_stratum": 1,
        "type": "u",
        "poll_interval": 64,
        "reachability": 255,
        "last_sample_when": 64,
        "offset": -0.123,
        "delay": 1.234,
        "jitter": 0.456,
        "selected_marker": "*"
      }
    ]
  }
]
```

## Error Example

```yaml
- target: "192.168.1.99"
  resolved_ip: null
  collected_at_utc: "2025-01-15T10:30:45.123456Z"
  success: false
  error:
    kind: "validation"
    message: "Invalid IP address"
    detail: "Invalid IP address: 192.168.1.99"
  server:
    reference_id: null
    stratum: null
    reftime_utc: null
    system_time: null
    last_offset: null
    rms_offset: null
    frequency: null
    residual_frequency: null
    skew: null
    root_delay: null
    root_dispersion: null
    update_interval: null
    leap_status:
      code: null
      meaning: null
    source_state: null
  peers: []
```

## Usage Notes

1. **Null Values**: Fields may be `null` when data is unavailable or parsing fails
2. **Mode-6 Fallback**: If Mode-6 queries are not supported, all `server` fields will be `null`
3. **Peer Truncation**: Very long hostnames in peer output may be truncated by ntpq
4. **Time Formats**: All timestamps are in UTC with ISO-8601 format
5. **Numeric Precision**: Floating-point values maintain precision from ntpq output
6. **IP-Only Mode**: The exporter only accepts IP addresses, no hostname resolution is performed

## Format Selection

- **Default**: YAML format for human readability
- **JSON**: Use `--json` flag for machine processing and API integration
- **File Output**: Use `--output-file` to write to file instead of stdout
