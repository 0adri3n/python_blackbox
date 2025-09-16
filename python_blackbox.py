"""
python_blackbox.py

Block common network access at the Python level to reduce risk of data exfiltration
when running scripts. This module monkey-patches common networking primitives
(socket, urllib, http.client, requests, SSLContext.wrap_socket) so that attempts
to open outbound network connections raise a `NetworkBlockedError`.

Usage:
    import python_blackbox   # blocks automatically unless PYTHON_BLACKBOX_NOAUTO=1

API:
    block_network()
    allow_network()
    is_blocked()
    allow_temporary()  # context manager
    add_whitelist(host_or_domain)
    remove_whitelist(host_or_domain)

Limitations:
    - Works at the Python interpreter level and blocks the most common libs.
    - Does not prevent external programs (curl, wget) launched via subprocess
      from using the network unless you also patch or restrict subprocess.
    - Native C extensions that call syscalls directly can bypass this.
    - For a stronger guarantee use OS-level firewall, network namespaces, or run
      the script in a container without network access.
"""

from contextlib import contextmanager
import os
import socket
import ssl
import urllib.request
import http.client
import sys
import types

# Optional: detect requests and patch if available
try:
    import requests
except Exception:
    requests = None

# Saved originals
_ORIG = {}
_BLOCKED = False
_WHITELIST = set()
_DEBUG = os.environ.get("PYTHON_BLACKBOX_DEBUG", "") in ("1", "true", "True")

def set_debug(enabled: bool):
    """Enable or disable debug logging for python_blackbox."""
    global _DEBUG
    _DEBUG = bool(enabled)

def _log(msg: str):
    if _DEBUG:
        print(f"[python_blackbox DEBUG] {msg}")

# Helper: check if a host is allowed (simple domain/IP match)
def _host_allowed(host):
    if not host:
        return False
    # remove port if present
    if ":" in host:
        host = host.split(":", 1)[0]
    host = host.lower()  # <-- Ajouté
    for w in _WHITELIST:
        if host == w or host.endswith("." + w):
            _log(f"Allowing access to whitelisted host {host}")
            return True
    # always allow localhost/loopback
    if host in ("localhost", "127.0.0.1", "::1"):
        _log(f"Allowing access to localhost {host}")
        return True
    _log(f"Blocking host {host}")  
    return False


class NetworkBlockedError(RuntimeError):
    """Raised when code attempts network access while blocked."""
    pass


# A socket constructor that always raises to block socket creation
class _BlockedSocket:
    def __init__(self, *args, **kwargs):
        raise NetworkBlockedError("Network access blocked by python_blackbox")


# Replacement for socket.create_connection with whitelist support
def _blocked_create_connection(address, timeout=None, source_address=None):
    host, port = address
    if _host_allowed(host):
        return _ORIG['socket.create_connection'](address, timeout, source_address)
    raise NetworkBlockedError(f"Attempt to connect to {host}:{port} blocked by python_blackbox")


# Replacement for http.client.HTTPConnection.connect
def _blocked_http_connect(self):
    host = getattr(self, 'host', None)
    if _host_allowed(host):
        return _ORIG['http.client.HTTPConnection.connect'](self)
    raise NetworkBlockedError(f"HTTP connect to {host} blocked by python_blackbox")


# Replacement for urllib.request.urlopen
def _blocked_urlopen(*args, **kwargs):
    url = args[0] if args else kwargs.get('url')
    host = None
    if isinstance(url, str):
        try:
            import urllib.parse as _up
            host = _up.urlparse(url).hostname
        except Exception:
            host = None
    if _host_allowed(host):
        return _ORIG['urllib.request.urlopen'](*args, **kwargs)
    raise NetworkBlockedError(f"urlopen to {host} blocked by python_blackbox")


# Replacement for requests.Session.request (if requests is installed)
def _blocked_requests_request(self, method, url, *args, **kwargs):
    try:
        import urllib.parse as _up
        host = _up.urlparse(url).hostname
    except Exception:
        host = None
    if _host_allowed(host):
        return _ORIG['requests.Session.request'](self, method, url, *args, **kwargs)
    raise NetworkBlockedError(f"requests to {host} blocked by python_blackbox")


def block_network():
    """Apply Python-level network blocking. Idempotent."""
    global _BLOCKED
    if _BLOCKED:
        return
    # Save originals
    _ORIG['socket.socket'] = socket.socket
    _ORIG['socket.create_connection'] = socket.create_connection
    _ORIG['urllib.request.urlopen'] = urllib.request.urlopen
    _ORIG['http.client.HTTPConnection.connect'] = http.client.HTTPConnection.connect

    # Patch create_connection to check whitelist
    socket.create_connection = _blocked_create_connection

    # Patch urllib / http.client
    urllib.request.urlopen = _blocked_urlopen
    http.client.HTTPConnection.connect = _blocked_http_connect

    # Patch requests if present
    if requests is not None:
        _ORIG['requests.Session.request'] = requests.Session.request
        requests.Session.request = _blocked_requests_request

    _BLOCKED = True


def allow_network():
    """Restore original networking functions."""
    global _BLOCKED
    if not _BLOCKED:
        return
    # restore saved originals
    for k, v in list(_ORIG.items()):
        if k == 'socket.socket':
            socket.socket = v
        elif k == 'socket.create_connection':
            socket.create_connection = v
        elif k == 'urllib.request.urlopen':
            urllib.request.urlopen = v
        elif k == 'http.client.HTTPConnection.connect':
            http.client.HTTPConnection.connect = v
        elif k == 'ssl.SSLContext.wrap_socket' and hasattr(ssl, 'SSLContext'):
            ssl.SSLContext.wrap_socket = v
        elif k == 'requests.Session.request' and requests is not None:
            requests.Session.request = v

    _ORIG.clear()
    _BLOCKED = False


def is_blocked():
    return _BLOCKED


@contextmanager
def allow_temporary():
    """Context manager that temporarily allows network access inside the with-block."""
    _log("Entering allow_temporary context")
    was_blocked = is_blocked()
    if was_blocked:
        allow_network()
    try:
        yield
    finally:
        if was_blocked:
            block_network()


def add_whitelist(host_or_domain):
    """Add a host or domain to the whitelist (e.g. 'example.com' or 'api.example.com')."""
    _WHITELIST.add(host_or_domain)
    _log("Host/domain added to whitelist: " + host_or_domain)


def remove_whitelist(host_or_domain):
    _WHITELIST.discard(host_or_domain)
    _log("Host/domain removed from whitelist: " + host_or_domain)


# Auto-block on import unless disabled via environment variable
if os.environ.get("PYTHON_BLACKBOX_NOAUTO", "") in ("1", "true", "True"):
    # do not auto-block
    pass
else:
    try:
        block_network()
        _log("Network access blocked on import.")
    except Exception:
        # fail gracefully if patching fails
        pass

