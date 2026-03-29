"""
inject_files.py - Copy plugin files vào Docker container
Chạy sau khi 'docker-compose up -d' để inject code mới nhất.

Usage:
    python inject_files.py
"""
import subprocess
import pathlib
import sys

BASE = pathlib.Path(__file__).parent

FILES = [
    (BASE / 'plugins' / 'shop-demo' / 'shop-demo.php',
     '/var/www/html/wp-content/plugins/shop-demo/shop-demo.php'),
    (BASE.parent / 'uopz_hooks.php',
     '/var/www/uopz/uopz_hooks.php'),
]

CONTAINER = 'shop_demo_wp'


def inject(src: pathlib.Path, dst: str) -> bool:
    if not src.exists():
        print(f'  ✗ File không tồn tại: {src}')
        return False

    data = src.read_bytes()
    print(f'  → {src.name} ({len(data)} bytes) → {dst}')

    # Pipe file content via stdin into 'docker exec -i ... tee'
    r = subprocess.run(
        ['docker', 'exec', '-i', CONTAINER, 'tee', dst],
        input=data,
        capture_output=True
    )
    if r.returncode != 0:
        print(f'  ✗ Lỗi: {r.stderr.decode()[:200]}')
        return False

    # Verify size
    r2 = subprocess.run(
        ['docker', 'exec', CONTAINER, 'bash', '-c', f'wc -c < {dst}'],
        capture_output=True, text=True
    )
    written = r2.stdout.strip()
    print(f'  ✓ OK ({written} bytes ghi vào container)')
    return True


def main():
    print(f'\n🐳 Inject files vào container [{CONTAINER}]...\n')
    ok = all(inject(src, dst) for src, dst in FILES)
    if ok:
        print('\n✅ Xong! Plugin đã sẵn sàng.')
        print('   → Kích hoạt plugin: http://localhost:8088/wp-admin/plugins.php')
        print('   → Test UI:           http://localhost:8088/?test-shop=1')
    else:
        print('\n❌ Có lỗi. Đảm bảo container đang chạy: docker ps')
        sys.exit(1)


if __name__ == '__main__':
    main()
