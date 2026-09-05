"""
ClaimLens AI — Synthetic Dataset Generator
Generates 80 motor insurance claims with documents and ground truth.
Deterministic: uses SEED=2026 for reproducibility.
"""
import csv
import json
import os
import random
from datetime import datetime, timedelta
from pathlib import Path

SEED = 2026
random.seed(SEED)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CLAIMS_DIR = DATA_DIR / "claims"

# ── Fictional Indian names ──
FIRST_NAMES = [
    "Aarav", "Neha", "Rohan", "Isha", "Kabir", "Priya", "Arjun", "Ananya",
    "Vikram", "Meera", "Siddharth", "Kavya", "Aditya", "Riya", "Dhruv",
    "Sneha", "Manish", "Pooja", "Raj", "Tanvi", "Amit", "Divya", "Nikhil",
    "Shreya", "Karan", "Simran", "Harsh", "Nisha", "Varun", "Sakshi",
    "Rahul", "Anjali", "Deepak", "Megha", "Akash", "Swati", "Gaurav",
    "Pallavi", "Suresh", "Komal", "Pranav", "Bhavna", "Tushar", "Renuka",
    "Yash", "Namrata", "Omkar", "Jyoti", "Shubham", "Rashmi",
    "Vivek", "Sunita", "Manoj", "Tara", "Ajay", "Lata", "Kunal", "Geeta",
    "Sameer", "Uma", "Nilesh", "Chitra", "Pankaj", "Rani", "Girish",
    "Padma", "Hemant", "Seema", "Dinesh", "Revathi", "Sandip", "Mala",
    "Vijay", "Hema", "Ashok", "Rekha", "Ramesh", "Kalpana", "Sunil", "Veena"
]
LAST_NAMES = [
    "Mehta", "Patil", "Kulkarni", "Deshmukh", "Shah", "Joshi", "Sharma",
    "Gupta", "Reddy", "Nair", "Patel", "Iyer", "Singh", "Verma", "Rao",
    "Das", "Mishra", "Chatterjee", "Pillai", "Kumar", "Chopra", "Bose",
    "Kapoor", "Deshpande", "Ghosh", "Banerjee", "Malhotra", "Tiwari",
    "Agarwal", "Sinha", "Thakur", "Shukla", "Pandey", "Saxena", "Bhatt",
    "Menon", "Hegde", "Kamath", "Kale", "More", "Pawar", "Jadhav",
    "Chavan", "Gaikwad", "Shinde", "Wagh", "Khare", "Sathe", "Gore", "Gokhale"
]

CITIES = [
    "Mumbai", "Pune", "Nashik", "Nagpur", "Aurangabad", "Thane", "Kolhapur",
    "Solapur", "Amravati", "Sangli", "Satara", "Ratnagiri", "Latur",
    "Jalgaon", "Dhule", "Ahmednagar", "Nanded", "Akola", "Chandrapur"
]
LOCATIONS_DETAIL = [
    "MG Road near signal", "Highway NH-48 km marker 120", "Station Road intersection",
    "Ring Road near petrol pump", "Market area main chowk", "Service road near mall",
    "Bypass road bridge section", "Old city area narrow lane", "Industrial zone gate 3",
    "College Road T-junction", "Bus stand approach road", "Temple Road curve",
    "Cantonment area main gate road", "Lake Road sharp bend", "IT Park access road",
    "Residential colony internal road", "Flyover entry ramp", "National Highway toll plaza",
    "State Highway near village crossing", "Municipal garden road"
]

RTO_CODES = ["MH01", "MH02", "MH03", "MH04", "MH05", "MH12", "MH14", "MH15",
             "MH20", "MH31", "MH43", "MH46", "MH49"]
LETTERS = "ABCDEFGHJKLMNPQRSTUVWXYZ"

CAR_MAKES = ["Maruti Swift", "Hyundai i20", "Tata Nexon", "Honda City", "Kia Seltos",
             "Mahindra XUV300", "Toyota Innova", "Skoda Slavia", "VW Virtus", "MG Hector"]
BIKE_MAKES = ["Honda Activa", "TVS Jupiter", "Bajaj Pulsar", "Royal Enfield Classic",
              "Hero Splendor", "Yamaha FZ", "Suzuki Access", "TVS Apache", "KTM Duke 200",
              "Honda CB Shine"]

DAMAGE_PARTS_CAR = ["Front bumper", "Rear bumper", "Headlight", "Tail light", "Bonnet",
                    "Boot lid", "Left fender", "Right fender", "Windshield", "Left door",
                    "Right door", "Side mirror", "Roof panel", "Quarter panel", "Radiator grille"]
DAMAGE_PARTS_BIKE = ["Front fairing", "Headlight assembly", "Handle bar", "Side panel",
                     "Fuel tank", "Exhaust pipe", "Footrest", "Front fork", "Rear view mirror",
                     "Seat cover", "Mudguard", "Brake lever", "Chain sprocket"]

DATE_FORMATS = [
    lambda d: d.strftime("%d %B %Y"),          # 10 August 2026
    lambda d: d.strftime("%d/%m/%Y"),           # 10/08/2026
    lambda d: d.strftime("%Y-%m-%d"),           # 2026-08-10
    lambda d: d.strftime("%d-%m-%Y"),           # 10-08-2026
    lambda d: d.strftime("%d %b %Y"),           # 10 Aug 2026
]

REG_LABELS = ["Registration Number", "Reg. No.", "Vehicle No.", "Registration", "Regn. No.",
              "Vehicle Registration", "Reg No"]
TIME_LABELS = ["Incident Time", "Time of Incident", "Time", "Approx. Time"]

def gen_reg():
    code = random.choice(RTO_CODES)
    letters = random.choice(LETTERS) + random.choice(LETTERS)
    num = random.randint(1000, 9999)
    return f"{code}{letters}{num}"

def gen_policy_number(idx):
    return f"POL-2026-{idx:03d}"

def gen_name(idx):
    return f"{FIRST_NAMES[idx % len(FIRST_NAMES)]} {LAST_NAMES[idx % len(LAST_NAMES)]}"

def gen_policy_dates():
    start = datetime(2026, 1, 1) + timedelta(days=random.randint(0, 120))
    end = start + timedelta(days=365)
    return start, end

