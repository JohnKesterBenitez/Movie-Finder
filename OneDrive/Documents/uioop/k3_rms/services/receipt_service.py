import os
from tkinter import filedialog, messagebox
from fpdf import FPDF
from datetime import datetime

class ReceiptService:
    @staticmethod
    def generate_receipt(reservation: dict) -> str | None:
        try:
            pdf = FPDF()
            pdf.add_page()
            
            # Colors
            TEAL_RGB = (45, 115, 105)
            GRAY_RGB = (100, 100, 100)
            BLACK_RGB = (50, 50, 50)
            
            # Header
            pdf.set_font("Helvetica", "B", 22)
            pdf.set_text_color(*TEAL_RGB)
            pdf.cell(0, 20, "ISLABOOK RESERVATION", new_x="LMARGIN", new_y="NEXT", align="C")
            
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(*GRAY_RGB)
            ref_code = reservation.get("reservation_code") or reservation.get("ref", "UNKNOWN")
            pdf.cell(0, 10, f"Booking Receipt: {ref_code}", new_x="LMARGIN", new_y="NEXT", align="C")
            pdf.ln(10)
            
            # Line
            pdf.set_draw_color(200, 200, 200)
            pdf.line(20, 50, 190, 50)
            pdf.ln(5)
            
            # Details Table-like layout
            def add_row(label, value):
                pdf.set_font("Helvetica", "B", 11)
                pdf.set_text_color(*BLACK_RGB)
                pdf.cell(50, 10, label, new_x="RIGHT", new_y="TOP")
                pdf.set_font("Helvetica", "", 11)
                pdf.cell(0, 10, str(value), new_x="LMARGIN", new_y="NEXT")
            
            guest_name = reservation.get("full_name") or reservation.get("name", "")
            add_row("Guest Name:", guest_name)
            
            contact_num = reservation.get("contact_number") or reservation.get("contact", "")
            add_row("Contact No:", contact_num)
            
            email = reservation.get("email")
            add_row("Email:", email if email else "N/A")
            
            cottage_str = f"{reservation.get('cottage_code', '')} | {reservation.get('cottage_name', '')}".strip(" |")
            if not cottage_str:
                cottage_str = reservation.get("cottage_id", "")
            add_row("Cottage:", cottage_str)
            
            # Multi-line destinations
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(50, 10, "Destinations:", new_x="RIGHT", new_y="TOP")
            pdf.set_font("Helvetica", "", 11)
            pdf.multi_cell(0, 10, reservation.get("destination", ""))
            
            dep_time = reservation.get("departure_time")
            ret_time = reservation.get("return_time")
            
            if hasattr(dep_time, "strftime"):
                date_str = dep_time.strftime("%Y-%m-%d")
                time_str = dep_time.strftime("%I:%M %p")
            else:
                date_str = reservation.get("date", "")
                time_str = reservation.get("slot", str(dep_time))
            
            add_row("Travel Date:", date_str)
            add_row("Departure Time:", time_str)
            
            hours = reservation.get("hours")
            if hours is None and dep_time and ret_time and hasattr(dep_time, "timestamp"):
                hours = max(int((ret_time.timestamp() - dep_time.timestamp()) // 3600), 1)
            add_row("Duration:", f"{hours} hour(s)")
            
            party = reservation.get("party_size") or reservation.get("party", "")
            add_row("Party Size:", f"{party} pax")
            
            pdf.ln(10)
            pdf.set_draw_color(*TEAL_RGB)
            pdf.set_line_width(0.5)
            pdf.line(20, pdf.get_y(), 190, pdf.get_y())
            pdf.ln(5)
            
            # Total
            total = float(reservation.get("total_price") or reservation.get("total") or 0)
            pdf.set_font("Helvetica", "B", 16)
            pdf.set_text_color(*BLACK_RGB)
            pdf.cell(100, 15, "TOTAL PRICE PAID:", new_x="RIGHT", new_y="TOP")
            pdf.set_text_color(*TEAL_RGB)
            pdf.cell(0, 15, f"PHP {total:,.2f}", new_x="LMARGIN", new_y="NEXT", align="R")
            
            pdf.ln(20)
            pdf.set_font("Helvetica", "I", 10)
            pdf.set_text_color(128, 128, 128)
            pdf.cell(0, 10, "Thank you for choosing K3's Floating Cottage!", new_x="LMARGIN", new_y="NEXT", align="C")
            
            created_at = reservation.get("created_at") or datetime.now()
            if hasattr(created_at, "strftime"):
                created_str = created_at.strftime("%Y-%m-%d %H:%M:%S")
            else:
                created_str = str(created_at)
            pdf.cell(0, 10, f"Generated on: {created_str}", new_x="LMARGIN", new_y="NEXT", align="C")

            # Ask user where to save
            filename = f"Receipt_{ref_code}.pdf"
            path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf")],
                initialfile=filename,
                title="Save Receipt",
            )
            if not path:
                return None

            pdf.output(path)
            return path
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate PDF: {str(e)}")
            raise e
