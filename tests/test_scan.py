import _bootstrap  # noqa: F401  (sys.path + isolated config)

from sysmind_scan import scan, compute_alerts

def test_scan_structure():
    data = scan("low")
    assert "generated_at" in data
    assert "system" in data
    assert "packages" in data
    assert "services" in data
    assert "resources" in data
    assert "alerts" in data
    print("PASS: scan_structure")

def test_alerts():
    data = {
        "resources": {"disk_root_percent": 85, "memory_percent": 90},
        "packages": {"upgradable": 5},
        "services": {"failed": 1, "failed_services": ["bluetooth.service"]},
        "security": {"open_ports": [22, 80]},
    }
    alerts = compute_alerts(data)
    categories = {a["category"] for a in alerts}
    assert "disk" in categories
    assert "memory" in categories
    assert "packages" in categories
    print("PASS: alerts")

if __name__ == "__main__":
    test_scan_structure()
    test_alerts()
