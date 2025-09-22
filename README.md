# python_blackbox

<img width="682" height="214" alt="image" src="https://github.com/user-attachments/assets/650e7c85-36c8-429a-b232-4aab51a08015" />


`python_blackbox` is a lightweight Python module that helps prevent accidental or malicious network exfiltration by disabling common Python networking primitives at runtime. It is intended as a developer tool to reduce risk when running untrusted or sensitive code inside the Python interpreter.

> **Warning:** `python_blackbox` works at the Python level and is NOT a full substitute for OS-level network isolation. For robust guarantees use network namespaces, containers without a network, or firewall rules.

## Features

- Blocks common Python networking APIs: `socket`, `socket.create_connection`, `urllib.request.urlopen`, `http.client`, and `requests` (if installed).
- Blocks `ssl.SSLContext.wrap_socket` to prevent direct TLS sockets.
- Provides API to toggle blocking, add simple host/domain whitelist, and temporarily allow network access with a context manager.
- Works without root privileges.

## Quickstart

Install by copying `python_blackbox.py` into your project, or add it as a submodule to your repository.

You can install `python_blackbox` directly from this GitHub repository using `pip`:

```bash
pip install git+https://github.com/0adri3n/python_blackbox.git
```

Optionally, you can install a specific branch or tag:

```bash
pip install git+https://github.com/0adri3n/python_blackbox.git@test_branch
pip install git+https://github.com/0adri3n/python_blackbox.git@v0.1.0
```

### Default (auto-block on import)

```python
import python_blackbox
# Network access from most Python libs is now blocked
````

### Disable auto-block and control manually

Set the environment variable before importing:

```bash
export PYTHON_BLACKBOX_NOAUTO=1
python -c "import python_blackbox; python_blackbox.block_network()"
```

Or in code:

```python
import os
os.environ['PYTHON_BLACKBOX_NOAUTO'] = '1'
import python_blackbox
python_blackbox.block_network()
```

### Allow temporary network access

```python
import python_blackbox
with python_blackbox.allow_temporary():
    import requests
    r = requests.get('https://example.com')
```

### Whitelist a host or domain

```python
import python_blackbox
python_blackbox.add_whitelist('api.mycompany.internal')
```

### Debug Logging

You can enable verbose debug logging to see more informations.

**Enable via environment variable**

```bash
export PYTHON_BLACKBOX_DEBUG=1
python your_script.py
```

**Enable via code**

```python
import python_blackbox
python_blackbox.set_debug(True)

python_blackbox.allow_network()
python_blackbox.add_whitelist("httpbin.org")
python_blackbox.block_network()
```

Logs will look like this:

```
[python_blackbox DEBUG] Network access allowed.
[python_blackbox DEBUG] Host/domain added to whitelist: httpbin.org
[python_blackbox DEBUG] Network access blocked.
```


## API

* `block_network()` — apply Python-level network blocking.
* `allow_network()` — restore original behavior.
* `is_blocked()` — returns boolean.
* `allow_temporary()` — context manager to allow network inside a `with` block.
* `add_whitelist(host_or_domain)` — allow a specific host or domain.
* `remove_whitelist(host_or_domain)` — remove from whitelist.
* `set_debug(boolean)` — activate/deactivate debug

## Limitations & Security Notes

* **Does not block** subprocesses launching external binaries (e.g., `curl`), native extensions doing syscalls, or other processes on the machine.
* A privileged user or code running in the same interpreter could restore patched functions.
* For stronger isolation use OS-level mechanisms:

  * Linux: `ip netns`, `iptables`/`nftables`, containers (`docker run --network none`), or run inside a VM.
  * macOS: use `pfctl` or run in a VM/container without network.
  * Windows: use Windows Firewall or run in a VM/container.

## Recommended usage patterns

* Use `python_blackbox` during tests or when executing third-party plugins.
* Combine with process-level restrictions (no subprocess calls) or run inside a container with no network.
* Keep a careful audit of any C extensions and subprocess usage in the codebase.

## Development & Tests

Add a small test file to validate blocking behavior. Example:

```python
# tests/test.py
import python_blackbox, requests

python_blackbox.add_whitelist("httpbin.org")

try:
    r = requests.get("https://httpbin.org/get")  # should succeed
    print("OK with whitelist:", r.status_code)
except python_blackbox.NetworkBlockedError as e:
    print("Blocked:", e)

python_blackbox.remove_whitelist("httpbin.org")

try:
    r = requests.get("https://httpbin.org/get")  # should fail
    print("OK:", r.status_code)
except python_blackbox.NetworkBlockedError as e:
    print("Blocked after whitelist removal:", e)

with python_blackbox.allow_temporary():
    try:
        r = requests.get("https://httpbin.org/get")  # should succeed
        print("OK in context with:", r.status_code)
    except python_blackbox.NetworkBlockedError as e:
        print("Blocked in context with:", e)

python_blackbox.allow_network()

try:
    r = requests.get("https://httpbin.org/get")  # should succeed
    print("OK after network allowed:", r.status_code)
except python_blackbox.NetworkBlockedError as e:
    print("Blocked:", e)
```

## Contributing

Feel free to add more primitives to patch (e.g., `asyncio` transports) or improve domain/IP parsing for the whitelist. Pull requests welcome.
