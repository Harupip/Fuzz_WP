import sys
import time
from pathlib import Path
import json

# Thêm đường dẫn để Python có thể import được energy.py
sys.path.insert(0, str(Path(__file__).parent))
from energy import EnergyScheduler

def main():
    base_dir = Path(__file__).parent.parent.parent / "output"
    requests_dir = base_dir / "requests"
    snapshot_path = base_dir / "total_coverage.json"

    print("=== BẮT ĐẦU THEO DÕI NĂNG LƯỢNG (ENERGY SCHEDULER) ===")
    print(f"Thư mục theo dõi : {requests_dir}")
    print(f"File tổng hợp    : {snapshot_path}")
    print("-" * 50)

    scheduler = EnergyScheduler(
        requests_dir=str(requests_dir),
        snapshot_path=str(snapshot_path),
        snapshot_interval=5  # Cập nhật snapshot thường xuyên hơn để demo
    )

    # Load state cũ nếu có
    if scheduler.load_previous_state():
        stats = scheduler.calculator.get_stats()
        print(f"➜ Đã load state cũ: {stats['total_registered']} đăng ký, {stats['total_executed']} thực thi.")

    print("\n[Đang chờ requests...] Hãy mở trình duyệt và tương tác với trang web!")
    
    try:
        while True:
            new_results = scheduler.process_new_requests()
            for req_id, result in new_results:
                print(f"\n🚀 [New Request] ID: {req_id}")
                print(f"   => Energy Score : {result.score} (Tier: {result.dominant_tier})")
                print(f"   => Hooks First Seen: {result.first_seen_count} | Rare: {result.rare_count} | Frequent: {result.frequent_count}")
                
                if result.blindspot_hits > 0:
                    print(f"   🔥 BONUS: {result.blindspot_hits} blindspot(s) được trigger!")
                if result.new_hooks_discovered > 0:
                    print(f"   💎 BONUS: Khám phá {result.new_hooks_discovered} hook(s) hoàn toàn mới!")
                    
            time.sleep(1) # Chờ 1 giây rồi quét tiếp
    except KeyboardInterrupt:
        print("\n\nĐang lưu state và thoát...")
        scheduler.save_state()
        print("Tạm biệt!")

if __name__ == "__main__":
    main()
