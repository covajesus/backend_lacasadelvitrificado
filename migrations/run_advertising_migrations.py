"""Ejecuta todas las migraciones de publicidad (idempotente)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

MIGRATIONS = [
    'run_add_advertising_campaigns.py',
    'run_add_advertising_promotion_id.py',
    'run_add_advertising_campaign_deliveries.py',
]


def main() -> None:
    root = Path(__file__).resolve().parent
    for name in MIGRATIONS:
        script = root / name
        print(f'--- {name} ---')
        result = subprocess.run([sys.executable, str(script)], check=False)
        if result.returncode != 0:
            raise SystemExit(result.returncode)
    print('Migraciones de publicidad completadas.')


if __name__ == '__main__':
    main()
