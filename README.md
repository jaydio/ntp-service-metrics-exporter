# NTP Service Metrics Exporter

A minimal, production-ready NTP service metrics exporter implemented in Python. Designed for Linux userland environments, this tool queries NTP servers using `ntpq` commands and outputs structured YAML or JSON data suitable for monitoring systems and analysis.

**Why ntpq instead of Python NTP libraries?** This exporter uses the standard `ntpq` command rather than Python libraries like `ntplib` or `python-ntp` to provide comprehensive NTP server diagnostics. While Python libraries can perform basic NTP time queries, they lack support for Mode-6 control queries that provide detailed server variables (stratum, reference clock, frequency adjustments, leap status) and cannot access peer table information showing server synchronization relationships. The `ntpq` tool offers decades of proven reliability and complete NTP protocol coverage, enabling this exporter to deliver the rich metrics required for production monitoring and analysis.

## Features

- **IP Address Only**: Accepts only valid IPv4 and IPv6 addresses (no hostname resolution)
- **Concurrent Querying**: Query multiple NTP servers simultaneously with configurable concurrency
- **Mode-6 Support Detection**: Automatically detects and uses Mode-6 queries when supported
- **Graceful Fallback**: Falls back to peer-only queries when Mode-6 is not available
- **Structured Output**: Clean YAML or JSON output suitable for monitoring systems
- **IPv4/IPv6 Support**: Query both IPv4 and IPv6 NTP servers with version filtering
- **Timeout Management**: Configurable timeouts to prevent hanging on unresponsive servers
- **Robust Error Handling**: Comprehensive structured error reporting with timeout management
- **Zero Dependencies**: Uses only standard system tools (ntpq, timeout, getent)
- **Production Ready**: Comprehensive logging, validation, and testing

## Requirements

- Python 3.6+ (uses only standard library)
- `ntpq` command (from ntpsec 1.2.4+ or compatible NTP implementation)
- Standard POSIX tools: `timeout`, `getent`
- Linux userland (tested on RHEL, SUSE, Ubuntu, Fedora)
- UDP port 123 access to target NTP servers
- Firewall/ACL configuration for Mode-6 queries (optional but recommended)

### Operational Considerations

- **Timeouts**: Default 5-second timeout balances responsiveness and reliability
- **Concurrency Limits**: Higher concurrency may overwhelm target servers or network
- **Monitoring**: Non-zero exit codes indicate failures for monitoring integration

### Performance Guidelines

- **Batch Processing**: Process multiple servers in single invocation for efficiency
- **Timeout Tuning**: Increase timeout for slow networks, decrease for fast response
- **Concurrency Limits**: Higher concurrency may overwhelm target servers or network
- **Output Size**: Large peer lists may produce substantial YAML output

## Installation

### Option 1: Direct Installation (Recommended)

```bash
# Clone or download the repository
git clone <repository-url>
cd ntp-server-metrics-export

# Make script executable
chmod +x ntp_exporter.py

# Install optional dependencies (PyYAML for enhanced validation)
pip3 install -r requirements.txt

# Test installation
./ntp_exporter.py --help
```

### Option 2: System-wide Installation

```bash
# Clone repository
git clone <repository-url>
cd ntp-server-metrics-export

# Install to system location
sudo cp ntp_exporter.py /usr/local/bin/ntp_exporter
sudo chmod +x /usr/local/bin/ntp_exporter

# Install optional dependencies system-wide
sudo pip3 install -r requirements.txt

# Test system installation
ntp_exporter --help
```

### Option 3: Virtual Environment Installation

```bash
# Clone repository
git clone <repository-url>
cd ntp-server-metrics-export

# Create and activate virtual environment
python3 -m venv ntp-exporter-env
source ntp-exporter-env/bin/activate

# Install dependencies in venv
pip3 install -r requirements.txt

# Make script executable
chmod +x ntp_exporter.py

# Test in venv
./ntp_exporter.py --help

# To use later, activate venv first:
# source ntp-exporter-env/bin/activate
```

### Dependencies

The script uses only Python standard library modules and requires no external dependencies for core functionality. The optional `requirements.txt` includes:

