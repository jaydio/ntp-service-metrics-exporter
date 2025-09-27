#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause

"""
Unit tests for NTP exporter parsing functions.

This comprehensive test suite includes:
- YAML emission and validation tests
- NTP parsing functionality tests  
- IP address validation and filtering tests
- Output format validation (JSON/YAML)
- Integration tests with mock data

Run with: make check (unit tests only) or make test-all (complete suite)
Test output includes colored indicators for easy result identification.
"""

import sys
import os
import unittest
import json
from unittest.mock import patch, MagicMock

# Add the parent directory to the path to import the module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from ntp_exporter import YAMLEmitter, NTPExporter

# Try to import PyYAML for validation tests
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


class TestYAMLEmitter(unittest.TestCase):
    """Test YAML emission functionality."""
    
    def test_emit_simple_values(self):
        """Test emission of simple values."""
        self.assertEqual(YAMLEmitter.emit(None), 'null')
        self.assertEqual(YAMLEmitter.emit(True), 'true')
        self.assertEqual(YAMLEmitter.emit(False), 'false')
        self.assertEqual(YAMLEmitter.emit(42), '42')
        self.assertEqual(YAMLEmitter.emit(3.14), '3.14')
        self.assertEqual(YAMLEmitter.emit('hello'), 'hello')
        self.assertEqual(YAMLEmitter.emit('hello world'), '"hello world"')
    
    def test_emit_list(self):
        """Test emission of lists."""
        # Empty list
        self.assertEqual(YAMLEmitter.emit([]), '[]')
        
        # Simple list
        result = YAMLEmitter.emit(['a', 'b', 'c'])
        expected = '- a\n- b\n- c'
        self.assertEqual(result, expected)
        
        # List with dict items
        data = [{'name': 'test', 'value': 42}]
        result = YAMLEmitter.emit(data)
        self.assertIn('- name: test', result)
        self.assertIn('  value: 42', result)
    
    def test_emit_dict(self):
        """Test emission of dictionaries."""
        # Empty dict
        self.assertEqual(YAMLEmitter.emit({}), '{}')
        
        # Simple dict
        result = YAMLEmitter.emit({'key': 'value', 'number': 42})
        self.assertIn('key: value', result)
        self.assertIn('number: 42', result)
    
    @unittest.skipUnless(HAS_YAML, "PyYAML not available")
    def test_yaml_validation(self):
        """Test that emitted YAML is valid and parseable."""
        # Test various data structures
        test_cases = [
            [],
            [{'target': 'test.com', 'success': True, 'peers': []}],
            [{'target': 'test.com', 'server': {'stratum': 2}, 'peers': [{'name': 'peer1'}]}],
            {'simple': 'value', 'nested': {'key': 'value'}},
        ]
        
        for data in test_cases:
            with self.subTest(data=data):
                yaml_output = YAMLEmitter.emit(data)
                # Should parse without error
                parsed = yaml.safe_load(yaml_output)
                # Should round-trip correctly
                self.assertEqual(parsed, data)


