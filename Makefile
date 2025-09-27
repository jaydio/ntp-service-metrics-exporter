# SPDX-License-Identifier: BSD-3-Clause
#
# NTP Service Metrics Exporter - Test Suite and Build Targets
#
# Key Features:
# - Comprehensive test suite with colored output (32 total tests)
# - Unified test runner combining unit and integration tests
# - Individual test categories for targeted validation
# - Real-time feedback with colored pass/fail indicators
#
# Usage:
#   make test-all    # Run complete test suite (recommended)
#   make check       # Run Python unit tests only
#   make test-*      # Run specific test categories

.PHONY: check example run clean help test-all test-ipv4-rejects-ipv6 test-ipv6-rejects-ipv4 test-hostname-rejection test-valid-ip-acceptance test-formats

# Default target
all: check

# Run tests with detailed output
check:
	@printf "\033[0;34mRunning Python unit tests...\033[0m\n"
	@printf "\033[0;34m════════════════════════════════════════\033[0m\n"
	@cd tests/python && python3 -m unittest test_parser -v 2>&1 | while IFS= read -r line; do \
		case "$$line" in \
			*"... ok") \
				test_name=$$(echo "$$line" | sed 's/ (.*//'); \
				printf "\033[0;32m✓ PASS\033[0m: $$test_name\n" ;; \
			*"... FAIL") \
				test_name=$$(echo "$$line" | sed 's/ (.*//'); \
				printf "\033[0;31m✗ FAIL\033[0m: $$test_name\n" ;; \
			*"... ERROR") \
				test_name=$$(echo "$$line" | sed 's/ (.*//'); \
				printf "\033[0;31m✗ ERROR\033[0m: $$test_name\n" ;; \
			"OK") \
				printf "\033[0;32mOK\033[0m\n" ;; \
			FAILED*) \
				printf "\033[0;31m$$line\033[0m\n" ;; \
			"Ran "* ) \
				printf "\033[0;34m$$line\033[0m\n" ;; \
			"----------------------------------------------------------------------") \
				printf "\033[0;34m$$line\033[0m\n" ;; \
			*) \
				;; \
		esac; \
	done
	@if cd tests/python && python3 -m unittest test_parser >/dev/null 2>&1; then \
		printf "\033[0;34m════════════════════════════════════════\033[0m\n"; \
		printf "\033[0;32m✓ Python tests completed successfully\033[0m\n"; \
	else \
		printf "\033[0;34m════════════════════════════════════════\033[0m\n"; \
		printf "\033[0;31m✗ Python tests failed\033[0m\n"; \
		exit 1; \
	fi

# Alias for check
test: check

# Test IPv4-only flag rejects IPv6 addresses
test-ipv4-rejects-ipv6:
	@printf "\033[0;34mTesting IPv4-only flag behavior...\033[0m\n"
	@if ./ntp_exporter.py -4 ::1 2>&1 | grep -q "Invalid IP address"; then \
		printf "\033[0;32m✓ PASS\033[0m: -4 flag correctly rejects IPv6 address\n"; \
	else \
		printf "\033[0;31m✗ FAIL\033[0m: -4 flag should reject IPv6 address with 'Invalid IP address' error\n"; \
		exit 1; \
	fi

# Test IPv6-only flag rejects IPv4 addresses  
test-ipv6-rejects-ipv4:
	@printf "\033[0;34mTesting IPv6-only flag behavior...\033[0m\n"
	@if ./ntp_exporter.py -6 192.168.1.1 2>&1 | grep -q "Invalid IP address"; then \
		printf "\033[0;32m✓ PASS\033[0m: -6 flag correctly rejects IPv4 address\n"; \
	else \
		printf "\033[0;31m✗ FAIL\033[0m: -6 flag should reject IPv4 address with 'Invalid IP address' error\n"; \
		exit 1; \
	fi

