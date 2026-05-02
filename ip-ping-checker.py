import subprocess
import sys
import time
import os
import platform
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

TIMEOUT = 2
MAX_WORKERS = 200
OUTPUT_FILE = None

lock = Lock()
stats = {"alive": 0, "dead": 0}

SYSTEM = platform.system().lower()


def parse_ip_range(ip_range):
    if "-" not in ip_range:
        return [ip_range]
    start, end = ip_range.split("-")
    start_parts = start.split(".")
    if "." in end and len(end.split(".")) == 4:
        end_parts = end.split(".")
        if start_parts[:3] == end_parts[:3]:
            base = ".".join(start_parts[:3])
            return [f"{base}.{i}" for i in range(int(start_parts[3]), int(end_parts[3]) + 1)]
    if end.isdigit():
        base = ".".join(start_parts[:3])
        return [f"{base}.{i}" for i in range(int(start_parts[3]), int(end) + 1)]
    return [ip_range]


def parse_targets(raw_text):
    if not raw_text or not raw_text.strip():
        return []
    results = []
    for line in raw_text.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line and "-" not in line:
            ip = line.rsplit(":", 1)[0]
        else:
            ip = line
        if "-" in ip:
            results.extend(parse_ip_range(ip))
        else:
            results.append(ip)
    return results


def ping(ip):
    if SYSTEM == "windows":
        cmd = ["ping", "-n", "1", "-w", str(TIMEOUT * 1000), ip]
    else:
        cmd = ["ping", "-c", "1", "-W", str(TIMEOUT), ip]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT + 1)
        if res.returncode == 0:
            latency = None
            if "time=" in res.stdout:
                latency = res.stdout.split("time=")[1].split()[0].replace("ms", "")
            elif "time<" in res.stdout:
                latency = "<1"
            return (ip, True, latency)
    except:
        pass

    return (ip, False, None)


def save_results(alive_ips, filename):
    try:
        full_path = os.path.abspath(filename)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(f"Alive IPs - {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total: {len(alive_ips)}\n")
            for ip, lat in alive_ips:
                l = f"{lat}ms" if lat else "-"
                f.write(f"{ip:<15} {l}\n")
            f.write(f"\nIP only:\n")
            for ip, _ in alive_ips:
                f.write(f"{ip}\n")

        if os.path.exists(full_path):
            size = os.path.getsize(full_path)
            print(f"Saved: {full_path} ({size} bytes)")
            return True
        else:
            print(f"Error: File not created at {full_path}")
            return False

    except PermissionError:
        print(f"Error: Permission denied: {filename}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False


def parse_args():
    global TIMEOUT, MAX_WORKERS, OUTPUT_FILE

    args = sys.argv[1:]
    input_file = None
    i = 0

    while i < len(args):
        arg = args[i]

        if arg == "-o" or arg == "--output":
            if i + 1 < len(args):
                OUTPUT_FILE = args[i + 1]
                i += 2
            else:
                print("Error: -o requires a filename")
                sys.exit(1)

        elif arg == "-t" or arg == "--timeout":
            if i + 1 < len(args):
                TIMEOUT = float(args[i + 1])
                i += 2
            else:
                print("Error: -t requires a value")
                sys.exit(1)

        elif arg == "-w" or arg == "--workers":
            if i + 1 < len(args):
                MAX_WORKERS = int(args[i + 1])
                i += 2
            else:
                print("Error: -w requires a value")
                sys.exit(1)

        elif arg == "-h" or arg == "--help":
            print("ip-ping IP ping checker")
            print("Usage:")
            print("  python3 pingsweep.py Interactive mode")
            print("  python3 pingsweep.py ips.txt From file")
            print("  python3 pingsweep.py ips.txt -o alive.txt Save output")
            print("Options:")
            print("  -o, --output FILE Save alive IPs to file")
            print("  -t, --timeout SEC Ping timeout (default: 2)")
            print("  -w, --workers N Max threads (default: 200)")
            print("  -h, --help Show this help")
            print("Input formats:")
            print("  192.168.1.1 Single IP")
            print("  192.168.1.1:443 Port ignored, IP only")
            print("  192.168.1.1-192.168.1.254 Range")
            print("  192.168.1.1-254 Short range")
            sys.exit(0)

        elif not arg.startswith("-"):
            input_file = arg
            i += 1

        else:
            print(f"Unknown option: {arg}")
            sys.exit(1)

    return input_file


def main():
    input_file = parse_args()

    if input_file:
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                raw = f.read()
            print(f"Loaded: {input_file}")
        except FileNotFoundError:
            print(f"Error: File not found: {input_file}")
            return
    else:
        print("Enter IPs (empty line to start):")
        lines = []
        while True:
            try:
                line = sys.stdin.readline().rstrip("\n")
            except (EOFError, KeyboardInterrupt):
                break
            if not line:
                break
            lines.append(line)
        raw = "\n".join(lines)

    targets = parse_targets(raw)

    if not targets:
        print("Error: No IPs found")
        return

    targets = list(dict.fromkeys(targets))

    print(f"\nTargets: {len(targets)}")
    print(f"Threads: {MAX_WORKERS}")
    print(f"Timeout: {TIMEOUT}s")
    if OUTPUT_FILE:
        print(f"Output:  {OUTPUT_FILE}")
    print()

    start = time.time()
    results = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(ping, ip): ip for ip in targets}
        for f in as_completed(futures):
            ip, alive, latency = f.result()
            results.append((ip, alive, latency))
            with lock:
                if alive:
                    stats["alive"] += 1
                else:
                    stats["dead"] += 1
                sys.stdout.write(f"\rAlive: {stats['alive']} | Dead: {stats['dead']}    ")
                sys.stdout.flush()

    elapsed = time.time() - start

    alive_ips = [(ip, lat) for ip, alive, lat in results if alive]
    dead_ips = [ip for ip, alive, _ in results if not alive]

    print(f"\n\nResults")
    print(f"Alive : {len(alive_ips)}")
    print(f"Dead  : {len(dead_ips)}")
    print(f"Time  : {elapsed:.1f}s")

    if alive_ips:
        alive_ips.sort(key=lambda x: float(x[1]) if x[1] and x[1] != "<1" else 0)
        for ip, lat in alive_ips:
            l = f"{lat}ms" if lat else "-"
            print(f"  {ip:<15} {l}")

        if OUTPUT_FILE:
            print()
            save_results(alive_ips, OUTPUT_FILE)

    if dead_ips:
        dead_list = ", ".join(dead_ips[:15])
        print(f"\nDead: {dead_list}")
        if len(dead_ips) > 15:
            print(f"      ... and {len(dead_ips) - 15} more")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped")
        sys.exit(0)
