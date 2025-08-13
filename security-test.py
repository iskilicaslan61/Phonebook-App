#!/usr/bin/env python3
"""
Security Testing Script for Phonebook App
This script tests for common security vulnerabilities
"""

import requests
import json
import sys
from urllib.parse import urljoin

class SecurityTester:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.vulnerabilities_found = []
        
    def test_sql_injection(self):
        """Test for SQL injection vulnerabilities"""
        print("🔍 Testing for SQL injection vulnerabilities...")
        
        # Test payloads that could cause SQL injection
        sql_payloads = [
            "' OR '1'='1",
            "'; DROP TABLE phonebook; --",
            "' UNION SELECT * FROM users --",
            "' OR 1=1 --",
            "admin'--",
            "'; SELECT SLEEP(5); --"
        ]
        
        for payload in sql_payloads:
            try:
                # Test search functionality
                response = self.session.post(
                    urljoin(self.base_url, '/'),
                    data={'username': payload},
                    timeout=10
                )
                
                # Check if the response indicates SQL injection
                if response.status_code == 500:
                    self.vulnerabilities_found.append(f"SQL Injection: Server error with payload '{payload}'")
                elif "mysql" in response.text.lower() or "sql" in response.text.lower():
                    self.vulnerabilities_found.append(f"SQL Injection: SQL error message found with payload '{payload}'")
                elif response.elapsed.total_seconds() > 4:  # Time-based injection
                    self.vulnerabilities_found.append(f"SQL Injection: Time-based injection possible with payload '{payload}'")
                    
            except requests.exceptions.Timeout:
                self.vulnerabilities_found.append(f"SQL Injection: Timeout with payload '{payload}' (possible time-based injection)")
            except Exception as e:
                print(f"Error testing payload '{payload}': {e}")
        
        # Test add functionality
        try:
            response = self.session.post(
                urljoin(self.base_url, '/add'),
                data={'username': "'; DROP TABLE phonebook; --", 'phonenumber': '1234567890'},
                timeout=10
            )
            
            if response.status_code == 500:
                self.vulnerabilities_found.append("SQL Injection: Add functionality vulnerable")
                
        except Exception as e:
            print(f"Error testing add functionality: {e}")
    
    def test_xss(self):
        """Test for XSS vulnerabilities"""
        print("🔍 Testing for XSS vulnerabilities...")
        
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<svg onload=alert('XSS')>",
            "'\"><script>alert('XSS')</script>"
        ]
        
        for payload in xss_payloads:
            try:
                response = self.session.post(
                    urljoin(self.base_url, '/'),
                    data={'username': payload},
                    timeout=10
                )
                
                if payload in response.text:
                    self.vulnerabilities_found.append(f"XSS: Payload '{payload}' reflected in response")
                    
            except Exception as e:
                print(f"Error testing XSS payload '{payload}': {e}")
    
    def test_input_validation(self):
        """Test input validation"""
        print("🔍 Testing input validation...")
        
        # Test empty inputs
        try:
            response = self.session.post(
                urljoin(self.base_url, '/'),
                data={'username': ''},
                timeout=10
            )
            
            if response.status_code == 200 and "error" not in response.text.lower():
                self.vulnerabilities_found.append("Input Validation: Empty username accepted without validation")
                
        except Exception as e:
            print(f"Error testing empty input: {e}")
        
        # Test very long inputs
        long_input = "A" * 1000
        try:
            response = self.session.post(
                urljoin(self.base_url, '/'),
                data={'username': long_input},
                timeout=10
            )
            
            if response.status_code == 200:
                self.vulnerabilities_found.append("Input Validation: Very long input accepted (potential DoS)")
                
        except Exception as e:
            print(f"Error testing long input: {e}")
    
    def test_authentication_bypass(self):
        """Test for authentication bypass vulnerabilities"""
        print("🔍 Testing for authentication bypass...")
        
        # Test if we can access admin-like endpoints
        admin_endpoints = ['/admin', '/config', '/debug', '/internal', '/api/users']
        
        for endpoint in admin_endpoints:
            try:
                response = self.session.get(
                    urljoin(self.base_url, endpoint),
                    timeout=10
                )
                
                if response.status_code == 200:
                    self.vulnerabilities_found.append(f"Authentication Bypass: Endpoint {endpoint} accessible without authentication")
                    
            except Exception as e:
                print(f"Error testing endpoint {endpoint}: {e}")
    
    def test_error_handling(self):
        """Test error handling and information disclosure"""
        print("🔍 Testing error handling...")
        
        # Test for information disclosure in errors
        try:
            response = self.session.get(
                urljoin(self.base_url, '/nonexistent'),
                timeout=10
            )
            
            if response.status_code == 500:
                self.vulnerabilities_found.append("Error Handling: Internal server error exposed")
            elif "stack trace" in response.text.lower() or "exception" in response.text.lower():
                self.vulnerabilities_found.append("Error Handling: Stack trace or exception details exposed")
                
        except Exception as e:
            print(f"Error testing error handling: {e}")
    
    def run_all_tests(self):
        """Run all security tests"""
        print("🚀 Starting security testing...")
        print(f"Target URL: {self.base_url}")
        print("-" * 50)
        
        self.test_sql_injection()
        self.test_xss()
        self.test_input_validation()
        self.test_authentication_bypass()
        self.test_error_handling()
        
        print("-" * 50)
        self.print_results()
    
    def print_results(self):
        """Print test results"""
        if not self.vulnerabilities_found:
            print("✅ No security vulnerabilities detected!")
            print("🎉 Your application appears to be secure against common attacks.")
        else:
            print(f"❌ {len(self.vulnerabilities_found)} security vulnerabilities found:")
            for i, vuln in enumerate(self.vulnerabilities_found, 1):
                print(f"  {i}. {vuln}")
            print("\n🚨 Immediate action required to fix these vulnerabilities!")
        
        return len(self.vulnerabilities_found) == 0

def main():
    if len(sys.argv) != 2:
        print("Usage: python security-test.py <base_url>")
        print("Example: python security-test.py http://localhost:5000")
        sys.exit(1)
    
    base_url = sys.argv[1]
    
    try:
        tester = SecurityTester(base_url)
        is_secure = tester.run_all_tests()
        
        if is_secure:
            sys.exit(0)
        else:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️ Testing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 