def gen_incident_date(policy_start, policy_end, within_policy=True):
    if within_policy:
        max_day = min((policy_end - policy_start).days - 30, 200)
        delta = random.randint(30, max(31, max_day))
        return policy_start + timedelta(days=delta)
    else:
        return policy_end + timedelta(days=random.randint(5, 60))

def gen_claim_date(incident_date, late=False):
    if late:
        return incident_date + timedelta(days=random.randint(10, 25))
    return incident_date + timedelta(days=random.randint(1, 5))

def gen_time():
    h = random.randint(6, 23)
    m = random.choice([0, 15, 30, 45])
    return f"{h:02d}:{m:02d}"

def fmt_date(dt, idx=None):
    if idx is None:
        idx = random.randint(0, len(DATE_FORMATS) - 1)
    return DATE_FORMATS[idx](dt)

def fmt_currency(amount):
    s = str(amount)
    result = ""
    for i, c in enumerate(reversed(s)):
        if i == 3:
            result = "," + result
        elif i > 3 and (i - 3) % 2 == 0:
            result = "," + result
        result = c + result if i == 0 else c + result.lstrip(c) if False else c + result
    return f"Rs. {amount:,}"

def pick_damage(vehicle_type, n=None):
    parts = DAMAGE_PARTS_CAR if vehicle_type == "Car" else DAMAGE_PARTS_BIKE
    if n is None:
        n = random.randint(2, 5)
    return random.sample(parts, min(n, len(parts)))

def gen_repair_items(damage_parts):
    items = []
    for p in damage_parts:
        cost = random.choice([5000, 8000, 10000, 12000, 15000, 18000, 20000, 25000, 30000, 35000])
        items.append((p, cost))
    return items

# ── Document generators ──

def gen_claim_form(claim, date_fmt_idx=None):
    reg_label = random.choice(REG_LABELS)
    d_fmt = date_fmt_idx if date_fmt_idx is not None else random.randint(0, len(DATE_FORMATS)-1)
    lines = [
        "CLAIM FORM",
        "=" * 40,
        "",
        f"Claim ID: {claim['claim_id']}",
        f"Policy Number: {claim['policy_number']}",
        "",
        "Policyholder Details:",
        f"Name: {claim['customer_name']}",
        "",
        "Vehicle Details:",
        f"Vehicle Type: {'Private Car' if claim['vehicle_type'] == 'Car' else 'Two-Wheeler'}",
        f"{reg_label}: {claim['vehicle_registration']}",
        "",
        "Incident Details:",
        f"Type of Incident: {claim['incident_type']}",
        f"Date of Incident: {fmt_date(claim['incident_date_dt'], d_fmt)}",
        f"{random.choice(TIME_LABELS)}: {claim['incident_time']}",
        f"Location: {claim['incident_location']}, {claim['incident_city']}",
        "",
        "Description:",
        claim['description'],
        "",
        f"Claim Date: {fmt_date(claim['claim_date_dt'], d_fmt)}",
        "",
        f"Declaration: I, {claim['customer_name']}, hereby declare that the information",
        "provided in this claim form is true and correct to the best of my knowledge.",
        "",
        f"Signature: {claim['customer_name']}",
        f"Date: {fmt_date(claim['claim_date_dt'], d_fmt)}",
    ]
    return "\n".join(lines)

def gen_incident_description(claim, date_fmt_idx=None):
    d_fmt = date_fmt_idx if date_fmt_idx is not None else random.randint(0, len(DATE_FORMATS)-1)
    if claim['incident_type'] == 'Accident':
        narrative = random.choice([
            f"On {fmt_date(claim['incident_date_dt'], d_fmt)}, at approximately {claim['incident_time']}, "
            f"I was driving my {claim['vehicle_type'].lower()} (registration {claim['vehicle_registration']}) "
            f"on {claim['incident_location']} in {claim['incident_city']}. Another vehicle suddenly "
            f"collided with my vehicle causing significant damage to the {', '.join(claim['damage_parts'][:2])}. "
            f"I immediately stopped and assessed the damage.",

            f"I, {claim['customer_name']}, report that on {fmt_date(claim['incident_date_dt'], d_fmt)} "
            f"around {claim['incident_time']}, while travelling near {claim['incident_location']}, "
            f"{claim['incident_city']}, my vehicle ({claim['vehicle_registration']}) was involved in "
            f"a collision. The {', '.join(claim['damage_parts'][:3])} were damaged. "
            f"There were no injuries.",

            f"Date of incident: {fmt_date(claim['incident_date_dt'], d_fmt)}\n"
            f"Time: {claim['incident_time']}\n"
            f"Location: {claim['incident_location']}, {claim['incident_city']}\n\n"
            f"My vehicle {claim['vehicle_registration']} was hit by another vehicle while I was "
            f"driving through the area. The impact caused damage to the {', '.join(claim['damage_parts'][:2])}. "
            f"I have obtained a repair estimate from an authorized service center.",
        ])
    else:  # Theft
        narrative = random.choice([
            f"On {fmt_date(claim['incident_date_dt'], d_fmt)}, I parked my {claim['vehicle_type'].lower()} "
            f"(registration {claim['vehicle_registration']}) near {claim['incident_location']} in "
            f"{claim['incident_city']} at around {claim['incident_time']}. When I returned after "
            f"approximately 2 hours, the vehicle was missing from the parking spot. I immediately "
            f"filed an FIR with the local police station.",

            f"I, {claim['customer_name']}, wish to report that my vehicle bearing registration "
            f"number {claim['vehicle_registration']} was stolen from {claim['incident_location']}, "
            f"{claim['incident_city']} on {fmt_date(claim['incident_date_dt'], d_fmt)}. "
            f"I had parked the vehicle at approximately {claim['incident_time']} and discovered "
            f"the theft when I returned. A police complaint has been lodged.",
        ])

    lines = [
        "INCIDENT DESCRIPTION",
        "=" * 40,
        "",
        f"Claim Reference: {claim['claim_id']}",
        f"Date: {fmt_date(claim['claim_date_dt'], d_fmt)}",
        "",
        narrative,
        "",
        f"Submitted by: {claim['customer_name']}",
    ]
    return "\n".join(lines)

