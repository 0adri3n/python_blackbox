import python_blackbox, requests

python_blackbox.add_whitelist("httpbin.org")

try:
    r = requests.get("https://httpbin.org/get")  # should succeed
    print("OK:", r.status_code)
except python_blackbox.NetworkBlockedError as e:
    print("Blocked:", e)

try:
    r = requests.get("https://httpbin.org/get")  # should raise
except python_blackbox.NetworkBlockedError as e:
    print("Blocked as expected:", e)

with python_blackbox.allow_temporary():
    python_blackbox.add_whitelist("httpbin.org")
    try:
        r = requests.get("https://httpbin.org/get")  # should succeed
        print("OK in context:", r.status_code)
    except python_blackbox.NetworkBlockedError as e:
        print("Blocked in context:", e)