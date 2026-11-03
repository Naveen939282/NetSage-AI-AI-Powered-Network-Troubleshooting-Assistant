"""Tests for the evidence-normalization layer (checker/normalize.py)."""
from checker import normalize as N

VLAN_BRIEF = """\
    1    default                          active    Fa1/0/1
   10   SALES                            active    Fa1/0/2
   20   ENG                              active
"""

IFACE_STATUS = """\
Gi0/1                      connected    trunk      a-full  a-100
Gi0/2                      notconnect   1          auto    auto
"""

IP_BRIEF = """\
Interface              IP-Address      OK?   Method   Status               Protocol
Gi0/0                  192.168.1.1    YES   unset    up                   up
Gi0/1                  10.0.0.1       YES   unset    administratively down down
"""

ROUTES = """\
Gateway of last resort is 10.0.0.1
S*   0.0.0.0/0 [1/0] via 10.0.0.1
S    10.1.0.0/16 [1/0] via 10.0.0.2
C    10.0.0.0/24 is directly connected, Ethernet0/0
"""

ARP = """\
Protocol  Address          Age   Hardware Addr    Type   Interface
Internet  10.0.0.2         0     5254.0001.0002  ARPA  Ethernet0/0
Internet  10.0.0.3         5     5254.0001.0003  ARPA  Ethernet0/1
"""

ACL = """\
Extended IP access list 100
    100 deny tcp any any
    110 permit udp any any
"""

DNS = """\
       DNS servers configured:
       10.0.0.1
       10.0.0.2
"""

NAT_STATS = """\
Total translations: 5 (0 dynamic, 5 static)
Active translations: 3
"""

DHCP_POOL = """\
Pool LAN: 192.168.1.0 192.168.1.1-192.168.1.100 used 30 free 70
"""


def _section(name, body):
    return f"R1#{name}\n{body}\n"


SHOW = "".join([
    _section("show vlan brief", VLAN_BRIEF),
    _section("show interfaces status", IFACE_STATUS),
    _section("show ip interface brief", IP_BRIEF),
    _section("show ip arp", ARP),
    _section("show ip route", ROUTES),
    _section("show ip access-lists", ACL),
    _section("show ip dns", DNS),
    _section("show ip nat statistics", NAT_STATS),
    _section("show ip dhcp pool", DHCP_POOL),
])


def test_split_sections_parses_commands():
    sections = N.split_sections("R1#show ip arp\nline-a\nline-b\n")
    assert "show ip arp" in sections
    assert sections["show ip arp"] == ["line-a", "line-b"]


def test_section_key_strips_prompt():
    assert N._section_key("Router1>show version") == "show version"
    assert N._section_key("R1#show ip route") == "show ip route"
    assert N._section_key("plain output line") is None


def test_vlan_brief_parsed():
    v = N._parse_vlan_brief(VLAN_BRIEF)
    assert v["1"]["name"] == "default"
    assert v["1"]["ports"] == ["Fa1/0/1"]
    assert v["10"]["name"] == "SALES" and v["10"]["ports"] == ["Fa1/0/2"]
    assert v["20"]["ports"] == []


def test_interface_status_parsed():
    ifs = N._parse_interfaces_status(IFACE_STATUS)
    assert ifs["Gi0/1"]["oper_status"] == "up"
    assert ifs["Gi0/1"]["vlan"] == "trunk"
    assert ifs["Gi0/2"]["oper_status"] == "down"
    assert ifs["Gi0/2"]["admin_status"] == "down"
    assert ifs["Gi0/2"]["vlan"] == "1"


def test_ip_brief_parsed():
    rows = N._parse_ip_brief(IP_BRIEF)
    by_if = {r["interface"]: r for r in rows}
    assert by_if["Gi0/0"]["ip"] == "192.168.1.1"
    assert by_if["Gi0/0"]["oper_status"] == "up"
    assert by_if["Gi0/1"]["ip"] == "10.0.0.1"
    assert by_if["Gi0/1"]["oper_status"] == "down"


def test_routes_parsed():
    r = N._parse_routes(ROUTES)
    assert r["default_route"] == {"next_hop": "10.0.0.1"}
    assert r["static_routes"] == [{"network": "10.1.0.0/16",
                                  "next_hop": "10.0.0.2"}]
    assert r["connected_subnets"] == [{"network": "10.0.0.0/24",
                                      "interface": "Ethernet0/0"}]


def test_arp_parsed():
    a = N._parse_arp(ARP)
    assert a[0]["ip"] == "10.0.0.2"
    assert a[0]["mac"] == "5254.0001.0002"
    assert a[0]["type"] == "ARPA"
    assert a[0]["interface"] == "Ethernet0/0"


def test_acls_parsed():
    acls = N._parse_acls(ACL)
    deny = [a for a in acls if a["action"] == "deny"][0]
    assert deny["name"] == "100"
    assert deny["protocol"] == "tcp"
    assert deny["seq"] == "100"


def test_dns_parsed_multiline():
    assert N._parse_dns(DNS) == ["10.0.0.1", "10.0.0.2"]


def test_dns_parses_name_server_directive():
    text = "ip name-server 192.168.0.1 192.168.0.2"
    assert N._parse_dns(text) == ["192.168.0.1", "192.168.0.2"]


def test_nat_stats_parsed():
    n = N._parse_nat_stats(NAT_STATS)
    assert n["total"] == 5
    assert n["active"] == 3


def test_dhcp_pool_parsed():
    pools = N._parse_dhcp_pool(DHCP_POOL)
    p = pools[0]
    assert p["name"] == "LAN"
    assert p["network"] == "192.168.1.0"
    assert p["first"] == "192.168.1.1"
    assert p["last"] == "192.168.1.100"
    assert p["used"] == 30
    assert p["free"] == 70


def test_normalize_show_output_aggregates():
    e = N.normalize_show_output(SHOW)
    assert "show ip route" in e["raw_sections"]
    assert e["routes"]["default_route"] == {"next_hop": "10.0.0.1"}
    assert e["routes"]["static_routes"]
    assert e["routes"]["connected_subnets"]
    assert e["arp"][0]["ip"] == "10.0.0.2"
    assert "10" in e["vlan"]
    assert e["vlan"]["10"]["name"] == "SALES"
    assert e["acls"][0]["name"] == "100"
    assert e["dns_servers"] == ["10.0.0.1", "10.0.0.2"]
    assert e["nat_stats"]["total"] == 5
    assert e["nat_stats"]["active"] == 3
    assert e["dhcp_pools"][0]["name"] == "LAN"
    assert e["interface_status"]["Gi0/2"]["oper_status"] == "down"


def test_normalize_handles_empty_output():
    e = N.normalize_show_output("")
    assert e["raw_sections"] == []
    assert e["routes"]["default_route"] is None
    assert e["arp"] == []
    assert e["vlan"] == {}


def test_normalize_works_on_real_case():
    from utils.csv_loader import case_by_id
    case = case_by_id("NETSAGE-002")
    e = N.normalize_show_output(case.show_output)
    assert isinstance(e, dict)
    assert "routes" in e and "arp" in e