def gen_repair_estimate(claim, date_fmt_idx=None):
    d_fmt = date_fmt_idx if date_fmt_idx is not None else random.randint(0, len(DATE_FORMATS)-1)
    reg_label = random.choice(REG_LABELS)
    items = claim['repair_items']
    total = sum(cost for _, cost in items)
    claim['repair_estimate_val'] = total

    lines = [
        "REPAIR ESTIMATE",
        "=" * 40,
        "",
        f"{reg_label}: {claim['vehicle_registration']}",
        f"Vehicle: {claim.get('vehicle_make', claim['vehicle_type'])}",
        f"Date of Assessment: {fmt_date(claim['incident_date_dt'] + timedelta(days=1), d_fmt)}",
        "",
        "Estimated Repair Cost:",
        "-" * 30,
    ]
    for part, cost in items:
        lines.append(f"  {part}: Rs. {cost:,}")
    lines.extend([
        "-" * 30,
        f"  Total Estimate: Rs. {total:,}",
        "",
        "Note: This is an estimate. Actual cost may vary upon disassembly.",
        "",
        "Authorized Workshop",
        f"Date: {fmt_date(claim['incident_date_dt'] + timedelta(days=1), d_fmt)}",
    ])
    return "\n".join(lines)

def gen_fir(claim, date_fmt_idx=None, override_date=None, override_reg=None, override_location=None):
    d_fmt = date_fmt_idx if date_fmt_idx is not None else random.randint(0, len(DATE_FORMATS)-1)
    incident_date = override_date if override_date else claim['incident_date_dt']
    reg = override_reg if override_reg else claim['vehicle_registration']
    location = override_location if override_location else f"{claim['incident_location']}, {claim['incident_city']}"

    fir_time = claim['incident_time']
    # Slight time variation for realism
    h, m = map(int, fir_time.split(':'))
    m2 = min(59, m + random.randint(0, 10))
    fir_time_str = f"{h:02d}:{m2:02d}"

    if claim['incident_type'] == 'Accident':
        desc = (f"Complainant reports a road accident involving vehicle bearing registration "
                f"number {reg}. The accident occurred at {location} on "
                f"{fmt_date(incident_date, d_fmt)} at approximately {fir_time_str}. "
                f"Damage reported to the vehicle.")
    else:
        desc = (f"Complainant reports theft of vehicle bearing registration number {reg}. "
                f"The vehicle was reportedly parked at {location} and was discovered "
                f"missing on {fmt_date(incident_date, d_fmt)} at approximately {fir_time_str}. "
                f"Investigation initiated.")

    lines = [
        "FIRST INFORMATION REPORT (FIR)",
        "=" * 40,
        "",
        f"FIR Number: FIR-{claim['claim_id'].replace('CLM', '')}-2026",
        f"Police Station: {claim['incident_city']} City Police Station",
        "",
        f"Complainant: {claim['customer_name']}",
        "",
        f"Vehicle: {reg}",
        f"Incident Date: {fmt_date(incident_date, d_fmt)}",
        f"Incident Time: {fir_time_str}",
        f"Location: {location}",
        "",
        "Report:",
        desc,
        "",
        "Status: Under Investigation",
        f"Date of Filing: {fmt_date(incident_date, d_fmt)}",
        "",
        "Officer: SI R. K. Patil",
    ]
    return "\n".join(lines)

def gen_vehicle_rc(claim, date_fmt_idx=None):
    d_fmt = date_fmt_idx if date_fmt_idx is not None else random.randint(0, len(DATE_FORMATS)-1)
    reg_label = random.choice(REG_LABELS)
    reg_date = claim['policy_start_dt'] - timedelta(days=random.randint(180, 1800))
    lines = [
        "REGISTRATION CERTIFICATE",
        "=" * 40,
        "",
        f"{reg_label}: {claim['vehicle_registration']}",
        f"Owner Name: {claim['customer_name']}",
        f"Vehicle Class: {'Motor Car' if claim['vehicle_type'] == 'Car' else 'Motor Cycle/Scooter'}",
        f"Make/Model: {claim.get('vehicle_make', claim['vehicle_type'])}",
        f"Fuel Type: Petrol",
        f"Registration Date: {fmt_date(reg_date, d_fmt)}",
        f"Registering Authority: RTO {claim['vehicle_registration'][:4]}",
        "",
        "Fitness Valid Till: " + fmt_date(reg_date + timedelta(days=365*15), d_fmt),
        "",
        "This is a computer-generated document.",
    ]
    return "\n".join(lines)

def gen_driving_license(claim, valid=True, date_fmt_idx=None):
    d_fmt = date_fmt_idx if date_fmt_idx is not None else random.randint(0, len(DATE_FORMATS)-1)
    issue_date = claim['incident_date_dt'] - timedelta(days=random.randint(365, 3650))
    if valid:
        expiry = claim['incident_date_dt'] + timedelta(days=random.randint(365, 3650))
    else:
        expiry = claim['incident_date_dt'] - timedelta(days=random.randint(30, 365))

    dl_number = f"MH-{random.randint(1, 50):02d}-{random.randint(2015, 2024)}-{random.randint(1000000, 9999999)}"
    veh_class = "LMV" if claim['vehicle_type'] == 'Car' else "MCWG"

    lines = [
        "DRIVING LICENCE",
        "=" * 40,
        "",
        f"DL Number: {dl_number}",
        f"Name: {claim['customer_name']}",
        f"Date of Issue: {fmt_date(issue_date, d_fmt)}",
        f"Valid Till: {fmt_date(expiry, d_fmt)}",
        f"Vehicle Class: {veh_class}",
        f"Issuing Authority: RTO {claim['vehicle_registration'][:4]}",
        "",
        "This is a computer-generated document.",
    ]
    return "\n".join(lines)

