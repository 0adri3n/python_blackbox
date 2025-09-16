import python_blackbox, requests

python_blackbox.set_debug(True)  # enable debug loggings

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