class TestOutputValidation(unittest.TestCase):
    """Test output format validation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.sample_data = [
            {
                'target': 'test.example.com',
                'resolved_ip': '192.168.1.1',
                'collected_at_utc': '2025-01-15T10:30:45Z',
                'success': True,
                'error': None,
                'server': {
                    'reference_id': 'GPS',
                    'stratum': 1,
                    'reftime_utc': '2025-01-15T10:30:42Z',
                    'system_time': '0xe6c5a8c2.8f5c28f6',
                    'last_offset': 0.123,
                    'rms_offset': None,
                    'frequency': -15.123,
                    'residual_frequency': None,
                    'skew': None,
                    'root_delay': 0.000,
                    'root_dispersion': 0.001,
                    'update_interval': 4,
                    'leap_status': {
                        'code': '00',
                        'meaning': 'none'
                    },
                    'source_state': None
                },
                'peers': [
                    {
                        'name_or_ip': 'time1.google.com',
                        'refid': '.GOOG.',
                        'source_stratum': 1,
                        'type': 'u',
                        'poll_interval': 64,
                        'reachability': 255,
                        'last_sample_when': 64,
                        'offset': -0.123,
                        'delay': 1.234,
                        'jitter': 0.456,
                        'selected_marker': '*'
                    }
                ]
            }
        ]
    
    @unittest.skipUnless(HAS_YAML, "PyYAML not available")
    def test_yaml_output_validation(self):
        """Test that YAML output is valid."""
        exporter = NTPExporter(output_format='yaml')
        yaml_output = YAMLEmitter.emit(self.sample_data)
        
        # Should parse without error
        parsed = yaml.safe_load(yaml_output)
        self.assertIsInstance(parsed, list)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]['target'], 'test.example.com')
    
    def test_json_output_validation(self):
        """Test that JSON output is valid."""
        exporter = NTPExporter(output_format='json')
        json_output = json.dumps(self.sample_data, indent=2)
        
        # Should parse without error
        parsed = json.loads(json_output)
        self.assertIsInstance(parsed, list)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]['target'], 'test.example.com')
    
    def test_output_format_integration(self):
        """Test output format integration with mock data."""
        with patch.object(NTPExporter, '_query_target') as mock_query:
            mock_query.return_value = self.sample_data[0]
            
            # Test YAML format
            exporter = NTPExporter(output_format='yaml', timeout=1)
            results = exporter.export_metrics(['test.com'])
            yaml_output = YAMLEmitter.emit(results)
            
            if HAS_YAML:
                parsed_yaml = yaml.safe_load(yaml_output)
                self.assertIsInstance(parsed_yaml, list)
            
            # Test JSON format
            exporter = NTPExporter(output_format='json', timeout=1)
            results = exporter.export_metrics(['test.com'])
            json_output = json.dumps(results, indent=2)
            
            parsed_json = json.loads(json_output)
            self.assertIsInstance(parsed_json, list)
    
    def test_emit_list(self):
        """Test emission of lists."""
        result = YAMLEmitter.emit([1, 2, 3])
        expected = """
