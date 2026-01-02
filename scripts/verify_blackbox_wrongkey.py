#!/usr/bin/env python3
"""
Verify CLI (wrong key): Always reject (for T3 test).
"""

import sys
import json


def main():
    _ = json.load(sys.stdin)
    print(json.dumps({"status": "REJECT"}, separators=(",", ":")))


if __name__ == "__main__":
    main()