def gen_key_declaration(claim, keys_available=True, date_fmt_idx=None):
    d_fmt = date_fmt_idx if date_fmt_idx is not None else random.randint(0, len(DATE_FORMATS)-1)
    total_keys = random.choice([2, 2, 2, 3])
    if keys_available:
        keys_submitted = total_keys
    else:
        keys_submitted = total_keys - random.randint(1, total_keys)

    lines = [
        "KEY DECLARATION",
        "=" * 40,
        "",
        f"Claim ID: {claim['claim_id']}",
        f"Policy Number: {claim['policy_number']}",
        f"Vehicle Registration: {claim['vehicle_registration']}",
        "",
        f"Total keys provided at time of purchase: {total_keys}",
        f"Keys currently in possession: {keys_submitted}",
        f"Keys submitted with this claim: {keys_submitted}",
        "",
    ]
    if keys_submitted < total_keys:
        lines.append(f"Note: {total_keys - keys_submitted} key(s) are unaccounted for.")
    else:
        lines.append("All keys accounted for and submitted herewith.")
    lines.extend([
        "",
        f"Declaration: I, {claim['customer_name']}, declare that the above information",
        "regarding vehicle keys is true and correct.",
        "",
        f"Signature: {claim['customer_name']}",
        f"Date: {fmt_date(claim['claim_date_dt'], d_fmt)}",
    ])
    return "\n".join(lines)

def gen_repair_invoice(claim, date_fmt_idx=None):
    d_fmt = date_fmt_idx if date_fmt_idx is not None else random.randint(0, len(DATE_FORMATS)-1)
    items = claim['repair_items']
    # Invoice may differ slightly from estimate
    invoice_items = [(p, int(c * random.uniform(0.9, 1.1))) for p, c in items]
    total = sum(c for _, c in invoice_items)

    lines = [
        "REPAIR INVOICE",
        "=" * 40,
        "",
        f"Invoice No: INV-{claim['claim_id'].replace('CLM', '')}-2026",
        f"Vehicle Registration: {claim['vehicle_registration']}",
        f"Date: {fmt_date(claim['incident_date_dt'] + timedelta(days=random.randint(7, 21)), d_fmt)}",
        "",
        "Repairs Completed:",
        "-" * 30,
    ]
    for part, cost in invoice_items:
        lines.append(f"  {part}: Rs. {cost:,}")
    lines.extend([
        "-" * 30,
        f"  Total: Rs. {total:,}",
        "",
        "Payment Terms: As per insurance agreement",
        "Workshop: Authorized Service Center",
    ])
    return "\n".join(lines)


# ── Claim Scenarios ──

def create_clean_accident(idx, claim_idx):
    claim = base_claim(claim_idx, "Accident")
    claim['expected_outcome'] = "APPROVE"
    claim['difficulty'] = "Easy"
    claim['scenario_type'] = "CLEAN"
    claim['expected_contradictions'] = []
    claim['expected_missing_documents'] = []
    claim['expected_policy_clauses'] = ["POL-001", "POL-004", "POL-005", "POL-014", "POL-015"]
    claim['expected_blocking_conditions'] = []
    claim['docs'] = {
        'claim_form': gen_claim_form(claim),
        'incident_description': gen_incident_description(claim),
        'repair_estimate': gen_repair_estimate(claim),
        'fir': gen_fir(claim),
        'vehicle_rc': gen_vehicle_rc(claim),
        'driving_license': gen_driving_license(claim, valid=True),
    }
    claim['document_count'] = len(claim['docs'])
    return claim

def create_clean_theft(idx, claim_idx):
    claim = base_claim(claim_idx, "Theft")
    claim['expected_outcome'] = "APPROVE"
    claim['difficulty'] = "Easy"
    claim['scenario_type'] = "CLEAN"
    claim['expected_contradictions'] = []
    claim['expected_missing_documents'] = []
    claim['expected_policy_clauses'] = ["POL-001", "POL-003", "POL-005", "POL-016", "POL-017"]
    claim['expected_blocking_conditions'] = []
    claim['repair_estimate_val'] = claim['idv']
    claim['docs'] = {
        'claim_form': gen_claim_form(claim),
        'incident_description': gen_incident_description(claim),
        'fir': gen_fir(claim),
        'vehicle_rc': gen_vehicle_rc(claim),
        'key_declaration': gen_key_declaration(claim, keys_available=True),
    }
    claim['document_count'] = len(claim['docs'])
    return claim

def create_missing_doc_accident(idx, claim_idx, missing_type):
    claim = base_claim(claim_idx, "Accident")
    claim['expected_outcome'] = "REQUEST_INFORMATION"
    claim['difficulty'] = "Medium"
    claim['scenario_type'] = "MISSING_DOCUMENT"
    claim['expected_contradictions'] = []
    claim['expected_blocking_conditions'] = []

    docs = {
        'claim_form': gen_claim_form(claim),
        'incident_description': gen_incident_description(claim),
        'repair_estimate': gen_repair_estimate(claim),
    }
    missing = []
    if missing_type == 'fir':
        missing = ['fir']
        claim['expected_policy_clauses'] = ["POL-025", "POL-006"]
    elif missing_type == 'repair_estimate':
        del docs['repair_estimate']
        missing = ['repair_estimate']
        claim['expected_policy_clauses'] = ["POL-018", "POL-006"]
    elif missing_type == 'driving_license':
        docs['fir'] = gen_fir(claim)
        docs['vehicle_rc'] = gen_vehicle_rc(claim)
        missing = ['driving_license']
        claim['expected_policy_clauses'] = ["POL-008", "POL-006"]
    elif missing_type == 'vehicle_rc':
        docs['fir'] = gen_fir(claim)
        missing = ['vehicle_rc']
        claim['expected_policy_clauses'] = ["POL-007", "POL-006"]

    claim['expected_missing_documents'] = missing
    claim['docs'] = docs
    claim['document_count'] = len(docs)
    return claim

def create_missing_doc_theft(idx, claim_idx, missing_type):
    claim = base_claim(claim_idx, "Theft")
    claim['expected_outcome'] = "REQUEST_INFORMATION"
    claim['difficulty'] = "Medium"
    claim['scenario_type'] = "MISSING_DOCUMENT"
    claim['expected_contradictions'] = []
    claim['expected_blocking_conditions'] = []
    claim['repair_estimate_val'] = claim['idv']

    docs = {
        'claim_form': gen_claim_form(claim),
        'incident_description': gen_incident_description(claim),
        'fir': gen_fir(claim),
        'vehicle_rc': gen_vehicle_rc(claim),
        'key_declaration': gen_key_declaration(claim, keys_available=True),
    }
    missing = []
    if missing_type == 'fir':
        del docs['fir']
        missing = ['fir']
        claim['expected_policy_clauses'] = ["POL-016", "POL-006"]
    elif missing_type == 'key_declaration':
        del docs['key_declaration']
        missing = ['key_declaration']
        claim['expected_policy_clauses'] = ["POL-017", "POL-006"]
    elif missing_type == 'vehicle_rc':
        del docs['vehicle_rc']
        missing = ['vehicle_rc']
        claim['expected_policy_clauses'] = ["POL-007", "POL-006"]

    claim['expected_missing_documents'] = missing
    claim['docs'] = docs
    claim['document_count'] = len(docs)
    return claim