- **PyYAML**: Enhanced YAML validation (optional - built-in YAML emitter available)

**System Requirements:**
- `ntpq` command (from ntpsec 1.2.4+ or compatible NTP implementation)
- Standard POSIX tools: `timeout`, `getent`

## Usage

### Quick Start

```bash
# Basic usage with IPv4 address
./ntp_exporter.py 192.168.1.1

# IPv4 only mode
./ntp_exporter.py -4 192.168.1.1

# IPv6 only mode  
./ntp_exporter.py -6 2001:4860:4860::8888

# JSON output with timeout
./ntp_exporter.py --json --timeout 10 8.8.8.8

# Quiet mode with high concurrency and output file
./ntp_exporter.py -q -j 16 \
  --output-file /var/log/ntp-metrics.yaml \
  --timeout 3 \
  192.168.1.1 10.0.0.1 8.8.8.8
```

### Command Line Options

- `--timeout`, `-t`: Timeout in seconds for ntpq commands (default: 5)
- `--jobs`, `-j`: Maximum concurrent jobs (default: 8)
- `--quiet`, `-q`: Suppress warning messages
- `--json`: Output in JSON format instead of YAML
- `--output-file`, `-o`: Write output to file instead of stdout
- `-4`, `--ipv4`: Use IPv4 addresses only (filters out IPv6)
- `-6`, `--ipv6`: Use IPv6 addresses only (filters out IPv4)
- `--help`, `-h`: Show help message and exit

### IP Version Selection

The exporter only accepts valid IP addresses (no hostname resolution). You can restrict IP version:

- Use `-4` or `--ipv4` to accept only IPv4 addresses
- Use `-6` or `--ipv6` to accept only IPv6 addresses
- Default behavior accepts both IPv4 and IPv6 addresses

This is particularly useful when:
- Your network only supports one IP version
- You want to test specific IP version connectivity
- You need to ensure consistent address family usage

## Output Schema

The exporter produces a YAML array with one entry per target server:

```yaml
- target: "192.168.1.1"
  resolved_ip: "192.168.1.1"
  collected_at_utc: "2025-01-15T10:30:45Z"
  success: true
  error: null
  server:
    reference_id: "GPS"
    stratum: 1
    reftime_utc: "2025-01-15T10:30:42Z"
    system_time: "0xe6c5a8c2.8f5c28f6"
    last_offset: 0.123
    rms_offset: null
    frequency: -15.123
    residual_frequency: null
    skew: null
    root_delay: 0.000
    root_dispersion: 0.001
    update_interval: 4
    leap_status:
      code: "00"
      meaning: "none"
    source_state: null
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
```

### Exported Metrics

#### Server Variables (from `ntpq -c rv`)

- `reference_id`: Reference clock identifier
- `stratum`: NTP stratum level
- `reftime_utc`: Reference time (ISO-8601 format when possible)
- `system_time`: System clock time
- `last_offset`: Last measured offset
- `rms_offset`: RMS offset
- `frequency`: Clock frequency adjustment
- `residual_frequency`: Residual frequency
- `skew`: Clock skew
- `root_delay`: Root delay
- `root_dispersion`: Root dispersion
- `update_interval`: Update interval
- `leap_status`: Leap second status (code and meaning)
- `source_state`: Synchronization state

#### Peer Information (from `ntpq -np`)

- `name_or_ip`: Peer server address
- `refid`: Peer's reference ID
- `source_stratum`: Peer's stratum
- `type`: Peer type (unicast, multicast, etc.)
- `poll_interval`: Polling interval
- `reachability`: Reachability status (octal)
- `last_sample_when`: Time since last sample
- `offset`: Time offset
- `delay`: Network delay
- `jitter`: Jitter measurement
- `selected_marker`: Selection status (`*`, `+`, `-`, etc.)

## Error Handling

The exporter provides structured error information:

```yaml
- target: "192.168.1.99"
  resolved_ip: null
  collected_at_utc: "2025-01-15T10:30:45Z"
  success: false
  error:
    kind: "validation"
    message: "Invalid IP address"
    detail: "Invalid IP address: 192.168.1.99"
  server: { ... null values ... }
  peers: []
```

