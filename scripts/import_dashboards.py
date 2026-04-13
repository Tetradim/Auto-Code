#!/usr/bin/env python3
"""
Grafana Dashboard Import Script

Usage:
    python scripts/import_dashboards.py --dry-run
    python scripts/import_dashboards.py --dashboard risk-ops
    python scripts/import_dashboards.py --all
"""
import argparse
import json
import os
import sys

DASHBOARD_DIR = os.path.join(os.path.dirname(__file__), "..", "grafana", "dashboards")
GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3000")
GRAFANA_API_KEY = os.getenv("GRAFANA_API_KEY", "")


def load_dashboard(name: str) -> dict:
    """Load dashboard JSON from file."""
    path = os.path.join(DASHBOARD_DIR, f"{name}.json")
    with open(path) as f:
        return json.load(f)


def import_dashboard(dashboard: dict, overwrite: bool = True) -> bool:
    """Import dashboard to Grafana via API."""
    import requests
    
    url = f"{GRAFANA_URL}/api/dashboards/db"
    headers = {
        "Authorization": f"Bearer {GRAFANA_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "dashboard": dashboard,
        "overwrite": overwrite,
        "message": f"Imported {dashboard.get('title', 'dashboard')}"
    }
    
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        if resp.status_code in (200, 204):
            print(f"✅ Imported: {dashboard.get('title')}")
            return True
        else:
            print(f"❌ Failed: {resp.status_code} - {resp.text}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Import Grafana dashboards")
    parser.add_argument("--all", action="store_true", help="Import all dashboards")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be imported")
    parser.add_argument("--dashboard", help="Import specific dashboard by name")
    args = parser.parse_args()
    
    dashboards = {
        "analyst-overview": "Sentinel Edge — Analyst Overview",
        "education-candles": "Sentinel Edge — Market Education (Beginner)", 
        "risk-ops": "Sentinel Edge — Risk & Operations"
    }
    
    if args.all:
        targets = list(dashboards.keys())
    elif args.dashboard:
        targets = [args.dashboard]
    else:
        parser.print_help()
        return
    
    for name in targets:
        if name not in dashboards:
            print(f"Unknown dashboard: {name}")
            continue
            
        try:
            dashboard = load_dashboard(name)
            if args.dry_run:
                print(f"[DRY RUN] Would import: {dashboards[name]}")
                print(f"  UID: {dashboard.get('uid')}")
                print(f"  Panels: {len(dashboard.get('panels', []))}")
            else:
                import_dashboard(dashboard)
        except FileNotFoundError:
            print(f"Dashboard file not found: {name}.json")
        except json.JSONDecodeError as e:
            print(f"Invalid JSON in {name}.json: {e}")


if __name__ == "__main__":
    main()