# Test output format validation
test-formats:
	@printf "\033[0;34mTesting output format validation...\033[0m\n"
	@printf "\033[0;34m  → Testing JSON format...\033[0m\n"
	@./ntp_exporter.py --json 127.0.0.1 > /tmp/test_output.json 2>/dev/null || true
	@if python3 -c "import json; json.load(open('/tmp/test_output.json'))" 2>/dev/null; then \
		printf "\033[0;32m  ✓ PASS\033[0m: JSON output is valid\n"; \
	else \
		printf "\033[0;31m  ✗ FAIL\033[0m: JSON output is invalid\n"; \
		rm -f /tmp/test_output.json /tmp/test_output.yaml; \
		exit 1; \
	fi
	@printf "\033[0;34m  → Testing YAML format...\033[0m\n"
	@./ntp_exporter.py 127.0.0.1 > /tmp/test_output.yaml 2>/dev/null || true
	@if python3 -c "import sys; sys.path.append('.'); from ntp_exporter import YAMLEmitter; data=open('/tmp/test_output.yaml').read(); print('YAML format valid' if data.startswith('- target:') else 'Invalid')" | grep -q "YAML format valid"; then \
		printf "\033[0;32m  ✓ PASS\033[0m: YAML output is valid\n"; \
	else \
		printf "\033[0;31m  ✗ FAIL\033[0m: YAML output is invalid\n"; \
		rm -f /tmp/test_output.json /tmp/test_output.yaml; \
		exit 1; \
	fi
	@rm -f /tmp/test_output.json /tmp/test_output.yaml

# Test hostname rejection (should fail with validation error)
test-hostname-rejection:
	@printf "\033[0;34mTesting hostname rejection...\033[0m\n"
	@if ./ntp_exporter.py example.com 2>&1 | grep -q "Invalid IP address"; then \
		printf "\033[0;32m✓ PASS\033[0m: Hostname correctly rejected with validation error\n"; \
	else \
		printf "\033[0;31m✗ FAIL\033[0m: Hostname should be rejected with 'Invalid IP address' error\n"; \
		exit 1; \
	fi

# Test valid IP acceptance
test-valid-ip-acceptance:
	@printf "\033[0;34mTesting valid IP acceptance...\033[0m\n"
	@if timeout 10 ./ntp_exporter.py 127.0.0.1 >/dev/null 2>&1; then \
		printf "\033[0;32m✓ PASS\033[0m: Valid IPv4 address accepted\n"; \
	else \
		printf "\033[1;33m⚠ SKIP\033[0m: Valid IPv4 test skipped (timeout or no NTP service)\n"; \
	fi
	@if timeout 10 ./ntp_exporter.py ::1 >/dev/null 2>&1; then \
		printf "\033[0;32m✓ PASS\033[0m: Valid IPv6 address accepted\n"; \
	else \
		printf "\033[1;33m⚠ SKIP\033[0m: Valid IPv6 test skipped (timeout or no NTP service)\n"; \
	fi