### Error Types

- `validation`: Invalid IP address format
- `timeout`: Command timeout or server unreachable
- `exec`: Execution failure
- `parse`: Parsing error

## Exit Codes

- `0`: All targets succeeded
- `1`: One or more targets failed (YAML still produced for successful targets)
- `130`: Interrupted by user (Ctrl+C)

## Development & Testing

### Running Tests

The project includes a comprehensive test suite with colored output for easy result identification:

```bash
# Run all tests (unit tests + integration tests)
make test-all

# Run only Python unit tests
make check

# Run individual test categories
make test-ipv4-rejects-ipv6
make test-ipv6-rejects-ipv4
make test-hostname-rejection
make test-valid-ip-acceptance
make test-formats
```

#### Test Suite Features

- **Colored Output**: Green ✓ PASS for successful tests, red ✗ FAIL for failures
- **Unified Results**: All 32 tests (25 unit + 7 integration) in single output
- **Comprehensive Coverage**: Unit tests, IP validation, output format validation
- **Real-time Feedback**: Individual test results with clear status indicators

### Generate Examples

```bash
# Generate sample output
make example

# Test with real servers (IP addresses only)
make run SERVERS="192.168.1.1 8.8.8.8"
```

### Makefile Targets

| Target | Description |
|--------|-----------|
| `test-all` | Run complete test suite (unit + integration tests) with colored output |
| `check` | Run Python unit tests with colored output |
| `test` | Alias for `check` |
| `test-ipv4-rejects-ipv6` | Test IPv4-only flag rejects IPv6 addresses |
| `test-ipv6-rejects-ipv4` | Test IPv6-only flag rejects IPv4 addresses |
| `test-hostname-rejection` | Test hostname rejection (IP-only validation) |
| `test-valid-ip-acceptance` | Test valid IP address acceptance |
| `test-formats` | Test JSON and YAML output format validation |
| `example` | Generate sample output using fixtures |
| `run` | Run Python exporter (requires SERVERS variable) |
| `clean` | Remove generated files |

## Security & Operational Notes

### Security Considerations

- **Network Access**: Exporter requires UDP port 123 access to target NTP servers
- **Firewall Rules**: Ensure outbound NTP queries are permitted
- **Input Validation**: Only accepts valid IP addresses (no DNS resolution)
- **File Permissions**: Output files inherit umask; set appropriate permissions

### Operational Considerations

- **Timeouts**: Default 5-second timeout balances responsiveness and reliability
- **Concurrency Limits**: Higher concurrency may overwhelm target servers or network
- **Monitoring**: Non-zero exit codes indicate failures for monitoring integration

## Troubleshooting

### Common Issues

**"Target IP not found in peer table"**

- This is expected behavior when querying a server's own metrics
- The peer table shows servers that the target synchronizes WITH, not the target itself
- Server variables are obtained via `ntpq -c rv` (Mode-6 queries)

**"Mode-6 queries not supported"**

- Some NTP servers disable Mode-6 queries for security
- The exporter automatically falls back to peer-only data collection
- Consider firewall/ACL configuration if Mode-6 support is expected

**Timeout errors**

- Increase timeout with `-t` flag: `./ntp_exporter.py -t 10 target`
- Check network connectivity and firewall rules
- Verify target server is running NTP service

**Invalid IP address errors**

- The exporter only accepts valid IPv4 and IPv6 addresses
- Use IP addresses directly instead of hostnames
- Check IP version filtering with `-4` or `-6` flags

### Debug Mode

```bash
# Remove --quiet flag and check stderr
./ntp_exporter.py 192.168.1.1
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `make test-all`
5. Submit a pull request

## Version History

### v1.0.0 (Current)
- Initial release with comprehensive IP-only NTP metrics collection
- IPv4/IPv6 support with version filtering (`-4`, `-6` flags)
- Mode-6 support detection with graceful fallback
- Structured YAML/JSON output with comprehensive error handling
- Robust test suite with 32 tests and colored output
- Zero external dependencies (Python standard library only)

## License

BSD 3-Clause License - see LICENSE file for details.
