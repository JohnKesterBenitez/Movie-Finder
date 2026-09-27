from fpdf import FPDF

res = {
    'ref': 'K3-77WIH',
    'name': '3efasfa',
    'contact': '23434235',
    'email': 'asdferq',
    'cottage_id': 'FC-01',
    'cottage_name': 'Azure Breeze',
    'destination': 'SandBar Area',
    'date': 'May 29, 2026',
    'slot': '08:00 AM - 12:00 PM',
    'hours': 4,
    'party': 6,
    'total': 11200.0,
    'created_at': '2026-05-08'
}
pdf = FPDF()
pdf.add_page()
TEAL_RGB = (45, 115, 105)
GRAY_RGB = (100, 100, 100)
BLACK_RGB = (50, 50, 50)
pdf.set_font('Helvetica', 'B', 22)
pdf.set_text_color(*TEAL_RGB)
pdf.cell(0, 20, 'ISLABOOK RESERVATION', ln=True, align='C')

pdf.set_font('Helvetica', 'B', 12)
pdf.set_text_color(*GRAY_RGB)
pdf.cell(0, 10, f"Booking Receipt: {res['ref']}", ln=True, align='C')
pdf.ln(10)
pdf.set_draw_color(200, 200, 200)
pdf.line(20, 50, 190, 50)
pdf.ln(5)

def add_row(label, value):
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(*BLACK_RGB)
    pdf.cell(50, 10, label, ln=False)
    pdf.set_font('Helvetica', '', 11)
    pdf.cell(0, 10, str(value), ln=True)

add_row('Guest Name:', res['name'])
add_row('Contact No:', res['contact'])
add_row('Email:', res['email'] if res.get('email') else 'N/A')
add_row('Cottage:', f"{res['cottage_id']} | {res['cottage_name']}")

pdf.set_font('Helvetica', 'B', 11)
pdf.cell(50, 10, 'Destinations:', ln=False)
pdf.set_font('Helvetica', '', 11)
pdf.multi_cell(0, 10, res['destination'])

add_row('Travel Date:', res['date'])
add_row('Departure Time:', res['slot'])
add_row('Duration:', f"{res['hours']} hour(s)")
add_row('Party Size:', f"{res['party']} pax")

pdf.ln(10)
pdf.set_draw_color(*TEAL_RGB)
pdf.set_line_width(0.5)
pdf.line(20, pdf.get_y(), 190, pdf.get_y())
pdf.ln(5)

pdf.set_font('Helvetica', 'B', 16)
pdf.set_text_color(*BLACK_RGB)
pdf.cell(100, 15, 'TOTAL PRICE PAID:', ln=False)
pdf.set_text_color(*TEAL_RGB)
pdf.cell(0, 15, f"PHP {res['total']:,.2f}", ln=True, align='R')

pdf.ln(20)
pdf.set_font('Helvetica', 'I', 10)
pdf.set_text_color(128, 128, 128)
pdf.cell(0, 10, "Thank you for choosing K3's Floating Cottage!", ln=True, align='C')
pdf.cell(0, 10, f"Generated on: {res['created_at']}", ln=True, align='C')

pdf.output('test_receipt.pdf')
