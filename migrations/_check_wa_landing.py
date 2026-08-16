import urllib.request

URLS = [
    "https://lacasadelvitrificado.com/wa/t/E6WheD89DF",
    "https://api.lacasadelvitrificado.com/api/authentications/campaign_access/E6WheD89DF",
]

for url in URLS:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            print(url)
            print("  status:", resp.status)
            for key in ("cache-control", "etag", "content-type"):
                print(f"  {key}:", resp.headers.get(key))
            body = resp.read().decode("utf-8", "replace")
            print("  body head:", body[:180].replace("\n", " "))
    except Exception as exc:  # noqa: BLE001
        print(url, "ERROR", exc)
    print()
