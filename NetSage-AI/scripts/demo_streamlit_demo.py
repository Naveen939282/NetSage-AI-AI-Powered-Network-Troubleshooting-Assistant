import json
from utils.csv_loader import case_by_id
from ai.provider import MockProvider
from checker import vlan_rules, ip_rules, gateway_rules, routing_rules, acl_rules, dhcp_rules, interface_rules

case_ids = ["NETSAGE-001", "NETSAGE-017", "NETSAGE-029"]
results = {}
for cid in case_ids:
    c = case_by_id(cid)
    if not c:
        results[cid] = {"error": "not found"}
        continue
    # Run rule checkers
    findings = []
    for runner in (vlan_rules.run_vlan_rules, ip_rules.run_ip_rules,
                   gateway_rules.run_gateway_rules, routing_rules.run_routing_rules,
                   acl_rules.run_acl_rules, dhcp_rules.run_dhcp_rules,
                   interface_rules.run_interface_rules):
        try:
            r = runner(c)
            if r and r.get("findings"):
                findings.extend(r.get("findings"))
        except Exception as e:
            findings.append({"error": str(e), "runner": getattr(runner, '__name__', str(runner))})
    # Mock AI
    p = MockProvider()
    diag = p.generate_diagnosis(c, rule_findings=findings)
    results[cid] = {
        "case_id": cid,
        "title": c.title,
        "symptom": c.symptom,
        "topology": c.topology,
        "show_output": c.show_output[:1000],
        "rule_findings": findings,
        "ai": diag.model_dump(),
    }
print(json.dumps(results, indent=2))
