import json
import urllib.request
from pathlib import Path

token = ""
for line in Path(__file__).resolve().parents[1].joinpath(".env").read_text(encoding="utf-8").splitlines():
    if line.startswith("META_TOKEN="):
        token = line.split("=", 1)[1].strip()
        break

url = (
    "https://graph.facebook.com/v22.0/790586727468909/message_templates"
    "?limit=200&fields=name,status,language,category,components"
)
req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
try:
    with urllib.request.urlopen(req, timeout=20) as response:
        data = json.load(response)
except urllib.error.HTTPError as exc:
    print(exc.read().decode())
    raise

keywords = ("custom", "campana", "publicidad", "advert", "product_discount")
for template in sorted(data.get("data", []), key=lambda item: item.get("name", "")):
    name = (template.get("name") or "").lower()
    if not any(keyword in name for keyword in keywords):
        continue
    components = [component.get("type") for component in template.get("components", [])]
    print(
        f"{template.get('name')} | language={template.get('language')} | "
        f"status={template.get('status')} | components={components}"
    )
