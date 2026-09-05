"""
Generate realistic sample motor insurance claim PDFs for ClaimLens AI.
"""
import os
import fitz  # pymupdf

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "sample_documents")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def create_claim_form_pdf():
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4
    
    # Header Banner
    rect = fitz.Rect(30, 30, 565, 80)
    page.draw_rect(rect, color=(0.12, 0.23, 0.45), fill=(0.94, 0.96, 1.0), width=1.5)
    page.insert_text((45, 55), "SHIELD MOTOR INSURANCE COMPANY LIMITED", fontsize=14, fontname="helv", color=(0.1, 0.2, 0.4))
    page.insert_text((45, 72), "FORM CL-01: MOTOR VEHICLE ACCIDENT CLAIM INTIMATION FORM", fontsize=10, fontname="helv", color=(0.3, 0.3, 0.3))
    
    y = 105
    def add_section(title):
        nonlocal y
        page.draw_rect(fitz.Rect(30, y-12, 565, y+5), fill=(0.88, 0.92, 0.98))
        page.insert_text((40, y), title.upper(), fontsize=10, fontname="helv", color=(0.1, 0.2, 0.4))
        y += 22

    def add_field(label, value, x_offset=40, width=240):
        nonlocal y
        page.insert_text((x_offset, y), f"{label}:", fontsize=9, fontname="helv", color=(0.4, 0.4, 0.4))
        page.insert_text((x_offset + 120, y), str(value), fontsize=9.5, fontname="helv", color=(0.1, 0.1, 0.1))

    add_section("1. Policyholder & Vehicle Identification")
    add_field("Policy Number", "POL-2024-001", 40)
    add_field("Insured Name", "Rahul Sharma", 320)
    y += 18
    add_field("Contact Mobile", "+91 98201 54321", 40)
    add_field("Email Address", "rahul.sharma@example.com", 320)
    y += 18
    add_field("Registration No", "KA01MJ9082", 40)
    add_field("Vehicle Type", "Private Car (Sedan)", 320)
    y += 18
    add_field("Make & Model", "Honda City 1.5 V i-VTEC", 40)
    add_field("Year of Mfg / IDV", "2021 / Rs. 6,50,000", 320)
    y += 26

    add_section("2. Incident Circumstances")
    add_field("Date of Incident", "12/11/2024", 40)
    add_field("Time of Incident", "14:30 HRS (02:30 PM)", 320)
    y += 18
    add_field("Incident Location", "Outer Ring Road, Bellandur, Bengaluru", 40)
    add_field("Nature of Loss", "Frontal Collision with divider", 320)
    y += 18
    add_field("Driver at Time", "Rahul Sharma (Owner-Driver)", 40)
    add_field("Driving License No", "KA01-20150087421 (Valid)", 320)
    y += 26

    add_section("3. Damage Assessment & Intimation Details")
    add_field("Claim Intimation Date", "13/11/2024 (Within 24 Hours)", 40)
    add_field("Estimated Claim Amount", "Rs. 48,500", 320)
    y += 18
    add_field("Workshop Name", "Prime Honda Authorized Service Centre", 40)
    add_field("Workshop Location", "Whitefield Road, Mahadevapura, Bengaluru", 320)
    y += 18
    add_field("Damaged Components", "Front bumper cracked, radiator grille broken, RHS headlamp assembly shattered", 40)
    y += 28

    add_section("4. Insured Declaration")
    desc = (
        "I, Rahul Sharma, hereby declare that on 12th November 2024 at approx 2:30 PM, while driving my Honda City "
        "(Reg: KA01MJ9082) on Outer Ring Road near Bellandur, a stray dog suddenly crossed the road. In attempting "
        "to avoid the animal, the vehicle collided with the median curb divider causing severe impact to the front bumper, "
        "grille, and right headlamp. No third party injuries or commercial carriage involved. Vehicle towed to Prime Honda."
    )
    rect_desc = fitz.Rect(40, y-5, 555, y+60)
    page.insert_textbox(rect_desc, desc, fontsize=8.5, fontname="helv", color=(0.2, 0.2, 0.2))
    
    y += 85
    page.insert_text((40, y), "Signature of Insured:  Rahul Sharma", fontsize=9, fontname="helv", color=(0.1, 0.2, 0.4))
    page.insert_text((360, y), "Date Signed: 13-11-2024", fontsize=9, fontname="helv", color=(0.3, 0.3, 0.3))
    
    # Footer
    page.draw_line(fitz.Point(30, 800), fitz.Point(565, 800), color=(0.7, 0.7, 0.7))
    page.insert_text((40, 815), "Official ClaimLens AI Evidence Docket — Verification Hash: 9F8A2D14C", fontsize=7.5, fontname="helv", color=(0.5, 0.5, 0.5))

    filepath = os.path.join(OUTPUT_DIR, "Accident_Claim_Form_KA01MJ9082.pdf")
    doc.save(filepath)
    doc.close()
    return filepath