def create_contradiction(idx, claim_idx, contradiction_type):
    claim = base_claim(claim_idx, random.choice(["Accident", "Accident", "Accident", "Theft"]))
    claim['expected_outcome'] = "ESCALATE"
    claim['difficulty'] = "Hard"
    claim['scenario_type'] = "CONTRADICTION"
    claim['expected_missing_documents'] = []
    claim['expected_blocking_conditions'] = []

    d_fmt = random.randint(0, len(DATE_FORMATS)-1)

    if contradiction_type == 'date':
        # FIR has different date
        wrong_date = claim['incident_date_dt'] + timedelta(days=random.choice([2, 3, -2]))
        docs = {
            'claim_form': gen_claim_form(claim, date_fmt_idx=d_fmt),
            'incident_description': gen_incident_description(claim, date_fmt_idx=d_fmt),
            'repair_estimate': gen_repair_estimate(claim, date_fmt_idx=d_fmt) if claim['incident_type'] == 'Accident' else None,
            'fir': gen_fir(claim, date_fmt_idx=d_fmt, override_date=wrong_date),
        }
        if claim['incident_type'] == 'Theft':
            docs['vehicle_rc'] = gen_vehicle_rc(claim)
            docs['key_declaration'] = gen_key_declaration(claim, keys_available=True)
            if docs.get('repair_estimate') is None:
                del docs['repair_estimate']
        claim['expected_contradictions'] = ['incident_date']
        claim['expected_policy_clauses'] = ["POL-005", "POL-033"]

    elif contradiction_type == 'vehicle':
        wrong_reg = gen_reg()
        docs = {
            'claim_form': gen_claim_form(claim, date_fmt_idx=d_fmt),
            'incident_description': gen_incident_description(claim, date_fmt_idx=d_fmt),
            'fir': gen_fir(claim, date_fmt_idx=d_fmt, override_reg=wrong_reg),
        }
        if claim['incident_type'] == 'Accident':
            docs['repair_estimate'] = gen_repair_estimate(claim, date_fmt_idx=d_fmt)
        else:
            docs['vehicle_rc'] = gen_vehicle_rc(claim)
            docs['key_declaration'] = gen_key_declaration(claim, keys_available=True)
        claim['expected_contradictions'] = ['vehicle_registration']
        claim['expected_policy_clauses'] = ["POL-007", "POL-033"]

    elif contradiction_type == 'location':
        wrong_location = random.choice([c for c in CITIES if c != claim['incident_city']])
        docs = {
            'claim_form': gen_claim_form(claim, date_fmt_idx=d_fmt),
            'incident_description': gen_incident_description(claim, date_fmt_idx=d_fmt),
            'fir': gen_fir(claim, date_fmt_idx=d_fmt, override_location=f"Main Road, {wrong_location}"),
        }
        if claim['incident_type'] == 'Accident':
            docs['repair_estimate'] = gen_repair_estimate(claim, date_fmt_idx=d_fmt)
        else:
            docs['vehicle_rc'] = gen_vehicle_rc(claim)
            docs['key_declaration'] = gen_key_declaration(claim, keys_available=True)
        claim['expected_contradictions'] = ['incident_location']
        claim['expected_policy_clauses'] = ["POL-022", "POL-033"]

    elif contradiction_type == 'damage':
        # repair estimate has different damage items than claim form
        claim2 = dict(claim)
        claim2['damage_parts'] = pick_damage(claim['vehicle_type'], 3)
        claim2['repair_items'] = gen_repair_items(claim2['damage_parts'])
        docs = {
            'claim_form': gen_claim_form(claim, date_fmt_idx=d_fmt),
            'incident_description': gen_incident_description(claim, date_fmt_idx=d_fmt),
            'repair_estimate': gen_repair_estimate(claim2, date_fmt_idx=d_fmt),
            'fir': gen_fir(claim, date_fmt_idx=d_fmt),
        }
        claim['expected_contradictions'] = ['damage_description']
        claim['expected_policy_clauses'] = ["POL-018", "POL-033"]

    elif contradiction_type == 'name':
        alt_name = gen_name(claim_idx + 40)
        claim_copy = dict(claim)
        claim_copy['customer_name'] = alt_name
        docs = {
            'claim_form': gen_claim_form(claim, date_fmt_idx=d_fmt),
            'incident_description': gen_incident_description(claim, date_fmt_idx=d_fmt),
            'fir': gen_fir(claim_copy, date_fmt_idx=d_fmt),
        }
        if claim['incident_type'] == 'Accident':
            docs['repair_estimate'] = gen_repair_estimate(claim, date_fmt_idx=d_fmt)
        else:
            docs['vehicle_rc'] = gen_vehicle_rc(claim)
            docs['key_declaration'] = gen_key_declaration(claim, keys_available=True)
        claim['expected_contradictions'] = ['customer_name']
        claim['expected_policy_clauses'] = ["POL-020", "POL-033"]

    docs = {k: v for k, v in docs.items() if v is not None}
    claim['docs'] = docs
    claim['document_count'] = len(docs)
    return claim

