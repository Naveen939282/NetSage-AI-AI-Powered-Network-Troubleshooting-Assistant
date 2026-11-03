#!/usr/bin/env python3
"""
NetSage-AI - dataset generator.

Produces:
    data/cases.csv            (30 troubleshooting cases, exactly 12 columns)
    data/responsible_ai_log.csv (5 historical human-corrected diagnoses)
    data/sample_cases.json     (3 demo cases + difficulty map for the UI)

Difficulty (10 easy / 12 medium / 8 hard) is tracked per case but NOT
written to cases.csv (the CSV schema is fixed at 12 fields).
"""
from __future__ import annotations

import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

CSV_FIELDS = [
    "case_id", "category", "title", "symptom", "topology", "show_output",
    "expected_fault", "osi_layer", "concept", "severity",
    "expected_command", "expected_fix",
]

# Each case is a dict. `difficulty` is metadata only (not written to cases.csv).
CASES = [
    {
        "case_id": "NETSAGE-001",
        "category": "VLAN",
        "title": "Wrong access VLAN assigned to host port",
        "symptom": "PC-A (192.168.20.10/24) cannot reach servers in VLAN 20. The host replies to ping within its own IP but cannot reach 192.168.20.2. PC-A should be in the SERVERS VLAN (20).",
        "topology": "PC-A -- Gi0/2 -- SwitchA -- Gi0/1 -- RouterB. Intended: PC-A belongs to VLAN 20 (SERVERS).",
        "show_output": """show vlan brief
VLAN Name                             Status    Ports
---- -------------------------------- --------- -----------------------------
1    default                          active
10   USERS                            active    Fa0/2 Fa0/3
20   SERVERS                          active    Fa0/5

show interfaces status
Port      Name               Status       Vlan       Duplex Speed   Type
Gi0/1     trunk-to-RouterB   connected    trunk      a-full  a-1000  1000BaseSX
Gi0/2     to-PC-A            connected    10         a-full  a-1000
Gi0/3                        connected    10         a-full  a-1000
Gi0/5                        connected    20         a-full  a-1000

show interfaces switchport
Name               : Gi0/2
Switchport Mode      : access
Access Mode VLAN     : 10
""",
        "expected_fault": "Port Gi0/2 is assigned to access VLAN 10 (USERS) instead of VLAN 20 (SERVERS)",
        "osi_layer": "Layer 2",
        "concept": "access vlan assignment",
        "severity": "HIGH",
        "expected_command": "show interfaces Gi0/2 status",
        "expected_fix": "On SwitchA, enter interface Gi0/2 and run: switchport access vlan 20",
        "difficulty": "easy",
    },
    {
        "case_id": "NETSAGE-002",
        "category": "VLAN",
        "title": "VLAN 30 missing from the switch database",
        "symptom": "Hosts that should be in VLAN 30 (DB) cannot communicate. Port Gi0/4 is configured for VLAN 30 but shows notconnect.",
        "topology": "SwitchA is meant to host VLAN 30 (DB) on Gi0/4. Only VLANs 10 and 20 exist in the VLAN database.",
        "show_output": """show vlan brief
VLAN Name                             Status    Ports
---- -------------------------------- --------- -----------------------------
1    default                          active
10   USERS                            active    Fa0/2
20   SERVERS                          active    Fa0/3

show interfaces status
Port      Name               Status       Vlan       Duplex Speed   Type
Gi0/1     trunk            connected    trunk      a-full  a-1000
Gi0/2                        connected    10         a-full  a-1000
Gi0/3                        connected    20         a-full  a-1000
Gi0/4     to-DB-host         notconnect   30         auto    auto

show interfaces switchport
Name                : Gi0/4
Administrative Mode : static access
Access Mode VLAN    : 30
""",
        "expected_fault": "VLAN 30 is not present in the VLAN database, yet Gi0/4 is configured for access VLAN 30",
        "osi_layer": "Layer 2",
        "concept": "vlan creation",
        "severity": "HIGH",
        "expected_command": "show vlan brief",
        "expected_fix": "Create the missing VLAN: vlan 30 ; name DB ; exit",
        "difficulty": "easy",
    },
        {
        "case_id": "NETSAGE-003",
        "category": "VLAN",
        "title": "Trunk permits only VLANs 10 and 20",
        "symptom": "Servers in VLAN 30 (DB) are reachable from the local switch but not across the inter-switch trunk. Traffic appears blocked over the trunk link.",
        "topology": "SwitchA and SwitchB are interconnected by a trunk on Gi0/1. VLAN 30 exists for database servers but may not be allowed on the trunk.",
        "show_output": """show vlan brief
VLAN Name                             Status    Ports
---- -------------------------------- --------- -----------------------------
10   USERS                            active    Fa0/2 Fa0/1
20   SERVERS                          active    Fa0/3 Fa0/1
30   DB                               active    Fa0/5

show interfaces trunk
Port        Mode          Encapsulation Status        Native Vlan  Vlans Allowed on Trunk
Gi0/1       desirable     802.1q        operational 1            10,20
""",
        "expected_fault": "Trunk Gi0/1 allows only VLANs 10 and 20; VLAN 30 is missing from the allowed-vlan list",
        "osi_layer": "Layer 2",
        "concept": "trunk allowed vlan",
        "severity": "MEDIUM",
        "expected_command": "show interfaces trunk",
        "expected_fix": "Add VLAN 30 to the trunk: switchport trunk allowed vlan add 30",
        "difficulty": "hard",
    },
    {
        "case_id": "NETSAGE-004",
        "category": "VLAN",
        "title": "Native VLAN mismatch on trunk",
        "symptom": "Intermittent connectivity and a flapping trunk. Some frames are dropped across the SwitchA-SwitchB trunk link.",
        "topology": "SwitchA Gi0/1 trunks to SwitchB Gi0/1. The native VLAN must match on both ends (SwitchB uses 999).",
        "show_output": """show interfaces trunk
Port        Mode          Encapsulation Status        Native Vlan  Vlans Allowed on Trunk
Gi0/1       trunk         802.1q        operational 1            10,20,30

show interfaces switchport
Name                : Gi0/1
Switchport Mode      : trunk
Administrative Native Vlan : 1
Operational Native Vlan    : 1
""",
        "expected_fault": "Native VLAN mismatch: SwitchA uses native VLAN 1 while SwitchB is configured for native VLAN 999",
        "osi_layer": "Layer 2",
        "concept": "native vlan mismatch",
        "severity": "HIGH",
        "expected_command": "show interfaces trunk",
        "expected_fix": "Configure a matching native VLAN on both ends (e.g. switchport trunk native vlan 999)",
        "difficulty": "medium",
    },
    {
        "case_id": "NETSAGE-005",
        "category": "VLAN",
        "title": "Newly created VLAN not added to trunk allowed list",
        "symptom": "After creating VLAN 40 for a new office, hosts there cannot reach the rest of the network through the trunk.",
        "topology": "SwitchA trunk to SwitchB. VLAN 40 was created on SwitchA only and not permitted on the trunk.",
        "show_output": """show vlan brief
VLAN Name                             Status    Ports
---- -------------------------------- --------- -----------------------------
10   USERS                            active    Fa0/2 Fa0/1
20   SERVERS                          active    Fa0/3 Fa0/1
40   NEW-OFFICE                       active    Fa0/6

show interfaces trunk
Port        Mode          Encapsulation Status        Native Vlan  Vlans Allowed on Trunk
Gi0/1       trunk         802.1q        operational 1            10,20
""",
        "expected_fault": "VLAN 40 exists in the VLAN database but is not permitted on the trunk Gi0/1",
        "osi_layer": "Layer 2",
        "concept": "trunk allowed vlan",
        "severity": "MEDIUM",
        "expected_command": "show interfaces trunk",
        "expected_fix": "Allow VLAN 40 on the trunk: switchport trunk allowed vlan add 40",
        "difficulty": "medium",
    },
        {
        "case_id": "NETSAGE-006",
        "category": "Default Gateway",
        "title": "Incorrect default gateway IP on host",
        "symptom": "Host 192.168.10.50 can reach local VLAN resources but nothing beyond the local subnet.",
        "topology": "Host 192.168.10.50/24 with a mis-configured default gateway (192.168.10.254 instead of the real .1).",
        "show_output": """show ip route
S*   0.0.0.0/0 [1/0] via 192.168.10.254
C    192.168.10.0/24 is directly connected, Vlan10

show ip interface brief
Interface              IP-Address      OK? Method Protocol Interface
Vlan10                 192.168.10.50   YES manual up     up
""",
        "expected_fault": "Default gateway 192.168.10.254 is not responding; the correct gateway is 192.168.10.1",
        "osi_layer": "Layer 3",
        "concept": "default gateway",
        "severity": "HIGH",
        "expected_command": "ping 192.168.10.1",
        "expected_fix": "Configure the host default gateway to 192.168.10.1",
        "difficulty": "easy",
    },
    {
        "case_id": "NETSAGE-007",
        "category": "Default Gateway",
        "title": "Default gateway outside host subnet",
        "symptom": "Host 192.168.20.15 cannot reach any external network; the configured default gateway is unreachable.",
        "topology": "Host 192.168.20.15/24 has gateway 192.168.10.1, which is outside its subnet.",
        "show_output": """show ip route
S*   0.0.0.0/0 [1/0] via 192.168.10.1
C    192.168.20.0/24 is directly connected, Vlan20
C    10.0.0.0/24 is directly connected, Ethernet0/0

show ip interface brief
Interface              IP-Address      OK? Method Protocol Interface
Vlan20                 192.168.20.15   YES manual up     up
""",
        "expected_fault": "Default gateway 192.168.10.1 is outside the host subnet 192.168.20.0/24",
        "osi_layer": "Layer 3",
        "concept": "gateway outside subnet",
        "severity": "HIGH",
        "expected_command": "show ip route",
        "expected_fix": "Set the gateway to an address within 192.168.20.0/24 (e.g. 192.168.20.1)",
        "difficulty": "medium",
    },
    {
        "case_id": "NETSAGE-008",
        "category": "Default Gateway",
        "title": "SVI administratively down disables the gateway",
        "symptom": "All hosts in VLAN 30 lose default-gateway connectivity; the VLAN 30 SVI is not forwarding.",
        "topology": "The Vlan30 SVI on the Layer 3 switch is administratively down.",
        "show_output": """show ip interface brief
Interface              IP-Address      OK? Method Protocol Interface
Vlan30                 192.168.30.1    YES manual administratively down down

show interfaces Vlan30
Vlan30 is administratively down, line protocol is down
  Hardware is iGbE, address is 5000.0001.0001
  Internet address is 192.168.30.1/24

show ip route
S*   0.0.0.0/0 [1/0] via 192.168.10.1
C    192.168.10.0/24 is directly connected, Vlan10
""",
        "expected_fault": "The Vlan30 SVI (192.168.30.1) is administratively down, so it cannot act as a gateway",
        "osi_layer": "Layer 3",
        "concept": "interface administratively down",
        "severity": "HIGH",
        "expected_command": "show ip interface brief",
        "expected_fix": "Re-enable the SVI: interface Vlan30 ; no shutdown",
        "difficulty": "medium",
    },
    {
        "case_id": "NETSAGE-009",
        "category": "Default Gateway",
        "title": "No default gateway or default route on host",
        "symptom": "Host 192.168.40.20 has no default route; it can only reach its local VLAN 40.",
        "topology": "Host 192.168.40.20/24 with no ip route 0.0.0.0/0 and no default-gateway statement.",
        "show_output": """show ip route
C    192.168.40.0/24 is directly connected, Vlan40

show ip interface brief
Interface              IP-Address      OK? Method Protocol Interface
Vlan40                 192.168.40.20   YES manual up     up
""",
        "expected_fault": "No default route (0.0.0.0/0 / S*) exists in the routing table",
        "osi_layer": "Layer 3",
        "concept": "default gateway",
        "severity": "HIGH",
        "expected_command": "show ip route",
        "expected_fix": "Add a default route: ip route 0.0.0.0 0.0.0.0 192.168.40.1",
        "difficulty": "easy",
    },
        {
        "case_id": "NETSAGE-010",
        "category": "DHCP",
        "title": "DHCP pool missing for a VLAN",
        "symptom": "Clients in VLAN 10 (192.168.10.0/24) receive APIPA addresses 169.254.x.x instead of 192.168.10.x.",
        "topology": "The DHCP server has pools for VLAN 20 and 30 but none for VLAN 10, even though Vlan10 has an SVI.",
        "show_output": """show ip route
C    192.168.10.0/24 is directly connected, Vlan10
C    192.168.20.0/24 is directly connected, Vlan20

show ip dhcp pool
Pool VLAN20-POOL: 192.168.20.0/24 192.168.20.10-192.168.20.29 used 1 free 19

show ip dhcp binding
IP address      Hardware address   Type        Lease
192.168.20.10   0001.0c10.000a    Automatic   86400
""",
        "expected_fault": "No DHCP pool is configured for the VLAN 10 (192.168.10.0/24) subnet",
        "osi_layer": "Layer 7",
        "concept": "dhcp pool",
        "severity": "HIGH",
        "expected_command": "show ip dhcp pool",
        "expected_fix": "Create a pool: ip dhcp pool VLAN10-POOL ; network 192.168.10.0 255.255.255.0 ; default-router 192.168.10.1",
        "difficulty": "easy",
    },
    {
        "case_id": "NETSAGE-011",
        "category": "DHCP",
        "title": "Excluded address range overlaps the DHCP pool",
        "symptom": "Some hosts in VLAN 20 receive duplicate-IP warnings; the DHCP server can hand out a reserved address.",
        "topology": "The DHCP pool for VLAN 20 includes addresses that overlap with the excluded-address range.",
        "show_output": """show ip dhcp pool
Pool VLAN20-POOL: 192.168.20.0/24 192.168.20.1-192.168.20.20 used 2 free 18

show ip dhcp excluded-address
192.168.20.10 - 192.168.20.15

show ip dhcp binding
IP address      Hardware address   Type        Lease
192.168.20.12   0001.0c10.0012    Automatic   86400
""",
        "expected_fault": "Excluded range 192.168.20.10-15 overlaps the DHCP pool range 192.168.20.1-20",
        "osi_layer": "Layer 7",
        "concept": "dhcp excluded address",
        "severity": "MEDIUM",
        "expected_command": "show ip dhcp excluded-address",
        "expected_fix": "Remove the overlap so the excluded range and the pool range do not intersect",
        "difficulty": "medium",
    },
    {
        "case_id": "NETSAGE-012",
        "category": "DHCP",
        "title": "DHCP relay (ip helper) missing on SVI",
        "symptom": "VLAN 30 clients do not get an IP address. The DHCP server lives on VLAN 10 and the relay agent was removed.",
        "topology": "DHCP server on Vlan10 (192.168.10.5). VLAN 30 (192.168.30.0/24) has no ip helper-address.",
        "show_output": """show running-config | section interface
interface Vlan10
 ip address 192.168.10.1 255.255.255.0
 ip helper-address 192.168.10.5
interface Vlan30
 ip address 192.168.30.1 255.255.255.0
 no ip helper-address

show ip dhcp server statistics
Total DHCP packet count: 0
""",
        "expected_fault": "Vlan30 is missing ip helper-address pointing to the DHCP server 192.168.10.5",
        "osi_layer": "Layer 3",
        "concept": "dhcp relay",
        "severity": "HIGH",
        "expected_command": "show running-config interface Vlan30",
        "expected_fix": "Add under interface Vlan30: ip helper-address 192.168.10.5",
        "difficulty": "medium",
    },
    {
        "case_id": "NETSAGE-013",
        "category": "DHCP",
        "title": "DHCP scope exhausted - no free addresses",
        "symptom": "New VLAN 40 clients fail to get an IP address; existing clients renew fine. The pool appears full.",
        "topology": "DHCP pool for VLAN 40 has size 5 and is fully utilized.",
        "show_output": """show ip dhcp pool
Pool VLAN40-POOL: 192.168.40.0/24 192.168.40.10-192.168.40.14 used 5 free 0

show ip dhcp binding
IP address      Hardware address   Type        Lease
192.168.40.10   0001.0c10.0020    Automatic   86400
192.168.40.11   0001.0c10.0021    Automatic   86400
192.168.40.12   0001.0c10.0022    Automatic   86400
192.168.40.13   0001.0c10.0023    Automatic   86400
192.168.40.14   0001.0c10.0024    Automatic   86400
""",
        "expected_fault": "DHCP pool VLAN40-POOL is fully allocated (5 of 5 used), leaving no free addresses",
        "osi_layer": "Layer 7",
        "concept": "dhcp scope exhausted",
        "severity": "MEDIUM",
        "expected_command": "show ip dhcp pool",
        "expected_fix": "Expand the pool size or reduce excluded addresses so free addresses are available",
        "difficulty": "hard",
    },
        {
        "case_id": "NETSAGE-014",
        "category": "DNS",
        "title": "DNS server unreachable (no route)",
        "symptom": "Clients can ping 8.8.8.8 but cannot resolve hostnames; DNS queries time out.",
        "topology": "DNS server 10.0.0.10 is configured but there is no route to the 10.0.0.0/8 network.",
        "show_output": """show ip dns
DNS Servers: 10.0.0.10
Domain: company.local

show ip route
S*   0.0.0.0/0 [1/0] via 192.168.10.1
C    192.168.10.0/24 is directly connected, Vlan10

show ip arp
Internet  192.168.10.1     0   001b.638a.0101   ARPA   Vlan10
Internet  192.168.10.50    0   001b.638a.0402   ARPA   Vlan10
""",
        "expected_fault": "Configured DNS server 10.0.0.10 is not in any directly-connected subnet and has no route to it",
        "osi_layer": "Layer 7",
        "concept": "dns server unreachable",
        "severity": "MEDIUM",
        "expected_command": "show ip route 10.0.0.10",
        "expected_fix": "Add a route to the DNS server subnet or change the DNS server to a reachable IP",
        "difficulty": "easy",
    },
    {
        "case_id": "NETSAGE-015",
        "category": "DNS",
        "title": "DNS server host not responding",
        "symptom": "Host resolves old records; the primary DNS server returns stale data and should be decommissioned.",
        "topology": "Primary DNS 192.168.10.99 is no longer alive; the active server is 192.168.10.50, but the host still lists .99 first.",
        "show_output": """show ip dns
Primary DNS Server: 192.168.10.99
Secondary DNS Server: 192.168.10.50
Domain: company.local

show ip arp
Internet  192.168.10.50    0   001b.638a.0402   ARPA   Vlan10
Internet  192.168.10.51    5   001b.638a.0403   ARPA   Vlan10

show ip route
C    192.168.10.0/24 is directly connected, Vlan10
""",
        "expected_fault": "Configured primary DNS server 192.168.10.99 is absent from the ARP table (host not responding)",
        "osi_layer": "Layer 7",
        "concept": "incorrect dns configuration",
        "severity": "HIGH",
        "expected_command": "ping 192.168.10.99",
        "expected_fix": "Remove the stale DNS server 192.168.10.99 and use 192.168.10.50",
        "difficulty": "hard",
    },
    {
        "case_id": "NETSAGE-016",
        "category": "DNS",
        "title": "Secondary DNS server unreachable (split config)",
        "symptom": "Some clients resolve, others do not. DNS works intermittently depending on which server answers.",
        "topology": "Two DNS servers configured; the primary (192.168.50.10) responds but the secondary (192.168.99.10) is unreachable.",
        "show_output": """show ip dns
Primary DNS Server: 192.168.50.10
Secondary DNS Server: 192.168.99.10
Domain: company.local

show ip arp
Internet  192.168.50.10    0   001b.638a.0510   ARPA   Vlan50
Internet  192.168.50.1     0   001b.638a.0501   ARPA   Vlan50

show ip route
C    192.168.50.0/24 is directly connected, Vlan50
""",
        "expected_fault": "Secondary DNS server 192.168.99.10 is not in the ARP table and not in any connected subnet",
        "osi_layer": "Layer 7",
        "concept": "dns configuration",
        "severity": "MEDIUM",
        "expected_command": "ping 192.168.99.10",
        "expected_fix": "Point all clients to the reachable DNS server or restore routing to 192.168.99.10",
        "difficulty": "hard",
    },
        {
        "case_id": "NETSAGE-017",
        "category": "Routing",
        "title": "Static route with unreachable next-hop",
        "symptom": "Hosts in 192.168.10.0/24 cannot reach the 192.168.50.0/24 subnet even though a static route is configured.",
        "topology": "RouterA has a static route for 192.168.50.0/24 via next-hop 172.16.1.1, which is not directly connected.",
        "show_output": """show ip route
C    192.168.10.0/24 is directly connected, Vlan10
C    10.0.0.0/24 is directly connected, Ethernet0/0
S    192.168.50.0/24 [1/0] via 172.16.1.1
S*   0.0.0.0/0 [1/0] via 192.168.10.254
""",
        "expected_fault": "Static route 192.168.50.0/24 via 172.16.1.1 has an unreachable next-hop (not directly connected)",
        "osi_layer": "Layer 3",
        "concept": "invalid next hop",
        "severity": "HIGH",
        "expected_command": "show ip route",
        "expected_fix": "Correct the next-hop to a reachable address (e.g. via 192.168.10.254)",
        "difficulty": "easy",
    },
    {
        "case_id": "NETSAGE-018",
        "category": "Routing",
        "title": "Incorrect next-hop in static route",
        "symptom": "The 192.168.50.0/24 subnet is reachable but only intermittently; packets sometimes time out.",
        "topology": "Static route 192.168.50.0/24 points to next-hop 192.168.99.1, but the correct next-hop is 192.168.99.254.",
        "show_output": """show ip route
C    192.168.10.0/24 is directly connected, Vlan10
C    192.168.99.0/24 is directly connected, Ethernet0/1
S    192.168.50.0/24 [1/0] via 192.168.99.1
S*   0.0.0.0/0 [1/0] via 192.168.10.254
""",
        "expected_fault": "Static route 192.168.50.0/24 uses next-hop 192.168.99.1 instead of the correct 192.168.99.254",
        "osi_layer": "Layer 3",
        "concept": "incorrect static route",
        "severity": "MEDIUM",
        "expected_command": "show ip route",
        "expected_fix": "ip route 192.168.50.0 255.255.255.0 192.168.99.254",
        "difficulty": "medium",
    },
    {
        "case_id": "NETSAGE-019",
        "category": "Routing",
        "title": "Default route missing",
        "symptom": "The router can reach local and one static subnet but cannot forward traffic to the internet.",
        "topology": "RouterB has no default route (0.0.0.0/0) configured.",
        "show_output": """show ip route
C    192.168.10.0/24 is directly connected, Vlan10
C    192.168.20.0/24 is directly connected, Ethernet0/0
S    192.168.50.0/24 [1/0] via 192.168.10.254
""",
        "expected_fault": "No default route (0.0.0.0/0 / S*) exists in the routing table",
        "osi_layer": "Layer 3",
        "concept": "default route missing",
        "severity": "HIGH",
        "expected_command": "show ip route",
        "expected_fix": "Add a default route: ip route 0.0.0.0 0.0.0.0 192.168.10.254",
        "difficulty": "easy",
    },
    {
        "case_id": "NETSAGE-020",
        "category": "Routing",
        "title": "OSPF neighbor stuck in INIT (area mismatch)",
        "symptom": "Routes are not being learned via OSPF; the neighbor stays in a non-FULL state.",
        "topology": "RouterA and RouterB form an OSPF adjacency that never reaches FULL due to an area mismatch.",
        "show_output": """show ip ospf neighbor
Neighbor ID     Pri   State           Dead Time   Interface ID    Interface
10.0.0.2        128   INIT/DROTHER    00:00:05    3               Ethernet0/0

show ip ospf interface brief
Interface    Area    Cost  State
Ethernet0/0  0       10    DR
Vlan10       1       10    DR
""",
        "expected_fault": "OSPF neighbor 10.0.0.2 is stuck in INIT state due to an area mismatch (area 0 vs area 1)",
        "osi_layer": "Layer 3",
        "concept": "ospf area mismatch",
        "severity": "HIGH",
        "expected_command": "show ip ospf neighbor",
        "expected_fix": "Put both interfaces in the same OSPF area",
        "difficulty": "hard",
    },
    {
        "case_id": "NETSAGE-021",
        "category": "Routing",
        "title": "Wrong next-hop causing a blackhole",
        "symptom": "The 192.168.50.0/24 subnet is intermittently unreachable; the configured next-hop host does not respond.",
        "topology": "Static route 192.168.50.0/24 via 172.16.5.6; the correct next-hop router is 172.16.5.254.",
        "show_output": """show ip route
C    192.168.10.0/24 is directly connected, Vlan10
C    172.16.5.0/24 is directly connected, Ethernet0/1
S    192.168.50.0/24 [1/0] via 172.16.5.6
S*   0.0.0.0/0 [1/0] via 192.168.10.254
""",
        "expected_fault": "Static route 192.168.50.0/24 uses next-hop 172.16.5.6, which does not respond (blackhole)",
        "osi_layer": "Layer 3",
        "concept": "wrong next hop",
        "severity": "MEDIUM",
        "expected_command": "ping 172.16.5.6",
        "expected_fix": "ip route 192.168.50.0 255.255.255.0 172.16.5.254",
        "difficulty": "medium",
    },
        {
        "case_id": "NETSAGE-022",
        "category": "ACL",
        "title": "ACL deny rule blocking inter-VLAN traffic",
        "symptom": "Hosts in 192.168.10.0/24 cannot reach servers in 192.168.20.0/24. ICMP and TCP are blocked.",
        "topology": "ACL 100 applied to the inter-VLAN routed interface denies the 10->20 traffic before the permit rule.",
        "show_output": """show access-lists
Extended IP access list 100
    10 deny   ip 192.168.10.0 0.0.0.255 192.168.20.0 0.0.0.255
    20 permit ip any any
""",
        "expected_fault": "ACL 100 sequence 10 denies ip 192.168.10.0/24 -> 192.168.20.0/24 before the permit",
        "osi_layer": "Layer 3",
        "concept": "acl deny rule",
        "severity": "HIGH",
        "expected_command": "show access-lists",
        "expected_fix": "Reorder or remove the deny rule so 10->20 traffic is permitted",
        "difficulty": "easy",
    },
    {
        "case_id": "NETSAGE-023",
        "category": "ACL",
        "title": "ACL applied to the wrong interface",
        "symptom": "Inbound traffic toward servers is filtered unexpectedly; the ACL is bound to the host-facing port instead of the server-facing port.",
        "topology": "ACL 110 should be on Gi0/2 (servers) but is applied to Gi0/1 (hosts).",
        "show_output": """show access-lists
Extended IP access list 110
    10 permit tcp 192.168.10.0 0.0.0.255 any eq 80
    20 deny   ip any any

show ip interface
GigabitEthernet0/1
    Inbound access list: 110
    Outbound access list: not set
GigabitEthernet0/2
    Inbound access list: not set
    Outbound access list: not set
""",
        "expected_fault": "ACL 110 is applied inbound on Gi0/1 instead of the server-facing Gi0/2",
        "osi_layer": "Layer 3",
        "concept": "acl wrong interface",
        "severity": "MEDIUM",
        "expected_command": "show ip interface",
        "expected_fix": "Move the ACL: no ip access-group 110 in on Gi0/1; ip access-group 110 in on Gi0/2",
        "difficulty": "medium",
    },
    {
        "case_id": "NETSAGE-024",
        "category": "ACL",
        "title": "ACL applied in the wrong direction",
        "symptom": "Return traffic is being dropped; the ACL direction (in/out) is inverted on the edge interface.",
        "topology": "ACL 120 should be inbound to filter inbound connections but is applied outbound on Gi0/1.",
        "show_output": """show access-lists
Extended IP access list 120
    10 permit tcp 192.168.10.0 0.0.0.255 any established
    20 deny   tcp 192.168.10.0 0.0.0.255 any

show ip interface
GigabitEthernet0/1
    Inbound access list: not set
    Outbound access list: 120
""",
        "expected_fault": "ACL 120 is applied outbound on Gi0/1; filtering should be inbound",
        "osi_layer": "Layer 3",
        "concept": "acl direction",
        "severity": "MEDIUM",
        "expected_command": "show ip interface",
        "expected_fix": "Remove outbound and apply inbound: no ip access-group 120 out; ip access-group 120 in",
        "difficulty": "medium",
    },
    {
        "case_id": "NETSAGE-025",
        "category": "ACL",
        "title": "ACL implicit/explicit deny blocks a new application",
        "symptom": "After an ACL change, a newly-deployed application on port 8443 stops working for some users.",
        "topology": "ACL 130 permits only SSH and HTTP then denies all other traffic; the new app uses port 8443.",
        "show_output": """show access-lists
Extended IP access list 130
    10 permit tcp 192.168.10.0 0.0.0.255 any eq 22
    20 permit tcp 192.168.10.0 0.0.0.255 any eq 80
    30 deny   ip any any

show ip interface
GigabitEthernet0/1
    Inbound access list: 130
""",
        "expected_fault": "ACL 130 denies all traffic except SSH and HTTP, blocking the new application on port 8443",
        "osi_layer": "Layer 3",
        "concept": "implicit deny",
        "severity": "HIGH",
        "expected_command": "show access-lists",
        "expected_fix": "Permit the new application: permit tcp 192.168.10.0 0.0.0.255 any eq 8443",
        "difficulty": "hard",
    },
        {
        "case_id": "NETSAGE-026",
        "category": "NAT",
        "title": "NAT not configured on the edge router",
        "symptom": "Internal hosts (192.168.0.0/16) cannot reach the internet; no NAT translations are occurring.",
        "topology": "The edge router has no NAT configuration; internal addresses are sent untranslated.",
        "show_output": """show ip nat statistics
Total translations: 0
Active inside mappings: 0
Outside mappings: 0

show ip nat translations
Pro  Inside global      Inside local       Outside local      Outside global

show running-config | section ip nat

""",
        "expected_fault": "No NAT configuration exists; translations count is 0 and no inside/outside interfaces are defined",
        "osi_layer": "Layer 3",
        "concept": "nat missing",
        "severity": "HIGH",
        "expected_command": "show ip nat statistics",
        "expected_fix": "Configure NAT: mark inside/outside interfaces and ip nat inside source list 1 interface ... overload",
        "difficulty": "easy",
    },
    {
        "case_id": "NETSAGE-027",
        "category": "NAT",
        "title": "NAT inside/outside interface roles swapped",
        "symptom": "NAT translations are failing; the inside and outside interface designations appear reversed.",
        "topology": "Gi0/0 (10.0.0.1, internal) is marked outside; Gi0/1 (203.0.113.1, external) is marked inside.",
        "show_output": """show running-config | section interface
interface GigabitEthernet0/0
 ip address 10.0.0.1 255.255.255.0
 ip nat outside
interface GigabitEthernet0/1
 ip address 203.0.113.1 255.255.255.0
 ip nat inside

ip nat inside source list NAT-ACL interface GigabitEthernet0/1 overload
""",
        "expected_fault": "Gi0/0 (10.0.0.1, private) is marked ip nat outside and Gi0/1 (203.0.113.1, public) is marked ip nat inside; roles are swapped",
        "osi_layer": "Layer 3",
        "concept": "nat inside outside",
        "severity": "HIGH",
        "expected_command": "show running-config interface",
        "expected_fix": "Swap the roles: Gi0/0 ip nat inside, Gi0/1 ip nat outside",
        "difficulty": "medium",
    },
    {
        "case_id": "NETSAGE-028",
        "category": "NAT",
        "title": "NAT ACL matches only a subset of the inside network",
        "symptom": "Only some internal hosts are translated and can reach the internet; the rest are not translated.",
        "topology": "The inside network is 192.168.0.0/16 but the NAT ACL only permits 192.168.10.0/24.",
        "show_output": """show running-config | section interface
interface GigabitEthernet0/1
 ip address 192.168.0.1 255.255.0.0
 ip nat inside
interface GigabitEthernet0/0
 ip address 203.0.113.1 255.255.255.0
 ip nat outside

ip nat inside source list NAT-ACL interface GigabitEthernet0/0 overload

show access-lists
Extended IP access list NAT-ACL
    10 permit ip 192.168.10.0 0.0.0.255 any
    20 deny   ip any any

show ip nat statistics
Total translations: 1
show ip nat translations
Pro  Inside global      Inside local       Outside local      Outside global
     203.0.113.1:1024   192.168.10.5:1024  0.0.0.0:0          0.0.0.0:0
""",
        "expected_fault": "NAT ACL permits only 192.168.10.0/24 while the inside interface is 192.168.0.0/16; 192.168.20.0/24 and beyond are not translated",
        "osi_layer": "Layer 3",
        "concept": "nat acl mismatch",
        "severity": "MEDIUM",
        "expected_command": "show access-lists NAT-ACL",
        "expected_fix": "Broaden the NAT ACL: permit ip 192.168.0.0 0.0.255.255 any",
        "difficulty": "hard",
    },
        {
        "case_id": "NETSAGE-029",
        "category": "Wireless",
        "title": "Guest wireless clients can reach each other",
        "symptom": "Guest wireless clients can communicate with each other and can ping internal hosts; client isolation is not enforced on the guest SSID.",
        "topology": "A guest SSID (GUEST-WiFi) maps to VLAN 999; private-vlan / client isolation is not configured.",
        "show_output": """show wireless client summary
Number of Clients: 4
MAC Address        Vlan       SSID        State
0011.2233.4455     999        GUEST-WiFi  Associated
0022.3344.5566     999        GUEST-WiFi  Associated

show running-config | section guest
dot11 ssid GUEST-WiFi
   vlan 999
   guest-mode
   authentication open
""",
        "expected_fault": "Guest SSID GUEST-WiFi has no client isolation / private-vlan configured; clients in VLAN 999 can intercommunicate",
        "osi_layer": "Layer 2",
        "concept": "wireless client isolation",
        "severity": "HIGH",
        "expected_command": "show wireless client summary",
        "expected_fix": "Enable client isolation or a private-vlan host on the guest SSID and switch ports",
        "difficulty": "medium",
    },
    {
        "case_id": "NETSAGE-030",
        "category": "Wireless",
        "title": "Corporate SSID mapped to the wrong VLAN",
        "symptom": "Wireless clients connecting to the CORP SSID receive an IP in the guest subnet and cannot reach corporate resources.",
        "topology": "The CORP SSID (CORP-WiFi) is mapped to VLAN 999 (guest) instead of VLAN 10 (corporate).",
        "show_output": """show dot11 ssid
SSID         Vlan     Status
CORP-WiFi    999      Active
GUEST-WiFi   999      Active

show running-config | section ssid
dot11 ssid CORP-WiFi
   vlan 999
   authentication open

show ip dhcp snooping binding
Mac Address          IP address        Lease(sec)  Type           Vlan  Interface
0011.2233.4400       192.168.99.50     86400       dhcp-snooping  999   Fa0/8
""",
        "expected_fault": "CORP-WiFi SSID maps to VLAN 999 (guest) instead of VLAN 10 (corporate); clients get a guest IP",
        "osi_layer": "Layer 2",
        "concept": "wireless vlan mapping",
        "severity": "HIGH",
        "expected_command": "show dot11 ssid",
        "expected_fix": "Map CORP-WiFi to the correct corporate VLAN: vlan 10 under the ssid",
        "difficulty": "hard",
    },
]

