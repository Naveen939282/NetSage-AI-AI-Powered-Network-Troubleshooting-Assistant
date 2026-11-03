Use the system prompt in `system_prompt.md`.

You will receive these inputs:
- `symptom`: free-text description from the user
- `topology`: architecture and port mappings
- `show_output`: raw Cisco show command outputs

Required JSON output schema (validate with Pydantic):

```
{
"root_cause": "",
"osi_layer": "",
"confidence": 0.0,
"severity": "",
"evidence": [],
"missing_evidence": [],
"next_command": "",
"fix_steps": [],
"reasoning_summary": "",
"rule_checker_findings": [],
"requires_human_review": true
}
```

Rules:
- Use only supplied evidence.
- Cite exact lines or snippets from `show_output` in `evidence`.
- If uncertain, set `confidence` appropriately and list `missing_evidence`.
- Always set `requires_human_review` to true.

Worked example 1 (VLAN):
- Input: `show vlan brief` lists VLANs 10 and 20; `show interfaces switchport` shows Gi0/2 access VLAN 10; symptom: host in VLAN 20 cannot reach servers.
- Output: `root_cause`: "access VLAN misassignment on Gi0/2"; `evidence`: include the two show outputs; `next_command`: "show interfaces Gi0/2 status"; `fix_steps`: ["switchport access vlan 20"].

Worked example 2 (Gateway outside subnet):
- Input: host 192.168.20.15 gateway 192.168.10.1; `show ip interface brief` shows Vlan20 192.168.20.15; `show ip route` shows default via 192.168.10.1.
- Output: `root_cause`: "default gateway outside host subnet"; `osi_layer`: "Layer 3"; `missing_evidence`: ["gateway device reachable? ping results"]

Worked example 3 (ACL):
- Input: `show access-lists` contains deny 192.168.10.0/24 -> 192.168.20.0/24 then permit any any; symptom: 10->20 blocked.
- Output: `root_cause`: "ACL denies inter-VLAN traffic"; `evidence`: capture ACL lines; `next_command`: "show ip interface"; `fix_steps`: ["reorder/remove deny sequence"]; `requires_human_review`: true.