def create_repair_estimate_pdf():
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    
    # Header
    page.draw_rect(fitz.Rect(30, 30, 565, 85), fill=(0.97, 0.97, 0.97), color=(0.2, 0.2, 0.2), width=1)
    page.insert_text((45, 55), "PRIME MOTORS HONDA AUTHORIZED WORKSHOP", fontsize=13, fontname="helv", color=(0.1, 0.1, 0.1))
    page.insert_text((45, 70), "Accident Repair Division | GSTIN: 29AABCP9912K1Z4 | Ph: 080-41558800", fontsize=8.5, fontname="helv", color=(0.3, 0.3, 0.3))
    page.insert_text((420, 55), "ESTIMATE QUOTATION", fontsize=10, fontname="helv", color=(0.8, 0.1, 0.1))
    page.insert_text((420, 70), "Est No: PMW-2024-8891", fontsize=8.5, fontname="helv", color=(0.3, 0.3, 0.3))

    y = 110
    # Customer Details
    page.insert_text((40, y), "Customer Name: Rahul Sharma", fontsize=9, fontname="helv")
    page.insert_text((320, y), "Date: 14/11/2024", fontsize=9, fontname="helv")
    y += 18
    page.insert_text((40, y), "Vehicle Reg No: KA01MJ9082", fontsize=9, fontname="helv")
    page.insert_text((320, y), "Vehicle Model: Honda City 1.5 V", fontsize=9, fontname="helv")
    y += 18
    page.insert_text((40, y), "Insurance: Shield Motor Insurance (POL-2024-001)", fontsize=9, fontname="helv")
    page.insert_text((320, y), "Odometer Reading: 28,450 KM", fontsize=9, fontname="helv")
    y += 28

    # Table Header
    page.draw_rect(fitz.Rect(30, y-12, 565, y+8), fill=(0.2, 0.25, 0.35))
    page.insert_text((40, y), "ITEM #", fontsize=8.5, fontname="helv", color=(1, 1, 1))
    page.insert_text((90, y), "PART DESCRIPTION / OPERATION", fontsize=8.5, fontname="helv", color=(1, 1, 1))
    page.insert_text((340, y), "TYPE", fontsize=8.5, fontname="helv", color=(1, 1, 1))
    page.insert_text((420, y), "QTY", fontsize=8.5, fontname="helv", color=(1, 1, 1))
    page.insert_text((480, y), "AMOUNT (INR)", fontsize=8.5, fontname="helv", color=(1, 1, 1))
    y += 16

    items = [
        ("01", "Front Bumper Assembly (OEM)", "Part", "1", "12,500.00"),
        ("02", "Radiator Front Grille Chrome/Mesh", "Part", "1", "6,800.00"),
        ("03", "Right Hand Side LED Headlamp Assembly", "Part", "1", "15,200.00"),
        ("04", "Front Bumper Bracket & Retainers Set", "Part", "1 Set", "2,400.00"),
        ("05", "Denting & Panel Alignment Labour", "Labour", "1 Job", "4,200.00"),
        ("06", "Bumper & Grille Painting (3-Coat Pearl)", "Paint", "1 Job", "5,400.00"),
        ("07", "Headlamp Aiming & Calibration", "Labour", "1 Job", "2,000.00"),
    ]

    for item in items:
        page.insert_text((40, y), item[0], fontsize=8.5, fontname="helv")
        page.insert_text((90, y), item[1], fontsize=8.5, fontname="helv")
        page.insert_text((340, y), item[2], fontsize=8.5, fontname="helv")
        page.insert_text((425, y), item[3], fontsize=8.5, fontname="helv")
        page.insert_text((490, y), item[4], fontsize=8.5, fontname="helv")
        page.draw_line(fitz.Point(30, y+4), fitz.Point(565, y+4), color=(0.85, 0.85, 0.85), width=0.5)
        y += 18

    y += 10
    # Summary Box
    page.draw_rect(fitz.Rect(350, y, 565, y+70), fill=(0.96, 0.96, 0.96), color=(0.5, 0.5, 0.5))
    page.insert_text((360, y+18), "Parts Subtotal:", fontsize=8.5, fontname="helv")
    page.insert_text((485, y+18), "Rs. 36,900.00", fontsize=8.5, fontname="helv")
    page.insert_text((360, y+34), "Labour & Painting:", fontsize=8.5, fontname="helv")
    page.insert_text((485, y+34), "Rs. 11,600.00", fontsize=8.5, fontname="helv")
    page.insert_text((360, y+55), "TOTAL ESTIMATE:", fontsize=9.5, fontname="helv", color=(0.8, 0.1, 0.1))
    page.insert_text((480, y+55), "Rs. 48,500.00", fontsize=10, fontname="helv", color=(0.8, 0.1, 0.1))
    
    y += 95
    page.insert_text((40, y), "Authorized Workshop Signatory:  Sunil Kumar (Service Advisor)", fontsize=9, fontname="helv")
    page.insert_text((40, y+16), "Note: Actual charges subject to insurance surveyor physical inspection.", fontsize=8, fontname="helv", color=(0.5, 0.5, 0.5))

    filepath = os.path.join(OUTPUT_DIR, "Authorized_Garage_Repair_Estimate_KA01MJ9082.pdf")
    doc.save(filepath)
    doc.close()
    return filepath


