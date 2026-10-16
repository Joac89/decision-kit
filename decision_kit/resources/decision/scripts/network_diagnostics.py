"""Registra metadatos de red sin credenciales, cuerpos ni cabeceras HTTP."""
from datetime import datetime, timezone
import json
from http.client import HTTPException
import os
from pathlib import Path
import platform
import re
import socket
import ssl
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener, getproxies, proxy_bypass
import uuid


def proxy_address(value: str) -> dict:
    try:
        parsed = urlsplit(value if '://' in value else '//' + value)
        if not parsed.hostname or not re.fullmatch(r'[A-Za-z0-9._:\-]+', parsed.hostname):
            return {'invalid_proxy_configuration': True}
        return {'host': parsed.hostname, 'port': parsed.port or (443 if parsed.scheme == 'https' else 80),
                'scheme': parsed.scheme or 'http', 'authentication_present': bool(parsed.username or parsed.password)}
    except (ValueError, TypeError):
        return {'invalid_proxy_configuration': True}


def network_snapshot(endpoint: str) -> dict:
    parsed = urlsplit(endpoint)
    env = {name.lower(): value for name, value in os.environ.items()}
    try:
        proxies = getproxies()
        bypass = proxy_bypass(parsed.netloc)
        effective_proxy = proxies.get('https') if not bypass else None
        route = proxy_address(effective_proxy) if effective_proxy else {
            'host': parsed.hostname, 'port': parsed.port or 443, 'scheme': 'direct'}
        proxy_information = {'detected': {key: proxy_address(value) for key, value in proxies.items() if key in ('http', 'https', 'all')},
                             'source': 'environment' if env.get('https_proxy') else 'system_or_registry' if proxies.get('https') else 'none',
                             'bypass_for_endpoint': bypass, 'effective_route': route}
    except (OSError, ValueError):
        proxy_information = {'proxy_inspection_failed': True, 'effective_route': {}}
    return {'endpoint_host': parsed.hostname, 'endpoint_port': parsed.port or 443,
            'python_version': platform.python_version(), 'python_implementation': platform.python_implementation(),
            'openssl_version': ssl.OPENSSL_VERSION, 'process_id': os.getpid(),
            'proxy_environment_present': {name: bool(env.get(name)) for name in ('http_proxy', 'https_proxy', 'all_proxy', 'no_proxy')},
            'sandbox_network_disabled_marker_present': bool(os.environ.get('CODEX_SANDBOX_NETWORK_DISABLED')),
            'proxy': proxy_information}


class NetworkLog:
    def __init__(self, case: Path, endpoint: str, operation: str):
        self.started = time.monotonic()
        self.path = (case if case.name == '.artifacts' else case / '.artifacts') / 'logs' / f'network-{datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")}-{uuid.uuid4().hex[:8]}.jsonl'
        self.write_error = False
        self.snapshot = network_snapshot(endpoint)
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open('x', encoding='utf-8'):
                pass
        except OSError:
            self.write_error = True
        self.record('environment', {'operation': operation, **self.snapshot})

    def record(self, event: str, data: dict) -> None:
        if self.write_error:
            return
        item = {'timestamp_utc': datetime.now(timezone.utc).isoformat(),
                'elapsed_ms': round((time.monotonic() - self.started) * 1000, 2), 'event': event, **data}
        try:
            with self.path.open('a', encoding='utf-8') as stream:
                stream.write(json.dumps(item, ensure_ascii=False) + '\n')
        except OSError:
            self.write_error = True

    def reference(self) -> dict:
        return {'network_log': str(self.path)} if not self.write_error else {'network_log_error': 'LOG_WRITE_FAILED'}

    def dns(self) -> bool:
        route = self.snapshot['proxy'].get('effective_route', {})
        host, port = route.get('host'), route.get('port')
        if not host or not isinstance(port, int):
            self.record('dns_failed', {'code': 'INVALID_ROUTE'})
            return False
        try:
            addresses = sorted({entry[4][0] for entry in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)})
            self.record('dns_resolved', {'host': host, 'port': port, 'addresses': addresses})
            return True
        except OSError as error:
            self.record('dns_failed', {'host': host, 'exception_type': type(error).__name__, 'errno': error.errno,
                                       'winerror': getattr(error, 'winerror', None)})
            return False


class NoDiagnosticRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def diagnose_network(case: Path, config, classify_error) -> dict:
    log = NetworkLog(case, config.endpoint, 'connectivity_probe_no_credentials')
    route = log.snapshot['proxy'].get('effective_route', {})
    if not log.dns():
        return {'reachable': False, 'stage': 'dns', 'decision_sent': False, **log.reference()}
    try:
        with socket.create_connection((route['host'], route['port']), timeout=min(config.timeout_seconds, 10)):
            log.record('tcp_connected', {'host': route['host'], 'port': route['port']})
    except OSError as error:
        failure = classify_error(error, config.endpoint)
        log.record('tcp_failed', failure.diagnostic)
        return {'reachable': False, 'stage': 'tcp', 'diagnostic': failure.diagnostic, 'decision_sent': False, **log.reference()}
    context = ssl.create_default_context()
    if not config.verify_tls:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    request = Request(config.endpoint, method='GET', headers={'Accept': 'application/json'})
    try:
        with build_opener(NoDiagnosticRedirect(), HTTPSHandler(context=context)).open(request, timeout=min(config.timeout_seconds, 15)) as response:
            status = response.status
    except HTTPError as error:
        status = error.code
    except (URLError, OSError, HTTPException) as error:
        failure = classify_error(error, config.endpoint)
        log.record('https_failed', failure.diagnostic)
        return {'reachable': False, 'stage': 'https', 'diagnostic': failure.diagnostic, 'decision_sent': False, **log.reference()}
    log.record('https_response', {'http_status': status, 'credentials_sent': False, 'decision_sent': False})
    return {'reachable': True, 'stage': 'https', 'http_status': status, 'decision_sent': False, **log.reference()}