def create_exclusion(idx, claim_idx, exclusion_type):
    claim = base_claim(claim_idx, "Accident")
    claim['expected_outcome'] = "REJECT"
    claim['difficulty'] = "Hard"
    claim['scenario_type'] = "EXCLUSION"
    claim['expected_contradictions'] = []
    claim['expected_missing_documents'] = []

    docs = {
        'claim_form': gen_claim_form(claim),
        'incident_description': gen_incident_description(claim),
        'repair_estimate': gen_repair_estimate(claim),
    }

    if exclusion_type == 'expired_licence':
        docs['driving_license'] = gen_driving_license(claim, valid=False)
        claim['expected_policy_clauses'] = ["POL-009"]
        claim['expected_blocking_conditions'] = ["invalid_licence"]

    elif exclusion_type == 'alcohol':
        # Modify FIR to mention alcohol
        fir_text = gen_fir(claim)
        fir_text = fir_text.replace(
            "Damage reported to the vehicle.",
            "Damage reported to the vehicle. The driver appeared to be under the influence of alcohol at the time of the incident as noted by the responding officer."
        )
        docs['fir'] = fir_text
        claim['expected_policy_clauses'] = ["POL-010"]
        claim['expected_blocking_conditions'] = ["alcohol_involvement"]

    elif exclusion_type == 'intentional':
        # Modify incident description to suggest intentional damage
        desc = gen_incident_description(claim)
        desc = desc.replace(
            "I immediately stopped and assessed the damage.",
            "The damage appears to have been self-inflicted as the vehicle was deliberately driven into a stationary object."
        ).replace(
            "There were no injuries.",
            "Upon investigation, witnesses reported the driver intentionally steered the vehicle into the barrier."
        ).replace(
            "I have obtained a repair estimate from an authorized service center.",
            "Witness statements suggest the collision was intentional."
        )
        docs['incident_description'] = desc
        claim['expected_policy_clauses'] = ["POL-011"]
        claim['expected_blocking_conditions'] = ["intentional_damage"]

    elif exclusion_type == 'mechanical':
        desc = gen_incident_description(claim)
        desc = desc.replace(
            "Another vehicle suddenly collided",
            "The engine seized while driving, causing loss of control. No other vehicle was involved. The damage is due to mechanical failure"
        ).replace(
            "was involved in a collision",
            "suffered engine seizure and mechanical breakdown while in motion"
        ).replace(
            "was hit by another vehicle",
            "experienced sudden mechanical failure causing the engine to seize"
        )
        docs['incident_description'] = desc
        claim['expected_policy_clauses'] = ["POL-013"]
        claim['expected_blocking_conditions'] = ["mechanical_breakdown"]

    elif exclusion_type == 'wear_tear':
        desc = gen_incident_description(claim)
        desc = desc.replace(
            "Another vehicle suddenly collided",
            "Over time, rust and corrosion had weakened the body panels. The damage claimed is primarily due to prolonged wear and tear"
        ).replace(
            "was involved in a collision",
            "has been gradually deteriorating due to wear and tear over several months"
        ).replace(
            "was hit by another vehicle",
            "has developed rust damage and paint deterioration from normal aging"
        )
        docs['incident_description'] = desc
        claim['expected_policy_clauses'] = ["POL-012"]
        claim['expected_blocking_conditions'] = ["wear_and_tear"]

    elif exclusion_type == 'policy_expired':
        # Set incident date outside policy period
        claim['incident_date_dt'] = claim['policy_end_dt'] + timedelta(days=15)
        claim['incident_date'] = claim['incident_date_dt'].strftime("%Y-%m-%d")
        claim['claim_date_dt'] = claim['incident_date_dt'] + timedelta(days=2)
        claim['claim_date'] = claim['claim_date_dt'].strftime("%Y-%m-%d")
        docs = {
            'claim_form': gen_claim_form(claim),
            'incident_description': gen_incident_description(claim),
            'repair_estimate': gen_repair_estimate(claim),
        }
        claim['expected_policy_clauses'] = ["POL-001"]
        claim['expected_blocking_conditions'] = ["policy_expired"]

    elif exclusion_type == 'commercial_use':
        desc = gen_incident_description(claim)
        desc = desc.replace(
            "I was driving my",
            "I was using my personal vehicle for ride-sharing service when I was driving my"
        ).replace(
            "while travelling",
            "while transporting a ride-share passenger and travelling"
        ).replace(
            "My vehicle",
            "My personal vehicle, being used for commercial ride-sharing,"
        )
        docs['incident_description'] = desc
        claim['expected_policy_clauses'] = ["POL-036"]
        claim['expected_blocking_conditions'] = ["commercial_use"]

    claim['docs'] = docs
    claim['document_count'] = len(docs)
    return claim