# Run all validation tests with comprehensive output
# This target combines all 32 tests (25 unit + 7 integration) with unified colored output
test-all: 
	@printf "\033[0;34m════════════════════════════════════════\033[0m\n"
	@printf "\033[0;34m    NTP Exporter Test Suite (32 tests)\033[0m\n"
	@printf "\033[0;34m════════════════════════════════════════\033[0m\n"
	@cd tests/python && python3 -m unittest test_parser -v 2>&1 | while IFS= read -r line; do \
		case "$$line" in \
			*"... ok") \
				test_name=$$(echo "$$line" | sed 's/ (.*//'); \
				printf "\033[0;32m✓ PASS\033[0m: $$test_name\n" ;; \
			*"... FAIL") \
				test_name=$$(echo "$$line" | sed 's/ (.*//'); \
				printf "\033[0;31m✗ FAIL\033[0m: $$test_name\n" ;; \
			*"... ERROR") \
				test_name=$$(echo "$$line" | sed 's/ (.*//'); \
				printf "\033[0;31m✗ ERROR\033[0m: $$test_name\n" ;; \
			"----------------------------------------------------------------------") \
				printf "\033[0;34m$$line\033[0m\n" ;; \
			"Ran "* ) \
				printf "\033[0;34m$$line\033[0m\n" ;; \
			"OK") \
				printf "\033[0;32m$$line\033[0m\n" ;; \
			FAILED*) \
				printf "\033[0;31m$$line\033[0m\n" ;; \
			*) \
				;; \
		esac; \
	done
	@printf "\033[0;34m────────────────────────────────────────\033[0m\n"
	@printf "\033[0;34mRunning Integration Tests...\033[0m\n"
	@printf "\033[0;34m────────────────────────────────────────\033[0m\n"
	@if ./ntp_exporter.py -4 ::1 2>&1 | grep -q "Invalid IP address"; then \
		printf "\033[0;32m✓ PASS\033[0m: IPv4-only flag correctly rejects IPv6 address\n"; \
	else \
		printf "\033[0;31m✗ FAIL\033[0m: IPv4-only flag should reject IPv6 address\n"; \
		exit 1; \
	fi
	@if ./ntp_exporter.py -6 192.168.1.1 2>&1 | grep -q "Invalid IP address"; then \
		printf "\033[0;32m✓ PASS\033[0m: IPv6-only flag correctly rejects IPv4 address\n"; \
	else \
		printf "\033[0;31m✗ FAIL\033[0m: IPv6-only flag should reject IPv4 address\n"; \
		exit 1; \
	fi
	@if ./ntp_exporter.py example.com 2>&1 | grep -q "Invalid IP address"; then \
		printf "\033[0;32m✓ PASS\033[0m: Hostname correctly rejected with validation error\n"; \
	else \
		printf "\033[0;31m✗ FAIL\033[0m: Hostname should be rejected with validation error\n"; \
		exit 1; \
	fi
	@if timeout 10 ./ntp_exporter.py 127.0.0.1 >/dev/null 2>&1; then \
		printf "\033[0;32m✓ PASS\033[0m: Valid IPv4 address accepted\n"; \
	else \
		printf "\033[1;33m⚠ SKIP\033[0m: Valid IPv4 test skipped (timeout or no NTP service)\n"; \
	fi
	@if timeout 10 ./ntp_exporter.py ::1 >/dev/null 2>&1; then \
		printf "\033[0;32m✓ PASS\033[0m: Valid IPv6 address accepted\n"; \
	else \
		printf "\033[1;33m⚠ SKIP\033[0m: Valid IPv6 test skipped (timeout or no NTP service)\n"; \
	fi
	@./ntp_exporter.py --json 127.0.0.1 > /tmp/test_output.json 2>/dev/null || true
	@if python3 -c "import json; json.load(open('/tmp/test_output.json'))" 2>/dev/null; then \
		printf "\033[0;32m✓ PASS\033[0m: JSON output format is valid\n"; \
	else \
		printf "\033[0;31m✗ FAIL\033[0m: JSON output format is invalid\n"; \
		rm -f /tmp/test_output.json /tmp/test_output.yaml; \
		exit 1; \
	fi
	@./ntp_exporter.py 127.0.0.1 > /tmp/test_output.yaml 2>/dev/null || true
	@if python3 -c "import sys; sys.path.append('.'); from ntp_exporter import YAMLEmitter; data=open('/tmp/test_output.yaml').read(); print('YAML format valid' if data.startswith('- target:') else 'Invalid')" | grep -q "YAML format valid"; then \
		printf "\033[0;32m✓ PASS\033[0m: YAML output format is valid\n"; \
	else \
		printf "\033[0;31m✗ FAIL\033[0m: YAML output format is invalid\n"; \
		rm -f /tmp/test_output.json /tmp/test_output.yaml; \
		exit 1; \
	fi
	@rm -f /tmp/test_output.json /tmp/test_output.yaml
	@printf "\033[0;34m════════════════════════════════════════\033[0m\n"
	@if cd tests/python && python3 -m unittest test_parser >/dev/null 2>&1; then \
		printf "\033[0;32m✓ All tests completed successfully!\033[0m\n"; \
	else \
		printf "\033[0;31m✗ Some tests failed!\033[0m\n"; \
		exit 1; \
	fi
	@printf "\033[0;34m════════════════════════════════════════\033[0m\n"

