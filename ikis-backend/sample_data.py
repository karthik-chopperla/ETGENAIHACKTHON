"""
Generates sample industrial documents for testing IKIS ingestion, RAG queries,
maintenance recommendations, and compliance gap detection.

Run: python sample_data.py
Creates files under ./sample_docs/
"""

import os

SAMPLE_DOCS = {
    "CP2000_Equipment_Manual.txt": """
EQUIPMENT MANUAL: Centrifugal Pump CP-2000 (PUMP-001)
Manufacturer: FlowTech Industries | Installed: 2019-03-14

1. OVERVIEW
PUMP-001 is a centrifugal pump rated for 450 GPM at 120 PSI, used in the
cooling water circuit of Unit 3. Rated operating temperature: 40-85 C.

2. ROUTINE MAINTENANCE SCHEDULE
- Weekly: Inspect bearing housing for vibration and temperature anomalies.
- Monthly: Check mechanical seal for leakage, verify lubrication levels.
- Quarterly: Full vibration analysis per OISD-STD-137.
- Annually: Replace bearings and inspect impeller for cavitation damage.

3. SAFETY REQUIREMENTS
Maintenance personnel must follow Factory Act Sec 13 lockout-tagout
procedures before opening any pressurized casing. PPE required: safety
glasses, gloves, hearing protection (pump room exceeds 85 dB).

4. KNOWN FAILURE MODES
- Bearing wear from insufficient lubrication (most common, ~60% of failures)
- Seal degradation from cavitation
- Vibration-induced coupling misalignment

Approved by: R. Menon, Chief Engineer. Reviewed: 2025-11-02.
""",

    "PUMP001_Maintenance_Log.txt": """
MAINTENANCE WORK ORDER LOG - PUMP-001
Facility: Unit 3 Cooling Water Circuit

WO-4471 | 2026-04-02 | Technician: S. Iyer
Vibration reading: 4.2 mm/s (baseline 2.8 mm/s). Flagged for follow-up.
Action: Lubrication top-up performed. No leak observed.

WO-4498 | 2026-05-10 | Technician: S. Iyer
Vibration reading: 5.6 mm/s. Seal temperature 4C above baseline.
Action: Recommended bearing inspection within 30 days. Deferred due to
production schedule.

WO-4552 | 2026-06-18 | Technician: A. Kapoor
Vibration reading: 6.9 mm/s, rising trend confirmed over 3 consecutive
readings (18% increase over 10 operating cycles). Seal temperature still
elevated. Escalated to maintenance supervisor.

WO-4571 | 2026-06-29 | Technician: A. Kapoor
Unplanned stoppage - suspected bearing wear. 6 hours downtime.
Root cause: delayed bearing replacement from WO-4498 recommendation.
Corrective action: Replace bearing and seal assembly. Update PM schedule
to weekly vibration checks for next 90 days.
""",

    "SafetyProcedure_ShutdownEmergency.txt": """
SAFETY PROCEDURE SP-014: Emergency Shutdown - Rotating Equipment
Applies to: PUMP-001, COMPRESSOR-02, TURBINE-04

1. PURPOSE
Defines the emergency shutdown sequence for rotating equipment following
a vibration alarm, seal failure, or unplanned high-temperature event.

2. PROCEDURE
Step 1: Operator on duty triggers local E-stop, notifies shift supervisor.
Step 2: Isolate equipment per Factory Act Sec 37 lockout-tagout protocol.
Step 3: Verify zero energy state before any inspection begins.
Step 4: Log incident in the shift roster and notify the plant safety lead.
Step 5: No restart until maintenance crew confirms seal and lubrication
health per SP-014 checklist.

3. TRAINING REQUIREMENT
All operators must complete annual refresher training on this procedure.
Training acknowledgment must be logged in the LMS within 30 days of the
refresh cycle. Non-compliance must be reported to the compliance officer.

4. REGULATORY REFERENCE
OISD-119 (Safety in Petroleum Industry), Factory Act Sec 37, ISO 45001.

Owner: Plant Safety Lead. Last reviewed: 2026-01-15.
""",

    "InspectionReport_Q2_2026.txt": """
QUARTERLY INSPECTION REPORT - Q2 2026
Inspector: M. Rao, Certified Pressure Vessel Inspector
Scope: PUMP-001, BOILER-03, associated pressure vessels

FINDINGS - PUMP-001
Vibration and seal temperature trend consistent with maintenance log
WO-4552/WO-4571. Bearing replaced 2026-06-29; post-replacement vibration
reading 2.6 mm/s, within baseline.

FINDINGS - BOILER-03
Pressure vessel inspection completed. Certification reference field is
missing from the inspection record submitted for audit; evidence packet
otherwise complete. This is a gap against OISD-119 traceability
requirements pending certification sheet attachment.

FINDINGS - GENERAL
Training matrix shows 2 operators overdue for SP-014 annual refresher
(due 2026-05-01, not yet completed as of report date).

Recommendations:
1. Attach signed certification sheet for BOILER-03 inspection record.
2. Schedule SP-014 refresher for overdue operators immediately.
3. Continue weekly vibration monitoring on PUMP-001 through Q3 2026.

Report filed: 2026-06-30.
""",

    "IncidentReport_COMPRESSOR02_NearMiss.txt": """
NEAR-MISS INCIDENT REPORT - COMPRESSOR-02
Reported by: T. Sharma, Shift Supervisor | Date: 2026-05-22

DESCRIPTION
Seal temperature alarm triggered during Unit 2 startup. Operator performed
manual shutdown before seal failure occurred. No injury, no release.

BACKGROUND
Seal replacement was recommended in inspection IR-2291 (2026-04-02) with
target date 2026-04-20. Work was deferred twice by the maintenance planning
committee to avoid interrupting the Unit 2 production run. Deferral notes
cite "no available shutdown window before Q2 targets."

CORRECTIVE ACTION
Seal replaced 2026-05-23. Recommend maintenance planning treat inspector
target dates as firm unless a documented safety review approves deferral.

Filed under: Near-Miss Register, Unit 2.
""",

    "IncidentReport_TURBINE04_Trip.txt": """
UNPLANNED TRIP REPORT - TURBINE-04
Reported by: A. Verma, Maintenance Engineer | Date: 2026-06-10

DESCRIPTION
Turbine tripped on high bearing temperature. 5-hour production loss.

ROOT CAUSE
Lubrication system inspection (WO-3390, 2026-03-15) recommended bearing
lubricant replacement within 30 days. Work order was deferred three times
over 11 weeks; maintenance planning log cites "production schedule
priority" each time. Lubricant degraded below spec, causing elevated
bearing friction and the eventual trip.

CORRECTIVE ACTION
Lubricant replaced, bearing inspected for damage (none found). Planning
team advised to escalate any inspection-recommended work deferred more
than twice to the plant safety lead for review.

Filed under: Trip & Incident Log, Unit 4.
""",

    "AuditFinding_Q1Q2_2026_MaintenanceDeferrals.txt": """
INTERNAL AUDIT FINDING - MAINTENANCE DEFERRAL PATTERN
Auditor: P. Krishnan, Internal Quality & Safety Audit | Date: 2026-06-28
Scope: Q1-Q2 2026, all units

FINDING
Reviewed corrective-action tracking across Units 2, 3, and 4. In 3 of the
last 4 documented near-miss or trip events, the triggering equipment had a
prior inspection or work-order recommendation that was deferred at least
once for "production schedule" reasons, with no documented safety review
of the deferral decision.

Affected equipment: PUMP-001 (WO-4498 deferred, led to WO-4571 stoppage),
COMPRESSOR-02 (seal replacement deferred twice, near-miss), TURBINE-04
(lubricant replacement deferred three times, unplanned trip).

RECOMMENDATION
Maintenance planning process lacks a mandatory safety review gate before
an inspector-recommended action can be deferred more than once. Recommend
this become a standing agenda item for the monthly safety committee until
a formal deferral-review procedure is adopted.

Report filed: 2026-06-28.
""",
}


def main():
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_docs")
    os.makedirs(out_dir, exist_ok=True)

    for filename, content in SAMPLE_DOCS.items():
        path = os.path.join(out_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content.strip() + "\n")
        print(f"Wrote {path}")

    print(f"\nDone. {len(SAMPLE_DOCS)} sample documents in {out_dir}")
    print("Upload one with:")
    print('  curl -X POST "http://localhost:8000/api/documents/upload" '
          '-F "file=@ikis-backend/sample_docs/CP2000_Equipment_Manual.txt" '
          '-F "doc_type=equipment_manual"')


if __name__ == "__main__":
    main()