def create_theft_fir_pdf():
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    
    # Official State Police Header
    page.draw_rect(fitz.Rect(30, 30, 565, 80), fill=(0.95, 0.95, 0.92), color=(0.3, 0.2, 0.1), width=1)
    page.insert_text((45, 52), "MAHARASHTRA STATE POLICE — MUMBAI ZONE 1", fontsize=12, fontname="helv", color=(0.2, 0.1, 0.0))
    page.insert_text((45, 68), "FIRST INFORMATION REPORT (Under Section 154 Cr.P.C.)", fontsize=10, fontname="helv", color=(0.4, 0.1, 0.1))
    page.insert_text((420, 52), "FIR NO: FIR-2024-051", fontsize=9.5, fontname="helv", color=(0.5, 0.1, 0.1))
    page.insert_text((420, 68), "POLICE STATION: Colaba", fontsize=8.5, fontname="helv")

    y = 110
    def add_line(k, v):
        nonlocal y
        page.insert_text((40, y), f"{k}:", fontsize=9, fontname="helv", color=(0.4, 0.4, 0.4))
        page.insert_text((220, y), str(v), fontsize=9, fontname="helv", color=(0.1, 0.1, 0.1))
        y += 18

    add_line("1. District & Police Station", "Mumbai South / Colaba Police Station")
    add_line("2. Acts & Sections", "Section 379 IPC (Theft of Motor Vehicle)")
    add_line("3. Date & Time of Occurrence", "08/11/2024 between 21:00 HRS to 23:30 HRS")
    add_line("4. Date & Time FIR Registered", "09/11/2024 at 08:30 HRS (Within 24 Hours)")
    add_line("5. Complainant / Informant Name", "Sunita Deshmukh")
    add_line("6. Contact & Address", "Flat 402, Sea Breeze Apts, Cuffe Parade, Mumbai")
    add_line("7. Stolen Vehicle Registration No", "MH01RB1289")
    add_line("8. Vehicle Make / Model / Type", "Two-Wheeler / Royal Enfield Classic 350 (Black)")
    add_line("9. Engine No / Chassis No", "U350-984214 / ME3U350B4L009841")
    add_line("10. Insured Declared Value / Loss", "Rs. 1,80,000 (One Lakh Eighty Thousand)")
    add_line("11. Place of Occurrence", "Public Parking outside Colaba Market, Colaba, Mumbai")
    add_line("12. Keys Accounted Status", "Both original ignition keys in complainant possession")
    
    y += 10
    page.draw_rect(fitz.Rect(30, y-8, 565, y+90), fill=(0.98, 0.98, 0.98), color=(0.7, 0.7, 0.7))
    page.insert_text((40, y+8), "BRIEF STATEMENT OF COMPLAINANT:", fontsize=8.5, fontname="helv", color=(0.3, 0.1, 0.1))
    stmt = (
        "I parked my Royal Enfield motorcycle (MH01RB1289) outside Colaba Market near gate 2 at 9:00 PM on 8 Nov 2024, "
        "duly locked the handlebar with key. Upon returning from dinner at 11:30 PM, the motorcycle was missing from the "
        "spot. I inquired with nearby shopkeepers and security but no trace was found. I possess both sets of original keys. "
        "Requesting urgent investigation and registration of vehicle theft FIR."
    )
    page.insert_textbox(fitz.Rect(40, y+16, 555, y+80), stmt, fontsize=8.5, fontname="helv")

    y += 110
    page.insert_text((40, y), "Investigating Officer:  Sub-Inspector V. K. Sawant", fontsize=9, fontname="helv")
    page.insert_text((350, y), "Station Seal & Signature Affixed", fontsize=8.5, fontname="helv", color=(0.3, 0.3, 0.3))

    filepath = os.path.join(OUTPUT_DIR, "Police_FIR_Theft_MH01RB1289.pdf")
    doc.save(filepath)
    doc.close()
    return filepath