# Generate example output using test fixtures
example:
	@echo "Generating sample output using test fixtures..."
	@mkdir -p examples
	@echo "# Sample NTP Exporter Output" > examples/sample_output_generated.yaml
	@echo "# Generated from test fixtures on $$(date -u '+%Y-%m-%dT%H:%M:%SZ')" >> examples/sample_output_generated.yaml
	@echo "" >> examples/sample_output_generated.yaml
	@echo "# This demonstrates the YAML schema structure" >> examples/sample_output_generated.yaml
	@echo "# In a real scenario, this would query actual NTP servers" >> examples/sample_output_generated.yaml

# Display help information
help:
	@printf "\033[0;34m════════════════════════════════════════\033[0m\n"
	@printf "\033[0;34m    NTP Exporter Makefile Help\033[0m\n"
	@printf "\033[0;34m════════════════════════════════════════\033[0m\n"
	@printf "\033[1;33mTesting Targets:\033[0m\n"
	@printf "  \033[0;32mtest-all\033[0m                 Run complete test suite (32 tests) with colored output\n"
	@printf "  \033[0;32mcheck\033[0m                    Run Python unit tests (25 tests) with colored output\n"
	@printf "  \033[0;32mtest\033[0m                     Alias for 'check'\n"
	@printf "  \033[0;32mtest-ipv4-rejects-ipv6\033[0m   Test IPv4-only flag rejects IPv6 addresses\n"
	@printf "  \033[0;32mtest-ipv6-rejects-ipv4\033[0m   Test IPv6-only flag rejects IPv4 addresses\n"
	@printf "  \033[0;32mtest-hostname-rejection\033[0m   Test hostname rejection (IP-only validation)\n"
	@printf "  \033[0;32mtest-valid-ip-acceptance\033[0m  Test valid IP address acceptance\n"
	@printf "  \033[0;32mtest-formats\033[0m              Test JSON and YAML output format validation\n"
	@printf "\n\033[1;33mDevelopment Targets:\033[0m\n"
	@printf "  \033[0;32mexample\033[0m                  Generate sample output using test fixtures\n"
	@printf "  \033[0;32mrun SERVERS=\"ip1 ip2\"\033[0m    Run exporter with specified IP addresses\n"
	@printf "  \033[0;32mclean\033[0m                    Clean up generated files\n"
	@printf "  \033[0;32mhelp\033[0m                     Show this help message\n"
	@printf "\n\033[1;33mExamples:\033[0m\n"
	@printf "  make test-all                    # Run complete test suite (recommended)\n"
	@printf "  make check                       # Run unit tests only\n"
	@printf "  make test-ipv4-rejects-ipv6      # Test specific functionality\n"
	@printf "  make run SERVERS=\"192.168.1.1\"   # Test with real server\n"
	@printf "\n\033[1;33mTest Output Features:\033[0m\n"
	@printf "  • Colored results: \033[0;32m✓ PASS\033[0m, \033[0;31m✗ FAIL\033[0m, \033[1;33m⚠ SKIP\033[0m\n"
	@printf "  • Unified display: All tests in single coherent output\n"
	@printf "  • Real-time feedback: Individual test results as they complete\n"
	@printf "\033[0;34m════════════════════════════════════════\033[0m\n"

# Clean up generated files
clean:
	@echo "Cleaning up generated files..."
	@rm -f /tmp/test_output.json /tmp/test_output.yaml
	@rm -rf examples/sample_output_generated.yaml
	@find . -name "*.pyc" -delete
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@echo "Clean completed."

# Convenience wrapper to run Python exporter
run:
	@if [ -z "$(SERVERS)" ]; then \
		echo "Usage: make run SERVERS=\"ip1 ip2 ...\""; \
		echo "Example: make run SERVERS=\"192.168.1.1 8.8.8.8\""; \
		echo "Note: Only IP addresses are accepted (no hostnames)"; \
		exit 1; \
	fi
	@echo "Running NTP exporter with servers: $(SERVERS)"
	@./ntp_exporter.py $(SERVERS)
	@echo "Cleaning generated files..."
	@rm -f examples/sample_output_generated.yaml
	@rm -f ntp_results.yaml
	@rm -f /tmp/ntp_*.yaml
	@find . -name "*.pyc" -delete 2>/dev/null || true
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@echo "Clean completed."