- 1
- 2
- 3""".strip()
        self.assertEqual(result, expected)
    
    def test_emit_dict(self):
        """Test emission of dictionaries."""
        data = {'key1': 'value1', 'key2': 42}
        result = YAMLEmitter.emit(data)
        self.assertIn('key1: value1', result)
        self.assertIn('key2: 42', result)


class TestNTPExporter(unittest.TestCase):
    """Test NTP exporter functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.exporter = NTPExporter(timeout=5, max_jobs=1, quiet=True)
    
    def test_is_valid_ip(self):
        """Test IP address validation."""
        self.assertTrue(self.exporter._is_valid_ip('192.168.1.1'))
        self.assertTrue(self.exporter._is_valid_ip('::1'))
        self.assertTrue(self.exporter._is_valid_ip('2001:db8::1'))
        self.assertFalse(self.exporter._is_valid_ip('example.com'))
        self.assertFalse(self.exporter._is_valid_ip('not-an-ip'))
    
    def test_validate_ip_target(self):
        """Test IP target validation."""
        # Valid IPs should return the same IP
        self.assertEqual(self.exporter._validate_ip_target('192.168.1.1'), '192.168.1.1')
        self.assertEqual(self.exporter._validate_ip_target('::1'), '::1')
        
        # Invalid IPs should raise ValueError
        with self.assertRaises(ValueError):
            self.exporter._validate_ip_target('example.com')
        with self.assertRaises(ValueError):
            self.exporter._validate_ip_target('not-an-ip')
    
    def test_parse_rv_output_complete(self):
        """Test parsing complete rv output."""
        rv_output = """associd=0 status=0615 leap=00, sync=4, clock=3, refid=GPS, stratum=1, rootdelay=0.000, rootdisp=0.001, reftime=0xe6c5a8b2.8f5c28f6, clock=0xe6c5a8c2.8f5c28f6, peer=12345, tc=4, mintc=3, offset=0.123, frequency=-15.123, sys_jitter=0.456, clk_jitter=0.789, clk_wander=0.012"""
        
        result = self.exporter._parse_rv_output(rv_output)
        
        self.assertEqual(result['reference_id'], 'GPS')
        self.assertEqual(result['stratum'], 1)
        self.assertEqual(result['last_offset'], 0.123)
        self.assertEqual(result['frequency'], -15.123)
        self.assertEqual(result['root_delay'], 0.000)
        self.assertEqual(result['root_dispersion'], 0.001)
        self.assertEqual(result['update_interval'], 4)
        self.assertEqual(result['leap_status']['code'], '00')
        self.assertEqual(result['leap_status']['meaning'], 'none')
    
    def test_parse_rv_output_partial(self):
        """Test parsing partial rv output."""
        rv_output = """associd=0 status=0615 leap=00, sync=4, refid=GPS, stratum=1, rootdelay=0.000"""
        
        result = self.exporter._parse_rv_output(rv_output)
        
        self.assertEqual(result['reference_id'], 'GPS')
        self.assertEqual(result['stratum'], 1)
        self.assertEqual(result['root_delay'], 0.000)
        self.assertIsNone(result['frequency'])
        self.assertIsNone(result['last_offset'])
    
    def test_parse_rv_output_empty(self):
        """Test parsing empty rv output."""
        result = self.exporter._parse_rv_output('')
        
        self.assertIsNone(result['reference_id'])
        self.assertIsNone(result['stratum'])
        self.assertIsNone(result['last_offset'])
    
    def test_parse_peers_output_complete(self):
        """Test parsing complete peers output."""
        peers_output = """     remote           refid      st t when poll reach   delay   offset  jitter
==============================================================================
*216.239.35.0    .GOOG.           1 u   64   64  377    1.234   -0.123   0.456
+216.239.35.4    .GOOG.           1 u   32   64  377    2.345    0.234   0.567
-192.168.1.10    .POOL.          16 p    -   64    0    0.000    0.000   0.000
 10.0.0.1        192.168.1.1      2 u  128  256  377   12.345   -1.234   2.345"""
        
        result = self.exporter._parse_peers_output(peers_output)
        
        self.assertEqual(len(result), 4)
        
        # Check first peer (selected)
        peer1 = result[0]
        self.assertEqual(peer1['name_or_ip'], '216.239.35.0')
        self.assertEqual(peer1['refid'], '.GOOG.')
        self.assertEqual(peer1['source_stratum'], 1)
        self.assertEqual(peer1['selected_marker'], '*')
        self.assertEqual(peer1['offset'], -0.123)
        self.assertEqual(peer1['delay'], 1.234)
        self.assertEqual(peer1['jitter'], 0.456)
        
        # Check second peer (candidate)
        peer2 = result[1]
        self.assertEqual(peer2['selected_marker'], '+')
        
        # Check third peer (discarded)
        peer3 = result[2]
        self.assertEqual(peer3['selected_marker'], '-')
        
        # Check fourth peer (no marker)
        peer4 = result[3]
        self.assertIsNone(peer4['selected_marker'])
    
    def test_parse_peers_output_empty(self):
        """Test parsing empty peers output."""
        result = self.exporter._parse_peers_output('')
        self.assertEqual(result, [])
    
    def test_ip_version_filtering(self):
        """Test IP version filtering."""
        # Test IPv4-only exporter
        ipv4_exporter = NTPExporter(ip_version='ipv4')
        self.assertTrue(ipv4_exporter._is_valid_ip('192.168.1.1'))
        self.assertFalse(ipv4_exporter._is_valid_ip('::1'))
        
        # Test IPv6-only exporter
        ipv6_exporter = NTPExporter(ip_version='ipv6')
        self.assertFalse(ipv6_exporter._is_valid_ip('192.168.1.1'))
        self.assertTrue(ipv6_exporter._is_valid_ip('::1'))
    
    def test_ipv4_only_rejects_ipv6(self):
        """Test that -4 flag rejects IPv6 addresses with proper error."""
        ipv4_exporter = NTPExporter(ip_version='ipv4', quiet=True)
        result = ipv4_exporter._process_single_target('::1')
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error']['kind'], 'validation')
        self.assertEqual(result['error']['message'], 'Invalid IP address')
        self.assertIn('Invalid IP address: ::1', result['error']['detail'])
        self.assertEqual(result['target'], '::1')
        self.assertIsNone(result['resolved_ip'])
    
    def test_ipv6_only_rejects_ipv4(self):
        """Test that -6 flag rejects IPv4 addresses with proper error."""
        ipv6_exporter = NTPExporter(ip_version='ipv6', quiet=True)
        result = ipv6_exporter._process_single_target('192.168.1.1')
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error']['kind'], 'validation')
        self.assertEqual(result['error']['message'], 'Invalid IP address')
        self.assertIn('Invalid IP address: 192.168.1.1', result['error']['detail'])
        self.assertEqual(result['target'], '192.168.1.1')
        self.assertIsNone(result['resolved_ip'])


