#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025, ProNetivity Inc., Philippines

"""
NTP Service Metrics Exporter (Python implementation)

Queries NTP servers via ntpq and exports metrics in YAML or JSON format.
Features IP-only operation (no DNS resolution), IPv4/IPv6 filtering, 
concurrent queries, and structured error handling.

Key Features:
- IP address validation with IPv4/IPv6 filtering (-4/-6 flags)
- Concurrent NTP server querying with timeout management
- Structured YAML/JSON output with comprehensive error reporting
- Mode-6 support detection with graceful fallback
- Comprehensive test suite with colored output (run: make test-all)

Developed by ProNetivity Inc., Philippines.
"""

import argparse
import concurrent.futures
import datetime
import ipaddress
import json
import os
import re
import socket
import subprocess
import sys
from typing import Dict, List, Optional, Union, Any


class YAMLEmitter:
    """Minimal YAML emitter for the fixed schema without external dependencies."""
    
    @staticmethod
    def _escape_string(s: str) -> str:
        """Escape string for YAML output."""
        if not s:
            return '""'
        # Check if we need quotes
        needs_quotes = (
            ' ' in s or s.startswith(' ') or s.endswith(' ') or
            ':' in s or '#' in s or '\n' in s or '\t' in s or
            s in ('true', 'false', 'null', 'True', 'False', 'None') or
            s.startswith('*') or s.startswith('&') or s.startswith('!') or
            s.isdigit() or
            (s.replace('.', '').replace('-', '').isdigit())
        )
        
        if needs_quotes:
            # Escape quotes and backslashes
            escaped = s.replace('\\', '\\\\').replace('"', '\\"')
            return f'"{escaped}"'
        return s
    
    @staticmethod
    def _emit_value(value: Any, indent: int = 0, is_root: bool = False) -> str:
        """Emit a YAML value with proper formatting."""
        if value is None:
            return 'null'
        elif isinstance(value, bool):
            return 'true' if value else 'false'
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, str):
            return YAMLEmitter._escape_string(value)
        elif isinstance(value, list):
            if not value:
                return '[]'
            result = []
            for item in value:
                if isinstance(item, dict):
                    # For dict items in list, we need special formatting
                    # Each dict key-value pair needs to be indented properly
                    dict_lines = []
                    for key, val in item.items():
                        val_yaml = YAMLEmitter._emit_value(val, indent + 4)
                        if isinstance(val, (dict, list)) and val:
                            dict_lines.append(f"{' ' * (indent + 2)}{key}:{val_yaml}")
                        else:
                            dict_lines.append(f"{' ' * (indent + 2)}{key}: {val_yaml}")
                    
                    if dict_lines:
                        # First line gets the dash
                        result.append(f"{' ' * indent}-{dict_lines[0][indent+1:]}")
                        # Subsequent lines get proper indentation
                        for line in dict_lines[1:]:
                            result.append(line)
                else:
                    item_yaml = YAMLEmitter._emit_value(item, indent + 2)
                    result.append(f"{' ' * indent}- {item_yaml}")
            if is_root:
                return '\n'.join(result)
            else:
                return '\n' + '\n'.join(result)
        elif isinstance(value, dict):
            if not value:
                return '{}'
            result = []
            for key, val in value.items():
                val_yaml = YAMLEmitter._emit_value(val, indent + 2)
                if isinstance(val, (dict, list)) and val:
                    result.append(f"{' ' * indent}{key}:{val_yaml}")
                else:
                    result.append(f"{' ' * indent}{key}: {val_yaml}")
            return '\n' + '\n'.join(result)
        else:
            return YAMLEmitter._escape_string(str(value))
    
    @staticmethod
    def emit(data: Any) -> str:
        """Emit YAML for the given data structure."""
        if isinstance(data, list):
            return YAMLEmitter._emit_value(data, is_root=True)
        else:
            return YAMLEmitter._emit_value(data).lstrip()


