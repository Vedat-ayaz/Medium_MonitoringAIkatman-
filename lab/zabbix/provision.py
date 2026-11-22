"""Lab Zabbix'ini hazırlar: 'Zabbix server' host'unu etkinleştirir, kısa aralıklı item ve trigger ekler.

Kullanım: python3 lab/zabbix/provision.py --url http://127.0.0.1:8081 --user Admin --password zabbix
(Zabbix 5.0 trigger ifade söz dizimi kullanılır; 6.0+ için ifadeler farklıdır.)
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from alerthealth.adapters.zabbix import ZabbixClient  # noqa: E402

HOST = "Zabbix server"
ITEMS = [  # (ad, anahtar, değer tipi: 0=float 3=uint)
    ("Lab: load per CPU (1m)", "system.cpu.load[percpu,avg1]", 0),
    ("Lab: running processes", "proc.num[,,run]", 3),
]
TRIGGERS = [  # (ad, ifade, öncelik: 2=warning 3=average 4=high)
    ("Lab: High load per CPU", "{%s:system.cpu.load[percpu,avg1].last()}>0.5" % HOST, 2),
    ("Lab: Many running processes", "{%s:proc.num[,,run].last()}>3" % HOST, 3),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8081")
    ap.add_argument("--user", default="Admin")
    ap.add_argument("--password", default="zabbix")
    args = ap.parse_args()

    zbx = ZabbixClient(args.url, user=args.user, password=args.password)
    host = zbx.call("host.get", {"filter": {"host": [HOST]}, "selectInterfaces": ["interfaceid", "type", "main"]})[0]
    zbx.call("host.update", {"hostid": host["hostid"], "status": 0})
    interface = next(i for i in host["interfaces"] if i["type"] == "1")

    existing = {i["key_"] for i in zbx.call("item.get", {"hostids": host["hostid"], "output": ["key_"]})}
    for name, key, value_type in ITEMS:
        if key not in existing:
            zbx.call("item.create", {"name": name, "key_": key, "hostid": host["hostid"], "type": 0,
                                     "value_type": value_type, "delay": "10s",
                                     "interfaceid": interface["interfaceid"]})
            print("item:", key)

    have = {t["description"] for t in zbx.call("trigger.get", {"hostids": host["hostid"], "output": ["description"]})}
    for name, expression, priority in TRIGGERS:
        if name not in have:
            zbx.call("trigger.create", {"description": name, "expression": expression, "priority": priority})
            print("trigger:", name)
    print("hazır:", HOST, host["hostid"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