def create_inflated_taxi_estimate_pdf():
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    
    # Header
    page.draw_rect(fitz.Rect(30, 30, 565, 80), fill=(1.0, 0.95, 0.95), color=(0.6, 0.1, 0.1), width=1)
    page.insert_text((45, 52), "SPEEDY BODYWORKS & AUTO COLLISION GARAGE", fontsize=12, fontname="helv", color=(0.6, 0.1, 0.1))
    page.insert_text((45, 68), "UNOFFICIAL ESTIMATE SHEET — ACCIDENT REPAIRS (COMMERCIAL TAXI)", fontsize=9, fontname="helv")
    page.insert_text((420, 52), "ESTIMATE # SB-9012", fontsize=9.5, fontname="helv")

    y = 110
    def add_line(k, v):
        nonlocal y
        page.insert_text((40, y), f"{k}:", fontsize=9, fontname="helv", color=(0.4, 0.4, 0.4))
        page.insert_text((220, y), str(v), fontsize=9, fontname="helv", color=(0.1, 0.1, 0.1))
        y += 18

    add_line("Vehicle Reg No", "DL01AZ9988 (Yellow Plate Commercial Taxi)")
    add_line("Owner / Fleet Operator", "Express Cabs Logistics Pvt Ltd")
    add_line("Driver Name", "Mukesh Yadav")
    add_line("Vehicle Model", "Maruti Ertiga Tour M (Commercial Yellow Board)")
    add_line("Incident Date Reported", "05/11/2024")
    add_line("Policy Number", "POL-2024-TAX-099")
    add_line("Estimated Repair Cost", "Rs. 1,85,000 (INFLATED: 3.5x Market Value)")
    add_line("Reported Damage", "Rear bumper scratch, Tail lamp cracked, Alleged complete chassis realignment")
    add_line("Discrepancy Indicators", "Policy is strictly PRIVATE CAR coverage but vehicle used for COMMERCIAL PASSENGER TAXI; Math sum Rs. 1,12,000 does not match stated Rs. 1,85,000!")

    y += 20
    page.insert_text((40, y), "WARNING: High-risk red flag candidate for SIU investigation & commercial use exclusion.", fontsize=8.5, fontname="helv", color=(0.8, 0.1, 0.1))

    filepath = os.path.join(OUTPUT_DIR, "Inflated_Taxi_Overclaim_Estimate_DL01AZ9988.pdf")
    doc.save(filepath)
    doc.close()
    return filepath


if __name__ == "__main__":
    f1 = create_claim_form_pdf()
    f2 = create_repair_estimate_pdf()
    f3 = create_theft_fir_pdf()
    f4 = create_inflated_taxi_estimate_pdf()
    print("Generated 4 sample PDFs:")
    print("1.", f1)
    print("2.", f2)
    print("3.", f3)
    print("4.", f4)