class NTPExporter:
    """Main NTP metrics exporter class."""
    
    def __init__(self, timeout: int = 5, max_jobs: int = 8, quiet: bool = False, output_format: str = 'yaml', ip_version: str = 'both'):
        self.timeout = timeout
        self.max_jobs = max_jobs
        self.quiet = quiet
        self.output_format = output_format
        self.ip_version = ip_version  # 'ipv4', 'ipv6', or 'both'
        self.env = dict(os.environ)
        self.env.update({'LC_ALL': 'C', 'LANG': 'C'})
    
    def _log_error(self, message: str, fatal: bool = False):
        """Log error message to stderr if not quiet or if fatal."""
        if not self.quiet or fatal:
            print(f"ERROR: {message}", file=sys.stderr)
    
    def _log_warning(self, message: str):
        """Log warning message to stderr if not quiet."""
        if not self.quiet:
            print(f"WARNING: {message}", file=sys.stderr)
    
    def _log_info(self, message: str):
        """Log info message to stdout."""
        print(f"INFO: {message}")
    
    def _test_mode6_support(self, ip: str) -> bool:
        """Test if server supports Mode-6 queries with a quick timeout."""
        try:
            # Use a shorter timeout for the test
            result = subprocess.run(
                ['ntpq', '-c', 'rv', ip],
                capture_output=True,
                text=True,
                timeout=2,  # Shorter timeout for testing
                env=self.env,
                check=False
            )
            return result.returncode == 0 and result.stdout.strip()
        except subprocess.TimeoutExpired:
            return False
        except Exception:
            return False
    
    def _is_valid_ip(self, addr: str) -> bool:
        """Check if string is a valid IP address."""
        try:
            ip_obj = ipaddress.ip_address(addr)
            # Apply IP version filtering
            if self.ip_version == 'ipv4' and not isinstance(ip_obj, ipaddress.IPv4Address):
                return False
            elif self.ip_version == 'ipv6' and not isinstance(ip_obj, ipaddress.IPv6Address):
                return False
            return True
        except ValueError:
            return False
    
    def _validate_ip_target(self, target: str) -> str:
        """Validate that target is a valid IP address and return it."""
        if not self._is_valid_ip(target):
            raise ValueError(f"Invalid IP address: {target}")
        return target
    
    def _empty_server_data(self) -> Dict[str, Any]:
        """Return empty server data structure."""
        return {
            'reference_id': None,
            'stratum': None,
            'reftime_utc': None,
            'system_time': None,
            'last_offset': None,
            'rms_offset': None,
            'frequency': None,
            'residual_frequency': None,
            'skew': None,
            'root_delay': None,
            'root_dispersion': None,
            'update_interval': None,
            'leap_status': {
                'code': None,
                'meaning': None
            },
            'source_state': None
        }
    
    def _run_ntpq_command(self, ip: str, command: str) -> Optional[str]:
        """Run ntpq command with timeout and return output."""
        try:
            result = subprocess.run(
                ['ntpq', '-c', command, ip],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=self.env,
                check=False
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return None
                
        except subprocess.TimeoutExpired:
            return None
        except Exception as e:
            return None
    
    def _parse_rv_output(self, output: str) -> Dict[str, Any]:
        """Parse ntpq -c rv output into structured data."""
        server_data = {
            'reference_id': None,
            'stratum': None,
            'reftime_utc': None,
            'system_time': None,
            'last_offset': None,
            'rms_offset': None,
            'frequency': None,
            'residual_frequency': None,
            'skew': None,
            'root_delay': None,
            'root_dispersion': None,
            'update_interval': None,
            'leap_status': {'code': None, 'meaning': None},
            'source_state': None
        }
        
        if not output:
            return server_data
        
        # Parse key=value pairs from rv output
        # Handle both space and comma separated values
        pairs = {}
        for line in output.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Split on commas and spaces, but preserve values
            # Use regex to find key=value pairs, handling various value formats
            pattern = r'(\w+)=([^,\s]+(?:\.[^,\s]*)*|[A-Z]+|\d+\.\d+)'
            matches = re.findall(pattern, line)
            for key, value in matches:
                pairs[key.strip()] = value.strip()
            
            # Also handle comma-separated pairs more carefully
            if ',' in line:
                parts = line.split(',')
                for part in parts:
                    part = part.strip()
                    if '=' in part:
                        key, value = part.split('=', 1)
                        pairs[key.strip()] = value.strip()
        
        # Map fields to our schema
        if 'refid' in pairs:
            server_data['reference_id'] = pairs['refid']
        
        if 'stratum' in pairs:
            try:
                server_data['stratum'] = int(pairs['stratum'])
            except ValueError:
                pass
        
        if 'reftime' in pairs:
            # Try to convert NTP timestamp to ISO-8601
            try:
                # NTP epoch starts at 1900-01-01, Unix epoch at 1970-01-01
                if pairs['reftime'].startswith('0x'):
                    ntp_timestamp = int(pairs['reftime'], 16)
                else:
                    ntp_timestamp = float(pairs['reftime'])
                # Convert from NTP epoch (1900) to Unix epoch (1970)
                unix_timestamp = ntp_timestamp - 2208988800
                dt = datetime.datetime.fromtimestamp(unix_timestamp, tz=datetime.timezone.utc)
                server_data['reftime_utc'] = dt.isoformat().replace('+00:00', 'Z')
            except (ValueError, OSError):
                server_data['reftime_utc'] = pairs['reftime']
        
        # Look for system time in various fields
        for field in ['clock', 'system', 'time']:
            if field in pairs:
                server_data['system_time'] = pairs[field]
                break
        
        if 'offset' in pairs:
            try:
                server_data['last_offset'] = float(pairs['offset'])
            except ValueError:
                pass
        
        if 'rms_offset' in pairs:
            try:
                server_data['rms_offset'] = float(pairs['rms_offset'])
            except ValueError:
                pass
        
        if 'frequency' in pairs:
            try:
                server_data['frequency'] = float(pairs['frequency'])
            except ValueError:
                pass
        
        if 'residual' in pairs:
            try:
                server_data['residual_frequency'] = float(pairs['residual'])
            except ValueError:
                pass
        
        if 'skew' in pairs:
            try:
                server_data['skew'] = float(pairs['skew'])
            except ValueError:
                pass
        
        if 'rootdelay' in pairs:
            try:
                server_data['root_delay'] = float(pairs['rootdelay'])
            except ValueError:
                pass
        
        if 'rootdisp' in pairs:
            try:
                server_data['root_dispersion'] = float(pairs['rootdisp'])
            except ValueError:
                pass
        
        if 'tc' in pairs:
            try:
                server_data['update_interval'] = int(pairs['tc'])
            except ValueError:
                pass
        
        # Parse leap status
        if 'leap' in pairs:
            leap_code = pairs['leap']
            server_data['leap_status']['code'] = leap_code
            leap_meanings = {
                '00': 'none',
                '01': 'add_sec',
                '10': 'del_sec',
                '11': 'alarm'
            }
            server_data['leap_status']['meaning'] = leap_meanings.get(leap_code)
        
        # Look for source state
        for field in pairs:
            if field.startswith('sync_') or field == 'state':
                server_data['source_state'] = pairs[field]
                break
        
        return server_data
    
    def _parse_peers_output(self, output: str) -> List[Dict[str, Any]]:
        """Parse ntpq -np output into list of peer data."""
        peers = []
        
        if not output:
            return peers
        
        lines = output.strip().split('\n')
        
        # Skip header lines
        data_lines = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith('remote') or line.startswith('='):
                continue
            data_lines.append(line)
        
        for line in data_lines:
            if not line:
                continue
            
            # Parse peer line: marker + remote refid st t when poll reach delay offset jitter
            peer_data = {
                'name_or_ip': None,
                'refid': None,
                'source_stratum': None,
                'type': None,
                'poll_interval': None,
                'reachability': None,
                'last_sample_when': None,
                'offset': None,
                'delay': None,
                'jitter': None,
                'selected_marker': None
            }
            
            # Extract marker (first character)
            marker = line[0] if line and line[0] in '*+-#ox. ' else None
            if marker and marker != ' ':
                peer_data['selected_marker'] = marker
            
            # Remove marker and split remaining fields
            remaining = line[1:].strip() if len(line) > 1 else line
            fields = remaining.split()
            
            if len(fields) >= 1:
                peer_data['name_or_ip'] = fields[0]
            
            if len(fields) >= 2:
                peer_data['refid'] = fields[1] if fields[1] != '-' else None
            
            if len(fields) >= 3:
                try:
                    peer_data['source_stratum'] = int(fields[2]) if fields[2] != '-' else None
                except ValueError:
                    pass
            
            if len(fields) >= 4:
                peer_data['type'] = fields[3] if fields[3] != '-' else None
            
            if len(fields) >= 5:
                when_field = fields[4]
                if when_field != '-':
                    try:
                        peer_data['last_sample_when'] = int(when_field)
                    except ValueError:
                        peer_data['last_sample_when'] = when_field
            
            if len(fields) >= 6:
                try:
                    peer_data['poll_interval'] = int(fields[5]) if fields[5] != '-' else None
                except ValueError:
                    pass
            
            if len(fields) >= 7:
                try:
                    # Reachability is octal
                    reach_str = fields[6]
                    if reach_str != '-':
                        peer_data['reachability'] = int(reach_str, 8) if reach_str.isdigit() else int(reach_str, 16)
                except ValueError:
                    pass
            
            if len(fields) >= 8:
                try:
                    peer_data['delay'] = float(fields[7]) if fields[7] != '-' else None
                except ValueError:
                    pass
            
            if len(fields) >= 9:
                try:
                    peer_data['offset'] = float(fields[8]) if fields[8] != '-' else None
                except ValueError:
                    pass
            
            if len(fields) >= 10:
                try:
                    peer_data['jitter'] = float(fields[9]) if fields[9] != '-' else None
                except ValueError:
                    pass
            
            peers.append(peer_data)
        
        return peers
    
    def _query_target(self, target: str, resolved_ip: str) -> Dict[str, Any]:
        """Query a single NTP target and return structured results."""
        collected_at = datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00', 'Z')
        
        result = {
            'target': target,
            'resolved_ip': resolved_ip,
            'collected_at_utc': collected_at,
            'success': False,
            'error': None,
            'server': {
                'reference_id': None,
                'stratum': None,
                'reftime_utc': None,
                'system_time': None,
                'last_offset': None,
                'rms_offset': None,
                'frequency': None,
                'residual_frequency': None,
                'skew': None,
                'root_delay': None,
                'root_dispersion': None,
                'update_interval': None,
                'leap_status': {'code': None, 'meaning': None},
                'source_state': None
            },
            'peers': []
        }
        
        # Test Mode-6 support first
        mode6_supported = self._test_mode6_support(resolved_ip)
        
        rv_output = None
        if mode6_supported:
            # Query server variables
            rv_output = self._run_ntpq_command(resolved_ip, 'rv')
        else:
            pass  # Silently skip Mode-6 queries if not supported
        
        # Always try to query peers
        peers_output = self._run_ntpq_command(resolved_ip, 'peers -n')
        if peers_output is None:
            peers_output = ""  # Use empty string so we can still parse server data
        
        # Parse results
        try:
            if rv_output:
                result['server'] = self._parse_rv_output(rv_output)
            else:
                result['server'] = self._parse_rv_output('')  # Empty server data
            result['peers'] = self._parse_peers_output(peers_output)
            
            # Only mark as success if we got some useful data
            if rv_output or peers_output:
                result['success'] = True
            else:
                result['error'] = {
                    'kind': 'timeout',
                    'message': 'Server not responding',
                    'detail': f'No response from {resolved_ip}'
                }
        except Exception as e:
            result['error'] = {
                'kind': 'parse',
                'message': 'Failed to parse ntpq output',
                'detail': str(e)
            }
        
        return result
    
    def _process_single_target(self, target: str) -> Dict[str, Any]:
        """Process a single target (IP address only) and return result."""
        try:
            # Validate that target is a valid IP address
            validated_ip = self._validate_ip_target(target)
            return self._query_target(target, validated_ip)
        except ValueError as e:
            return {
                'target': target,
                'resolved_ip': None,
                'collected_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'success': False,
                'error': {
                    'kind': 'validation',
                    'message': 'Invalid IP address',
                    'detail': str(e)
                },
                'server': self._empty_server_data(),
                'peers': []
            }
    
    def export_metrics(self, targets: List[str]) -> List[Dict[str, Any]]:
        """Export metrics for all targets with concurrent processing."""
        results = []
        
        if self.max_jobs == 1:
            # Sequential processing
            for target in targets:
                results.append(self._process_single_target(target))
        else:
            # Concurrent processing
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_jobs) as executor:
                future_to_target = {
                    executor.submit(self._process_single_target, target): target
                    for target in targets
                }
                
                for future in concurrent.futures.as_completed(future_to_target):
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        target = future_to_target[future]
                        self._log_error(f"Unexpected error processing {target}: {e}")
                        # Add failed result
                        collected_at = datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00', 'Z')
                        results.append({
                            'target': target,
                            'resolved_ip': None,
                            'collected_at_utc': collected_at,
                            'success': False,
                            'error': {
                                'kind': 'exec',
                                'message': 'Unexpected error',
                                'detail': str(e)
                            },
                            'server': {
                                'reference_id': None,
                                'stratum': None,
                                'reftime_utc': None,
                                'system_time': None,
                                'last_offset': None,
                                'rms_offset': None,
                                'frequency': None,
                                'residual_frequency': None,
                                'skew': None,
                                'root_delay': None,
                                'root_dispersion': None,
                                'update_interval': None,
                                'leap_status': {'code': None, 'meaning': None},
                                'source_state': None
                            },
                            'peers': []
                        })
        
        # Sort results to match input order
        target_order = {target: i for i, target in enumerate(targets)}
        results.sort(key=lambda x: target_order.get(x['target'], len(targets)))
        
        return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='NTP Service Metrics Exporter - Query NTP servers and output structured metrics',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s 192.168.1.1
  %(prog)s --timeout 10 --jobs 4 192.168.1.1 10.0.0.1
  %(prog)s --json --quiet 8.8.8.8
  %(prog)s -4 192.168.1.1  # IPv4 only
  %(prog)s -6 2001:4860:4860::8888  # IPv6 only
  %(prog)s --help

