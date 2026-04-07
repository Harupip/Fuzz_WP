import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from energy import EnergyScheduler


def main():
    base_dir = Path(__file__).parent.parent.parent / "output"
    requests_dir = base_dir / "requests"
    snapshot_path = base_dir / "total_coverage.json"

    print("=== BAT DAU THEO DOI NANG LUONG (ENERGY SCHEDULER) ===")
    print(f"Thu muc theo doi : {requests_dir}")
    print(f"File tong hop    : {snapshot_path}")
    print("-" * 50)

    scheduler = EnergyScheduler(
        requests_dir=str(requests_dir),
        snapshot_path=str(snapshot_path),
        snapshot_interval=5,
    )

    if scheduler.load_previous_state():
        stats = scheduler.calculator.get_stats()
        print(
            f"Da load state cu: {stats['total_registered']} dang ky, "
            f"{stats['total_executed']} thuc thi."
        )

    print("\n[DANG CHO REQUESTS...] Hay mo trinh duyet va tuong tac voi trang web!")

    try:
        while True:
            new_results = scheduler.process_new_requests()
            for req_id, result in new_results:
                print(f"\n[New Request] ID: {req_id}")
                print(f"   => Energy Score : {result.score} (Tier: {result.dominant_tier})")
                print(
                    f"   => Hooks First Seen: {result.first_seen_count} | "
                    f"Rare: {result.rare_count} | Frequent: {result.frequent_count}"
                )

                if result.blindspot_hits > 0:
                    print(f"   => BONUS blindspot: {result.blindspot_hits}")
                if result.new_hooks_discovered > 0:
                    print(f"   => BONUS new hooks: {result.new_hooks_discovered}")

            time.sleep(1)
    except KeyboardInterrupt:
        print("\nDang luu state va thoat...")
        scheduler.save_state()
        print("Tam biet!")


if __name__ == "__main__":
    main()