# 5 historical human corrections demonstrating responsible-AI oversight.
RESPONSIBLE_LOG = [
    {
        "case_id": "NETSAGE-003",
        "ai_root_cause": "Native VLAN mismatch on the trunk Gi0/1",
        "human_decision": "EDIT",
        "corrected_root_cause": "Trunk Gi0/1 permits only VLANs 10,20; VLAN 30 is missing from the allowed list",
        "reason_for_correction": "The output shows VLAN 30 exists in 'show vlan brief' but is absent from the trunk allowed list; the AI focused on the native VLAN instead.",
        "reviewer_note": "Reviewed 'show interfaces trunk' and 'show vlan brief'; corrected to the actual allowed-vlan gap.",
        "timestamp": "2026-07-15T09:12:03Z",
    },
    {
        "case_id": "NETSAGE-007",
        "ai_root_cause": "Incorrect default gateway IP configured on the host",
        "human_decision": "EDIT",
        "corrected_root_cause": "Default gateway 192.168.10.1 is outside the host subnet 192.168.20.0/24",
        "reason_for_correction": "The AI assumed a wrong IP value, but the real problem is the gateway is in the wrong subnet, not the wrong address within a subnet.",
        "reviewer_note": "Verified with ipaddress math: 192.168.10.1 not in 192.168.20.0/24.",
        "timestamp": "2026-07-16T11:04:22Z",
    },
    {
        "case_id": "NETSAGE-015",
        "ai_root_cause": "Primary DNS server 192.168.10.99 returned stale records",
        "human_decision": "REJECT",
        "corrected_root_cause": "DNS server 192.168.10.99 is absent from the ARP table, so it is unreachable (not returning stale data)",
        "reason_for_correction": "Ping/resolution fails at Layer 2; the device is offline, so 'stale records' is the wrong framing.",
        "reviewer_note": "Marked REJECT because diagnosis mischaracterized reachability vs content.",
        "timestamp": "2026-07-17T15:30:10Z",
    },
    {
        "case_id": "NETSAGE-021",
        "ai_root_cause": "Missing static route for 192.168.50.0/24",
        "human_decision": "EDIT",
        "corrected_root_cause": "Static route exists but next-hop 172.16.5.6 is a blackhole (host does not respond)",
        "reason_for_correction": "show ip route clearly contains the 192.168.50.0/24 route; the problem is the next-hop, not a missing route.",
        "reviewer_note": "Corrected root cause and next command to 'ping 172.16.5.6'.",
        "timestamp": "2026-07-18T08:45:55Z",
    },
    {
        "case_id": "NETSAGE-028",
        "ai_root_cause": "NAT inside/outside interface roles are swapped",
        "human_decision": "EDIT",
        "corrected_root_cause": "NAT ACL only matches 192.168.10.0/24 while the inside interface is 192.168.0.0/16",
        "reason_for_correction": "Inside/outside roles are correct; the interface markings are fine. The ACL scope is the real issue.",
        "reviewer_note": "Confirmed with 'show access-lists' and interface 192.168.0.1/16.",
        "timestamp": "2026-07-19T13:20:40Z",
    },
]


