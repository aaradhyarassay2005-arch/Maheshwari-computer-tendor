import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors


def generate_sample_boq_pdf(dest_path: str):
    # Ensure directory exists
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    
    doc = SimpleDocTemplate(dest_path, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    
    # Title
    title_text = "<b>NORTHERN RAILWAY - BOQ SAMPLE</b>"
    story.append(Paragraph(title_text, styles["Title"]))
    story.append(Spacer(1, 12))
    
    # Info
    story.append(Paragraph("Tender Notice No: NR-CIVIL-2026-15", styles["Normal"]))
    story.append(Paragraph("Name of Work: Construction of station building at Kashmiri Gate", styles["Normal"]))
    story.append(Spacer(1, 18))
    
    # Schedule A Header
    story.append(Paragraph("<b>SCHEDULE - A (Items of Works)</b>", styles["Heading2"]))
    story.append(Spacer(1, 8))
    
    # Table data
    data_sched_a = [
        ["Item No", "Description of Item / Work", "Quantity", "Unit", "Rate (Rs.)", "Amount (Rs.)"],
        ["1", "Earthwork in excavation", "150.00", "Cum", "320.00", "48000.00"],
        ["2", "Providing cement concrete 1:3:6", "80.00", "Cum", "4200.00", "336000.00"],
        ["", "excluding cost of cement and reinforcement", "", "", "", ""],
        ["3", "Brick work in cement mortar 1:6", "250.00", "Sqm", "450.00", "112500.00"],
    ]
    
    t1 = Table(data_sched_a, colWidths=[50, 200, 60, 50, 70, 70])
    t1.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
    ]))
    story.append(t1)
    
    # Force page break to test multi-page extraction and schedule change
    story.append(PageBreak())
    
    # Page 2: Schedule B
    story.append(Paragraph("<b>SCHEDULE - B (Special Items)</b>", styles["Heading2"]))
    story.append(Spacer(1, 8))
    
    data_sched_b = [
        ["Item No", "Description of Item / Work", "Quantity", "Unit", "Rate (Rs.)", "Amount (Rs.)"],
        ["4", "Structural steel work", "1500.00", "Kg", "90.00", "135000.00"],
        ["5", "Supply of security signage boards", "25.00", "Nos.", "1800.00", "45000.00"],
        ["", "as per drawing specification and approval", "", "", "", ""],
    ]

    
    t2 = Table(data_sched_b, colWidths=[50, 200, 60, 50, 70, 70])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
    ]))
    story.append(t2)
    
    doc.build(story)


if __name__ == "__main__":
    generate_sample_boq_pdf("tests/test_files/test_boq_replica.pdf")
