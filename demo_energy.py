import sys
import os
import json
import time
import glob
import atexit

# Add path so we can import energy.py
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "fuzzer-core", "fuzzing"))

try:
    from energy import EnergyScheduler
except ImportError:
    print("Cannot import energy module. Make sure fuzzer-core/fuzzing/energy.py exists.")
    sys.exit(1)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
REQUESTS_DIR = os.path.join(OUTPUT_DIR, "requests")
LOCK_FILE = os.path.join(OUTPUT_DIR, "energy_demo.lock")

def cleanup():
    """Xóa file lock khi script thoát để PHP lại tiếp tục chặn log tiết kiệm I/O"""
    if os.path.exists(LOCK_FILE):
        try:
            os.remove(LOCK_FILE)
        except:
            pass

def setup_lock():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(REQUESTS_DIR, exist_ok=True)
    
    # Tạo lock file: Khi PHP thấy file này, nó sẽ âm thầm đính kèm hook_coverage
    # vào request.json cho ta đo đạc real-time (tương tác liên hoàn)
    with open(LOCK_FILE, "w") as f:
        f.write("active")
    atexit.register(cleanup)

def wait_for_new_requests():
    print("\n" + "=" * 70)
    print("   📡 BỘ THEO DÕI LIVE ENERGY (RADAR) ĐÃ ĐƯỢC BẬT 📡")
    print("=" * 70)
    print(" [MẸO] Hãy mở trình duyệt, bấm thoải mái vào các link trên WordPress!")
    print(" Script này sẽ thu trộm các request sinh ra và tính toán điểm tại chỗ.")
    print(" Bấm Ctrl+C để thoát. (Sẽ tự động trả PHP về file tiết kiệm I/O khi thoát)")
    print("-" * 70 + "\n")
    
    scheduler = EnergyScheduler(
        requests_dir=REQUESTS_DIR,
        snapshot_path=os.path.join(OUTPUT_DIR, "total_coverage.json")
    )
    scheduler.load_previous_state()
    
    # Lấy lướt qua các file cũ đang có để không in lại
    processed_files = set(glob.glob(os.path.join(REQUESTS_DIR, "*.json")))
    api_call_count = 0
    
    try:
        while True:
            current_files = set(glob.glob(os.path.join(REQUESTS_DIR, "*.json")))
            new_files = sorted(list(current_files - processed_files), key=os.path.getmtime)
            
            for file_path in new_files:
                time.sleep(0.05) # Chờ xíu để PHP flush data Json xong
                
                filename = os.path.basename(file_path)
                req_id = filename.replace(".json", "")
                
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        request_data = json.load(f)
                except Exception:
                    continue
                
                method = request_data.get("http_method", "GET")
                target = request_data.get("http_target", req_id)
                
                # Lỡ PHP bị crash hụt lúc sinh JSON:
                if "hook_coverage" not in request_data:
                    processed_files.add(file_path)
                    continue

                api_call_count += 1
                energy_result = scheduler.get_energy_for_request(request_data)
                
                # Cập nhật lịch sử state trong in-memory
                scheduler.processed_ids.add(req_id)
                scheduler.state.update_from_request(request_data)
                
                print(f"[Call #{api_call_count}] [{method}] {target}")
                print(f" ⚡ Energy: {energy_result.score: <4} | Trội nhất: {energy_result.dominant_tier.upper(): <12} | New Hooks: {energy_result.new_hooks_discovered} | Blindspots: {energy_result.blindspot_hits}")
                
                # Hiển thị số lần gọi của từng hàm
                executed_callbacks = request_data.get("hook_coverage", {}).get("executed_callbacks", {})
                if executed_callbacks:
                    print(" 🔍 Số lần gọi của các hàm (Execution Count):")
                    func_counts = []
                    for cb_id, cb_info in executed_callbacks.items():
                        func_name = cb_info.get("callback_repr", "Unknown")
                        hook_name = cb_info.get("hook_name", "Unknown")
                        count = cb_info.get("executed_count", 0)
                        func_counts.append((func_name, hook_name, count))
                    
                    # Sắp xếp giảm dần theo số lần gọi
                    func_counts.sort(key=lambda x: x[2], reverse=True)
                    
                    # In ra tối đa 10 hàm được gọi nhiều nhất
                    for func_name, hook_name, count in func_counts[:10]:
                        print(f"    - {func_name} (Hook: {hook_name}): {count} lần")
                    
                    if len(func_counts) > 10:
                        print(f"    ... và {len(func_counts) - 10} hàm khác.")
                        
                print("-" * 70)
                
                processed_files.add(file_path)
                
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        print("\n\n[+] Đã tắt Radar. Đã dọn dẹp biến tạm!")

if __name__ == "__main__":
    setup_lock()
    wait_for_new_requests()