def write_cases_csv():
    path = os.path.join(DATA_DIR, "cases.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for c in CASES:
            writer.writerow({k: c[k] for k in CSV_FIELDS})
    return path, len(CASES)


def write_responsible_log():
    fields = ["case_id", "ai_root_cause", "human_decision",
              "corrected_root_cause", "reason_for_correction",
              "reviewer_note", "timestamp"]
    path = os.path.join(DATA_DIR, "responsible_ai_log.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in RESPONSIBLE_LOG:
            writer.writerow(row)
    return path, len(RESPONSIBLE_LOG)


def write_sample_cases():
    demo_ids = ["NETSAGE-001", "NETSAGE-020", "NETSAGE-030"]
    difficulty = {c["case_id"]: c["difficulty"] for c in CASES}
    demos = [c for c in CASES if c["case_id"] in demo_ids]
    payload = {
        "demo_cases": [
            {
                "case_id": c["case_id"],
                "category": c["category"],
                "title": c["title"],
                "symptom": c["symptom"],
                "topology": c["topology"],
                "show_output": c["show_output"],
                "expected_fault": c["expected_fault"],
                "expected_command": c["expected_command"],
                "expected_fix": c["expected_fix"],
                "difficulty": c["difficulty"],
            }
            for c in demos
        ],
        "difficulty_distribution": difficulty,
        "category_counts": {
            cat: sum(1 for c in CASES if c["category"] == cat)
            for cat in ["VLAN", "Default Gateway", "DHCP", "DNS", "Routing",
                        "ACL", "NAT", "Wireless"]
        },
    }
    path = os.path.join(DATA_DIR, "sample_cases.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return path, len(demos)


if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    cp, n = write_cases_csv()
    rp, m = write_responsible_log()
    sp, d = write_sample_cases()
    print(f"[ok] {cp}  ({n} cases)")
    print(f"[ok] {rp}  ({m} corrected cases)")
    print(f"[ok] {sp}  ({d} demo cases)")

