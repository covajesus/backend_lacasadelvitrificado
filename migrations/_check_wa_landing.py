import urllib.request

JS = "https://lacasadelvitrificado.com/assets/index-BRcywbc5.js"

req = urllib.request.Request(JS, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=60) as resp:
    js = resp.read().decode("utf-8", "replace")

print("bundle size:", len(js))
for needle in ("/wa/t/:code", "wa/t/", "WhatsAppCampaignLanding", "campaign_access"):
    print(f"{needle!r} present:", needle in js)