def create_ambiguous(idx, claim_idx, ambiguity_type):
    claim = base_claim(claim_idx, random.choice(["Accident", "Theft"]))
    claim['expected_outcome'] = "ESCALATE"
    claim['difficulty'] = "Hard"
    claim['scenario_type'] = "AMBIGUOUS"
    claim['expected_contradictions'] = []
    claim['expected_missing_documents'] = []
    claim['expected_blocking_conditions'] = []

    if ambiguity_type == 'vague_time':
        # Vague time in description
        claim['description'] = (
            f"The accident happened sometime around {claim['incident_time'][:2]}:00 or maybe a bit later, "
            f"I'm not exactly sure of the precise time. It was on {claim['incident_location']} in "
            f"{claim['incident_city']}. My vehicle {claim['vehicle_registration']} was damaged."
        )
        docs = {
            'claim_form': gen_claim_form(claim),
            'incident_description': gen_incident_description(claim),
        }
        if claim['incident_type'] == 'Accident':
            docs['repair_estimate'] = gen_repair_estimate(claim)
            docs['fir'] = gen_fir(claim)
        else:
            docs['fir'] = gen_fir(claim)
            docs['vehicle_rc'] = gen_vehicle_rc(claim)
            docs['key_declaration'] = gen_key_declaration(claim, keys_available=True)
        claim['expected_policy_clauses'] = ["POL-033", "POL-034"]

    elif ambiguity_type == 'vague_theft_time':
        claim['incident_type'] = 'Theft'
        claim['description'] = (
            f"I think the vehicle was stolen sometime during the night of "
            f"{fmt_date(claim['incident_date_dt'])}. I parked it at "
            f"{claim['incident_location']}, {claim['incident_city']} in the evening and "
            f"discovered it missing the next morning. I cannot provide an exact time."
        )
        claim['repair_estimate_val'] = claim['idv']
        docs = {
            'claim_form': gen_claim_form(claim),
            'incident_description': gen_incident_description(claim),
            'fir': gen_fir(claim),
            'vehicle_rc': gen_vehicle_rc(claim),
            'key_declaration': gen_key_declaration(claim, keys_available=True),
        }
        claim['expected_policy_clauses'] = ["POL-003", "POL-033", "POL-034"]

    elif ambiguity_type == 'late_claim':
        # Claim filed 12 days after incident
        claim['claim_date_dt'] = claim['incident_date_dt'] + timedelta(days=12)
        claim['claim_date'] = claim['claim_date_dt'].strftime("%Y-%m-%d")
        claim['description'] = (
            f"I was unable to file the claim earlier as I was hospitalized after the "
            f"accident on {fmt_date(claim['incident_date_dt'])}. I am now submitting "
            f"the claim along with hospital discharge papers."
        )
        docs = {
            'claim_form': gen_claim_form(claim),
            'incident_description': gen_incident_description(claim),
        }
        if claim['incident_type'] == 'Accident':
            docs['repair_estimate'] = gen_repair_estimate(claim)
        else:
            docs['fir'] = gen_fir(claim)
            docs['vehicle_rc'] = gen_vehicle_rc(claim)
            docs['key_declaration'] = gen_key_declaration(claim, keys_available=True)
        claim['expected_policy_clauses'] = ["POL-005", "POL-030", "POL-034"]

    elif ambiguity_type == 'borderline_repair':
        # Repair close to IDV
        claim['incident_type'] = 'Accident'
        high_parts = pick_damage(claim['vehicle_type'], 5)
        items = [(p, random.randint(40000, 80000)) for p in high_parts]
        claim['repair_items'] = items
        claim['repair_estimate_val'] = sum(c for _, c in items)
        claim['description'] = (
            f"Major accident on {fmt_date(claim['incident_date_dt'])} involving my "
            f"vehicle {claim['vehicle_registration']} at {claim['incident_location']}, "
            f"{claim['incident_city']}. The vehicle sustained extensive damage."
        )
        docs = {
            'claim_form': gen_claim_form(claim),
            'incident_description': gen_incident_description(claim),
            'repair_estimate': gen_repair_estimate(claim),
            'fir': gen_fir(claim),
        }
        claim['expected_policy_clauses'] = ["POL-014", "POL-026", "POL-034"]

    elif ambiguity_type == 'partial_info':
        claim['description'] = (
            f"There was an incident with my vehicle. I am not able to recall all the "
            f"details clearly. It happened near {claim['incident_city']}. "
            f"My vehicle {claim['vehicle_registration']} was damaged."
        )
        docs = {
            'claim_form': gen_claim_form(claim),
            'incident_description': gen_incident_description(claim),
        }
        if claim['incident_type'] == 'Accident':
            docs['repair_estimate'] = gen_repair_estimate(claim)
        else:
            docs['fir'] = gen_fir(claim)
            docs['vehicle_rc'] = gen_vehicle_rc(claim)
        claim['expected_policy_clauses'] = ["POL-006", "POL-033", "POL-034"]

    claim['docs'] = docs
    claim['document_count'] = len(docs)
    return claim


def base_claim(idx, incident_type):
    vehicle_type = random.choice(["Car", "Car", "Two-Wheeler"])
    reg = gen_reg()
    policy_start, policy_end = gen_policy_dates()
    incident_date = gen_incident_date(policy_start, policy_end, within_policy=True)
    claim_date = gen_claim_date(incident_date, late=False)
    city = random.choice(CITIES)
    location = random.choice(LOCATIONS_DETAIL)

    if vehicle_type == "Car":
        idv = random.choice([350000, 450000, 550000, 650000, 750000, 850000])
        deductible = 2000
        make = random.choice(CAR_MAKES)
    else:
        idv = random.choice([50000, 70000, 90000, 110000, 130000])
        deductible = 1000
        make = random.choice(BIKE_MAKES)

    damage = pick_damage(vehicle_type)
    repair_items = gen_repair_items(damage)
    repair_total = sum(c for _, c in repair_items)
    time = gen_time()

    if incident_type == 'Accident':
        desc = (f"On the day of the incident, I was driving my {vehicle_type.lower()} "
                f"near {location} in {city}. Another vehicle collided with mine, "
                f"causing damage to the {', '.join(damage[:2])}.")
    else:
        desc = (f"I parked my {vehicle_type.lower()} at {location} in {city}. "
                f"When I returned, the vehicle was missing from the parking spot.")

    return {
        'claim_id': f"CLM{idx:03d}",
        'policy_number': gen_policy_number(idx),
        'customer_name': gen_name(idx),
        'vehicle_type': vehicle_type,
        'vehicle_registration': reg,
        'vehicle_make': make,
        'incident_type': incident_type,
        'incident_date': incident_date.strftime("%Y-%m-%d"),
        'incident_date_dt': incident_date,
        'incident_time': time,
        'incident_location': location,
        'incident_city': city,
        'claim_date': claim_date.strftime("%Y-%m-%d"),
        'claim_date_dt': claim_date,
        'policy_start_date': policy_start.strftime("%Y-%m-%d"),
        'policy_start_dt': policy_start,
        'policy_end_date': policy_end.strftime("%Y-%m-%d"),
        'policy_end_dt': policy_end,
        'idv': idv,
        'repair_estimate_val': repair_total,
        'deductible': deductible,
        'damage_parts': damage,
        'repair_items': repair_items,
        'description': desc,
        'document_count': 0,
    }


def generate_all():
    claims = []
    claim_idx = 1

    # ── 25 clean claims: 15 accident + 10 theft ──
    for i in range(15):
        claims.append(create_clean_accident(i, claim_idx))
        claim_idx += 1
    for i in range(10):
        claims.append(create_clean_theft(i, claim_idx))
        claim_idx += 1

    # ── 10 extra claims to reach 80: 7 accident + 3 theft ──
    for i in range(7):
        claims.append(create_clean_accident(i + 15, claim_idx))
        claim_idx += 1
    for i in range(3):
        claims.append(create_clean_theft(i + 10, claim_idx))
        claim_idx += 1

    # ── 15 missing-document claims ──
    accident_missing = ['fir', 'repair_estimate', 'driving_license', 'vehicle_rc',
                        'fir', 'repair_estimate', 'driving_license', 'vehicle_rc',
                        'fir', 'repair_estimate']
    theft_missing = ['fir', 'key_declaration', 'vehicle_rc', 'key_declaration', 'fir']
    for mt in accident_missing:
        claims.append(create_missing_doc_accident(0, claim_idx, mt))
        claim_idx += 1
    for mt in theft_missing:
        claims.append(create_missing_doc_theft(0, claim_idx, mt))
        claim_idx += 1

    # ── 15 contradiction claims ──
    contradiction_types = ['date', 'date', 'date', 'vehicle', 'vehicle', 'vehicle',
                           'location', 'location', 'location', 'damage', 'damage',
                           'name', 'name', 'date', 'vehicle']
    for ct in contradiction_types:
        claims.append(create_contradiction(0, claim_idx, ct))
        claim_idx += 1

    # ── 10 exclusion claims ──
    exclusion_types = ['expired_licence', 'alcohol', 'intentional', 'mechanical',
                       'wear_tear', 'policy_expired', 'commercial_use',
                       'expired_licence', 'alcohol', 'policy_expired']
    for et in exclusion_types:
        claims.append(create_exclusion(0, claim_idx, et))
        claim_idx += 1

    # ── 5 ambiguous claims ──
    ambiguous_types = ['vague_time', 'vague_theft_time', 'late_claim',
                       'borderline_repair', 'partial_info']
    for at in ambiguous_types:
        claims.append(create_ambiguous(0, claim_idx, at))
        claim_idx += 1

    return claims