class TestOutputFormats(unittest.TestCase):
    """Test output format validation using same modules as the script."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.sample_data = [
            {
                'target': '192.168.1.1',
                'resolved_ip': '192.168.1.1',
                'collected_at_utc': '2025-01-15T10:30:45Z',
                'success': True,
                'error': None,
                'server': {
                    'reference_id': 'GPS',
                    'stratum': 1,
                    'reftime_utc': '2025-01-15T10:30:42Z',
                    'system_time': '0xe6c5a8c2.8f5c28f6',
                    'last_offset': 0.123,
                    'rms_offset': None,
                    'frequency': -15.123,
                    'residual_frequency': None,
                    'skew': None,
                    'root_delay': 46.875,
                    'root_dispersion': 25.624,
                    'update_interval': 9,
                    'leap_status': {
                        'code': '00',
                        'meaning': 'none'
                    },
                    'source_state': None
                },
                'peers': [
                    {
                        'name_or_ip': 'time.google.com',
                        'refid': '.GOOG.',
                        'source_stratum': 1,
                        'type': 'u',
                        'poll_interval': 512,
                        'reachability': 255,
                        'last_sample_when': 25,
                        'offset': 16.793,
                        'delay': 79.064,
                        'jitter': 0.64,
                        'selected_marker': '*'
                    }
                ]
            }
        ]
    
    def test_json_output_format_validation(self):
        """Test JSON output format using json module (same as script)."""
        # Generate JSON output using same method as script
        json_output = json.dumps(self.sample_data, indent=2, ensure_ascii=False)
        
        # Validate it can be parsed back
        parsed_data = json.loads(json_output)
        
        # Verify structure
        self.assertIsInstance(parsed_data, list)
        self.assertEqual(len(parsed_data), 1)
        
        entry = parsed_data[0]
        self.assertEqual(entry['target'], '192.168.1.1')
        self.assertEqual(entry['success'], True)
        self.assertIsNone(entry['error'])
        self.assertIsInstance(entry['server'], dict)
        self.assertIsInstance(entry['peers'], list)
        
        # Verify server data
        server = entry['server']
        self.assertEqual(server['reference_id'], 'GPS')
        self.assertEqual(server['stratum'], 1)
        self.assertEqual(server['last_offset'], 0.123)
        
        # Verify peer data
        self.assertEqual(len(entry['peers']), 1)
        peer = entry['peers'][0]
        self.assertEqual(peer['name_or_ip'], 'time.google.com')
        self.assertEqual(peer['selected_marker'], '*')
    
    def test_yaml_output_format_validation(self):
        """Test YAML output format using YAMLEmitter (same as script)."""
        # Generate YAML output using same method as script
        yaml_output = YAMLEmitter.emit(self.sample_data)
        
        # Validate YAML structure by parsing lines
        lines = yaml_output.strip().split('\n')
        self.assertTrue(any('target: "192.168.1.1"' in line for line in lines))
        self.assertTrue(any('success: true' in line for line in lines))
        self.assertTrue(any('reference_id: GPS' in line for line in lines))
        self.assertTrue(any('stratum: 1' in line for line in lines))
        
        # Test that it doesn't contain invalid YAML constructs
        self.assertNotIn('{{', yaml_output)
        self.assertNotIn('}}', yaml_output)
        
        # Verify proper indentation (should start with -)
        self.assertTrue(yaml_output.startswith('- target:'))
    
    @unittest.skipUnless(HAS_YAML, "PyYAML not available")
    def test_yaml_output_pyaml_validation(self):
        """Test YAML output can be parsed by PyYAML if available."""
        yaml_output = YAMLEmitter.emit(self.sample_data)
        
        # Parse with PyYAML to ensure it's valid YAML
        parsed_data = yaml.safe_load(yaml_output)
        
        # Verify structure matches original
        self.assertIsInstance(parsed_data, list)
        self.assertEqual(len(parsed_data), 1)
        
        entry = parsed_data[0]
        self.assertEqual(entry['target'], '192.168.1.1')
        self.assertEqual(entry['success'], True)
        self.assertIsNone(entry['error'])
        
        # Verify round-trip consistency
        self.assertEqual(entry['server']['reference_id'], 'GPS')
        self.assertEqual(entry['server']['stratum'], 1)
        self.assertEqual(entry['peers'][0]['selected_marker'], '*')
    
    def test_error_output_format_validation(self):
        """Test error output format validation."""
        error_data = [
            {
                'target': 'invalid.hostname',
                'resolved_ip': None,
                'collected_at_utc': '2025-01-15T10:30:45Z',
                'success': False,
                'error': {
                    'kind': 'validation',
                    'message': 'Invalid IP address',
                    'detail': 'Invalid IP address: invalid.hostname'
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
                    'leap_status': {
                        'code': None,
                        'meaning': None
                    },
                    'source_state': None
                },
                'peers': []
            }
        ]
        
        # Test JSON format
        json_output = json.dumps(error_data, indent=2, ensure_ascii=False)
        parsed_json = json.loads(json_output)
        self.assertEqual(parsed_json[0]['error']['message'], 'Invalid IP address')
        
        # Test YAML format
        yaml_output = YAMLEmitter.emit(error_data)
        self.assertIn('Invalid IP address', yaml_output)
        self.assertIn('success: false', yaml_output)


class TestIntegration(unittest.TestCase):
    """Integration tests using test fixtures."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = os.path.join(os.path.dirname(__file__), '..', 'test_inputs')
    
    def test_parse_rv_fixture(self):
        """Test parsing rv fixture file."""
        exporter = NTPExporter(quiet=True)
        
        with open(os.path.join(self.test_dir, 'rv_ok.txt'), 'r') as f:
            rv_data = f.read()
        
        result = exporter._parse_rv_output(rv_data)
        
        self.assertEqual(result['reference_id'], 'GPS')
        self.assertEqual(result['stratum'], 1)
        self.assertEqual(result['last_offset'], 0.123)
    
    def test_parse_peers_fixture(self):
        """Test parsing peers fixture file."""
        exporter = NTPExporter(quiet=True)
        
        with open(os.path.join(self.test_dir, 'peers_np_ok.txt'), 'r') as f:
            peers_data = f.read()
        
        result = exporter._parse_peers_output(peers_data)
        
        self.assertEqual(len(result), 4)
        self.assertEqual(result[0]['selected_marker'], '*')
        self.assertEqual(result[1]['selected_marker'], '+')


if __name__ == '__main__':
    unittest.main()
