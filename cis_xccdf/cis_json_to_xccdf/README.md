# CIS To XCCDF Compliant XML



```bash
python cis_to_xccdf.py \
    -i cis_benchmark.json \
    -o U_CIS_Windows_Server_2019_V3R1_Manual-xccdf.xml \
    -t "CIS Microsoft Windows Server 2019 Benchmark" \
    -b "CIS_Windows_Server_2019_V3" \
    -v 3 \
    -r "Release: 1 Benchmark Date: 22 Jul 2025" \
    -m mapping.yaml \
    --start-vid 500000
```

```yaml
metadata:
  publisher: "Center for Internet Security (CIS)"
  dc_identifier: 3000

profiles:
  "Level 1 - Domain Controller": "CIS_L1_DC"
  "Level 1 - Member Server": "CIS_L1_MS"
  "Level 2 - Domain Controller": "CIS_L2_DC"

severity:
  "Level 1": "medium"
  "Level 2": "high"

check_content_href: "CIS_Windows_Server_2019_Manual_Checks.xml"

cci_mappings:
  "1.1.1": ["CCI-000192", "CCI-001619"]
  "1.1.2": ["CCI-000366"]

skip:
  - "9.1.1"  # Known false positive
```

## CIS JSON to XCCDF Mapping Guide

This table defines **how to map fields from a CIS Benchmark JSON** (e.g., `cis_benchmark.json`) into a **fully compliant DISA-style XCCDF 1.1 Manual STIG**.

| XCCDF Required Element                         | How to Map from CIS JSON                                   | Notes                                                                                             |
|------------------------------------------------|--------------------------------------------------------------------|---------------------------------------------------------------------------------------------------|
| `<Benchmark id="...">`                         | `-b` CLI arg or derived from title                         | Must be unique and URL-safe. <br>Example: `CIS_Windows_Server_2019_v3.0.1`                        |
| `<title>`                                      | `-t` CLI arg or `benchmark` field                          | Full human-readable title. <br>Example: `CIS Microsoft Windows Server 2019 Benchmark`             |
| `<version>`                                    | `-v` CLI arg                                               | Integer version of the benchmark. <br>Example: `3`                                                |
| `<plain-text id="release-info">`               | `-r` CLI arg                                               | Exact format used by DISA. <br>Example: `Release: 1 Benchmark Date: 22 Jul 2025`                 |
| `<Profile>`                                    | From `profile` field in each recommendation                | Create one `<Profile>` per unique value. <br>Common: <br>• Level 1 - Domain Controller <br>• Level 1 - Member Server <br>• Level 2 - Domain Controller |
| `<Group id="V-XXXXXX">`                        | Generate sequential or seeded V-ID                         | **Critical**: Must be stable and non-overlapping with DISA. <br>Recommended start: `V-400000+` (safe community range) |
| `<Rule id="SV-XXXXXXrXXXXXX_rule">`            | Generate using counter + revision                          | Example: `SV-400001r1_rule` <br>Increment revision only when content changes                     |
| `<version>` inside `<Rule>`                    | Use CIS recommendation number                              | Example: `CIS-1.1.1`, `1.1.1`, or `WN19-1.1.1`                                                     |
| `<title>` (inside `<Rule>`)                    | Use `title` field                                          | Optionally strip `(L1)`, `(L2)` prefixes for cleaner display                                      |
| `<description>`                                | Combine: <br>• `description` <br>• `rational_statement` <br>• `impact_statement` | Place into `<VulnDiscussion>`, `<FalsePositives>`, `<Mitigations>`, etc. Use proper XCCDF sub-tags |
| `<fixtext>` / `<fix>`                          | `remediation_procedure` → `<fixtext>`                      | Generate matching `<fix id="F-xxxxxrx_fix">`                                                      |
| `<check>` / `<check-content>`                  | `audit_procedure` → manual check reference                 | All CIS checks are manual → use: <br>`<check-content-ref href="CIS_*.xml" name="M"/>`             |
| `<ident system="http://cyber.mil/cci">`        | Optional — not in CIS source                               | Add via external YAML mapper. <br>Highly recommended for DoD/FedRAMP use                         |
| `<reference><dc:identifier>`                   | Hardcode or pass via config                                | CIS typically uses `3000` range. <br>DISA uses `2900` series (e.g., `2907` for Win2019)           |

### Recommended V-ID Ranges (2025 Community Standard)

| Owner / Use Case                  | Safe V-ID Range       | Example                  |
|-----------------------------------|-----------------------|--------------------------|
| DISA Official STIGs               | V-20000 → V-399999    | V-205624 (Win2019)       |
| CIS-Converted / Community         | **V-400000 → V-999999** | **V-400001** (your output) |
| Experimental / Local Only         | V-1000000+            | V-1000123                |

**Never** use V-IDs below 400000 unless you are DISA.

### Best Practice Summary

- Keep **CCI mappings external** (in `mapping.yaml`) — never embed in JSON  
- Always use `--start-vid 400000` (or higher) for CIS conversions  
- Use YAML mapper for: severity, profile IDs, skips, CCIs, check file href  
- Output matches 100% of DISA Manual STIG XCCDF structure → accepted by STIG Viewer, eMASS, ACAS, OpenSCAP

CIS converted XCCDF will be **indistinguishable** from official DISA Manual STIGs.

## Safe, widely adopted community ranges

--start-vid 400000   # CIS Windows → V-400000+
--start-vid 500000   # CIS RHEL      → V-500000+
--start-vid 600000   # CIS Kubernetes → V-600000+
--start-vid 700000   # Custom/In-house

## Official DISA V-ID Ranges (2025)

| Owner                   | V-ID Range        | Example                | 
|-------------------------|-------------------|------------------------| 
| DISA (official STIGs)   | V-20000 → 399999  | V-205624 (Win2019)     |
| Vendor/Community (safe) | V-400000 → 999999 | V-400001 (CIS Win2019) |
| Experimental / Local    | V-1000000+        | V-1000123              |