def save_claims(claims):
    # Create subdirectories
    for subdir in ['accident', 'theft', 'missing_documents', 'contradictions', 'exclusions', 'ambiguous']:
        (CLAIMS_DIR / subdir).mkdir(parents=True, exist_ok=True)

    # Map scenario to folder
    folder_map = {
        'CLEAN': lambda c: 'accident' if c['incident_type'] == 'Accident' else 'theft',
        'MISSING_DOCUMENT': lambda c: 'missing_documents',
        'CONTRADICTION': lambda c: 'contradictions',
        'EXCLUSION': lambda c: 'exclusions',
        'AMBIGUOUS': lambda c: 'ambiguous',
    }

    # Save documents
    for claim in claims:
        folder = folder_map[claim['scenario_type']](claim)
        claim_dir = CLAIMS_DIR / folder / claim['claim_id']
        claim_dir.mkdir(parents=True, exist_ok=True)

        for doc_name, doc_content in claim['docs'].items():
            filepath = claim_dir / f"{doc_name}.txt"
            filepath.write_text(doc_content, encoding='utf-8')

        # Save ground truth
        ground_truth = {
            'claim_id': claim['claim_id'],
            'expected_outcome': claim['expected_outcome'],
            'expected_contradictions': claim.get('expected_contradictions', []),
            'expected_missing_documents': claim.get('expected_missing_documents', []),
            'expected_policy_clauses': claim.get('expected_policy_clauses', []),
            'expected_blocking_conditions': claim.get('expected_blocking_conditions', []),
            'scenario_type': claim['scenario_type'],
            'difficulty': claim['difficulty'],
        }
        gt_path = claim_dir / "ground_truth.json"
        gt_path.write_text(json.dumps(ground_truth, indent=2), encoding='utf-8')

    # Save claims_master.csv
    csv_path = CLAIMS_DIR / "claims_master.csv"
    fieldnames = [
        'claim_id', 'policy_number', 'customer_name', 'vehicle_type',
        'vehicle_registration', 'incident_type', 'incident_date', 'incident_time',
        'incident_location', 'claim_date', 'policy_start_date', 'policy_end_date',
        'idv', 'repair_estimate', 'deductible', 'document_count',
        'expected_outcome', 'difficulty', 'scenario_type'
    ]
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for c in claims:
            writer.writerow({
                'claim_id': c['claim_id'],
                'policy_number': c['policy_number'],
                'customer_name': c['customer_name'],
                'vehicle_type': c['vehicle_type'],
                'vehicle_registration': c['vehicle_registration'],
                'incident_type': c['incident_type'],
                'incident_date': c['incident_date'],
                'incident_time': c['incident_time'],
                'incident_location': f"{c['incident_location']}, {c['incident_city']}",
                'claim_date': c['claim_date'],
                'policy_start_date': c['policy_start_date'],
                'policy_end_date': c['policy_end_date'],
                'idv': c['idv'],
                'repair_estimate': c.get('repair_estimate_val', 0),
                'deductible': c['deductible'],
                'document_count': c['document_count'],
                'expected_outcome': c['expected_outcome'],
                'difficulty': c['difficulty'],
                'scenario_type': c['scenario_type'],
            })

    # Save generation metadata
    gen_dir = DATA_DIR / "generated"
    gen_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "generated_at": datetime.now().isoformat(),
        "seed": SEED,
        "total_claims": len(claims),
        "distribution": {
            "clean": sum(1 for c in claims if c['scenario_type'] == 'CLEAN'),
            "missing_document": sum(1 for c in claims if c['scenario_type'] == 'MISSING_DOCUMENT'),
            "contradiction": sum(1 for c in claims if c['scenario_type'] == 'CONTRADICTION'),
            "exclusion": sum(1 for c in claims if c['scenario_type'] == 'EXCLUSION'),
            "ambiguous": sum(1 for c in claims if c['scenario_type'] == 'AMBIGUOUS'),
        },
        "incident_types": {
            "accident": sum(1 for c in claims if c['incident_type'] == 'Accident'),
            "theft": sum(1 for c in claims if c['incident_type'] == 'Theft'),
        }
    }
    (gen_dir / "generation_metadata.json").write_text(json.dumps(metadata, indent=2), encoding='utf-8')

    print(f"\n✓ Generated {len(claims)} claims")
    print(f"  Clean: {metadata['distribution']['clean']}")
    print(f"  Missing Document: {metadata['distribution']['missing_document']}")
    print(f"  Contradiction: {metadata['distribution']['contradiction']}")
    print(f"  Exclusion: {metadata['distribution']['exclusion']}")
    print(f"  Ambiguous: {metadata['distribution']['ambiguous']}")
    print(f"  Accident: {metadata['incident_types']['accident']}")
    print(f"  Theft: {metadata['incident_types']['theft']}")
    print(f"\n✓ Claims saved to {CLAIMS_DIR}")
    print(f"✓ CSV saved to {csv_path}")


if __name__ == "__main__":
    print("=" * 50)
    print("ClaimLens AI — Dataset Generator")
    print("=" * 50)
    (DATA_DIR / "embeddings").mkdir(parents=True, exist_ok=True)
    claims = generate_all()
    save_claims(claims)
    print("\n✓ Dataset generation complete!")
