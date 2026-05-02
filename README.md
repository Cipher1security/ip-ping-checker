# ip-ping-checker

Fast multi threaded IP ping scanner Check which IPs are alive from a list

## Installation

```bash
git clone https://github.com/Cipher1security/ip-ping-checker.git
cd ip-ping-checker
```

## Usage

### Interactive mode

python3 ip-ping-checker.py

Paste your IP list and press Enter twice to start

### From file

python3 ip-ping-checker.py ips.txt

### Save results to file

python3 ip-ping-checker.py ips.txt -o alive.txt

### Custom settings

python3 ip-ping-checker.py ips.txt -o result.txt -t 1 -w 300

### Options

-o, --output    Output file path (default: none)
-t, --timeout   Ping timeout in seconds (default: 2)
-w, --workers   Max threads (default: 200)
-h, --help      Show help

## Input Formats

ips.txt:

# Single IP
8.8.8.8

# IP with port (port is ignored)
1.2.3.4:443

# Range
192.168.1.1-192.168.1.254

# Short range
10.0.0.1-50