For more information, see the README.md file.
        """
    )
    
    parser.add_argument('targets', nargs='+', help='NTP server IP addresses to query')
    parser.add_argument('--timeout', '-t', type=int, default=5, 
                       help='Timeout in seconds for ntpq commands (default: 5)')
    parser.add_argument('--jobs', '-j', type=int, default=8,
                       help='Maximum concurrent jobs (default: 8)')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Suppress warning messages')
    parser.add_argument('--json', action='store_true',
                       help='Output in JSON format instead of YAML')
    parser.add_argument('--output-file', '-o', type=str,
                       help='Write output to file instead of stdout')
    
    # IP version selection (mutually exclusive)
    ip_group = parser.add_mutually_exclusive_group()
    ip_group.add_argument('-4', '--ipv4', action='store_const', const='ipv4', dest='ip_version',
                         help='Use IPv4 addresses only')
    ip_group.add_argument('-6', '--ipv6', action='store_const', const='ipv6', dest='ip_version',
                         help='Use IPv6 addresses only')
    
    args = parser.parse_args()
    
    # Default to 'both' if no IP version specified
    ip_version = args.ip_version or 'both'
    
    # Validate arguments
    if args.timeout < 1:
        print("ERROR: Timeout must be at least 1 second", file=sys.stderr)
        sys.exit(1)
    
    if args.jobs < 1:
        print("ERROR: Jobs must be at least 1", file=sys.stderr)
        sys.exit(1)
    
    # Create exporter and run
    output_format = 'json' if args.json else 'yaml'
    exporter = NTPExporter(
        timeout=args.timeout,
        max_jobs=args.jobs,
        quiet=args.quiet,
        output_format=output_format,
        ip_version=ip_version
    )
    
    try:
        results = exporter.export_metrics(args.targets)
        
        # Generate output in requested format
        if args.json:
            output_data = json.dumps(results, indent=2, ensure_ascii=False)
        else:
            output_data = YAMLEmitter.emit(results)
        
        # Write output
        if args.output_file:
            try:
                with open(args.output_file, 'w') as f:
                    f.write(output_data)
                    f.write('\n')
            except IOError as e:
                print(f"ERROR: Failed to write to {args.output_file}: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            print(output_data)
        
        # Exit with error code if any target failed
        if any(not result['success'] for result in results):
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
