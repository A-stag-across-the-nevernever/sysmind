import _bootstrap  # noqa: F401  (sys.path + isolated config)

from sysmind import check_ollama
from sysmind_common import contains_blocked

def test_ollama_check():
    result = check_ollama()
    print(f"Ollama found: {result}")

def test_blocked():
    assert contains_blocked("dd if=/dev/zero of=/dev/sda")
    assert not contains_blocked("systemctl status ssh")
    print("PASS: blocked detection")

if __name__ == "__main__":
    test_ollama_check()
    test_blocked()
