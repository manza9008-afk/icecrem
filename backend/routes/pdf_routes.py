"""
HOOREN ERP - PDF Generation Service
Professional invoices and reports with QR code support
"""
from fastapi import APIRouter, HTTPException, Depends, Response
from typing import Optional
from datetime import datetime, timezone
import io
import base64
import qrcode

router = APIRouter(prefix="/api/pdf", tags=["pdf"])

from server import db
from utils import get_current_user

# Try to import reportlab, fallback to simple HTML if not available
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.units import inch, mm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


def generate_qr_code(data: str) -> bytes:
    """Generate QR code as PNG bytes"""
    qr = qrcode.QRCode(version=1, box_size=4, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer.getvalue()


def generate_gst_qr_data(invoice: dict, company: dict) -> str:
    """Generate GST-compliant QR code data"""
    # As per GST QR code specification
    qr_data = {
        "sellerGstin": company.get("gstin", ""),
        "buyerGstin": invoice.get("customer_gstin", ""),
        "docNo": invoice.get("invoice_number", ""),
        "docDt": invoice.get("invoice_date", ""),
        "totInvVal": invoice.get("grand_total", 0),
        "itemCnt": len(invoice.get("items", [])),
        "mainHsnCode": invoice.get("items", [{}])[0].get("hsn_code", ""),
        "irn": invoice.get("irn", "")
    }
    
    # Format as GST QR string
    qr_string = f"upi://pay?pa={company.get('upi_id', '')}&pn={company.get('name', '')}&am={invoice.get('grand_total', 0)}&cu=INR&tn=Invoice-{invoice.get('invoice_number', '')}"
    
    return qr_string


@router.get("/invoice/{invoice_id}")
async def generate_invoice_pdf(
    invoice_id: str,
    include_qr: bool = True,
    current_user: dict = Depends(get_current_user)
):
    """Generate professional GST invoice PDF"""
    
    # Get invoice
    invoice = await db.sales_invoices.find_one({"id": invoice_id}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Get company info
    company = await db.company_settings.find_one({}, {"_id": 0})
    if not company:
        company = {
            "name": "HOOREN FOOD PRODUCTS",
            "address": "Survey No 409, Ranuj, Patan, Gujarat",
            "gstin": "24AAHFH1702M1ZK",
            "state": "Gujarat",
            "state_code": "24",
            "phone": "",
            "email": ""
        }
    
    # Get branch info
    branch = await db.branches.find_one({"id": invoice.get("branch_id")}, {"_id": 0})
    
    if not HAS_REPORTLAB:
        # Return HTML invoice if reportlab not available
        return Response(
            content=generate_html_invoice(invoice, company, branch),
            media_type="text/html"
        )
    
    # Generate PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20*mm, bottomMargin=20*mm)
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER))
    styles.add(ParagraphStyle(name='Right', alignment=TA_RIGHT))
    styles.add(ParagraphStyle(name='CompanyName', fontSize=16, fontName='Helvetica-Bold', alignment=TA_CENTER))
    styles.add(ParagraphStyle(name='InvoiceTitle', fontSize=12, fontName='Helvetica-Bold', alignment=TA_CENTER))
    
    elements = []
    
    # Company Header
    elements.append(Paragraph(company.get("name", "HOOREN FOOD PRODUCTS"), styles['CompanyName']))
    elements.append(Paragraph(company.get("address", ""), styles['Center']))
    elements.append(Paragraph(f"GSTIN: {company.get('gstin', '')} | State: {company.get('state', '')} ({company.get('state_code', '')})", styles['Center']))
    if company.get("phone"):
        elements.append(Paragraph(f"Phone: {company.get('phone')} | Email: {company.get('email', '')}", styles['Center']))
    elements.append(Spacer(1, 10*mm))
    
    # Invoice Title
    invoice_type = "TAX INVOICE" if invoice.get("is_gst") else "INVOICE"
    elements.append(Paragraph(invoice_type, styles['InvoiceTitle']))
    elements.append(Spacer(1, 5*mm))
    
    # Invoice Details Table
    invoice_info = [
        ["Invoice No:", invoice.get("invoice_number", ""), "Date:", invoice.get("invoice_date", "")],
        ["Place of Supply:", invoice.get("place_of_supply", company.get("state", "")), "State Code:", invoice.get("state_code", company.get("state_code", ""))],
    ]
    
    t = Table(invoice_info, colWidths=[80, 150, 80, 150])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 5*mm))
    
    # Customer Details
    customer_info = [
        ["Bill To:"],
        [invoice.get("customer_name", "")],
        [invoice.get("customer_address", "")],
        [f"GSTIN: {invoice.get('customer_gstin', 'N/A')}"],
        [f"State: {invoice.get('customer_state', '')} ({invoice.get('customer_state_code', '')})"]
    ]
    
    t = Table(customer_info, colWidths=[460])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (0, 0), colors.lightgrey),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 5*mm))
    
    # Items Table
    items_header = ["#", "Description", "HSN", "Qty", "Rate", "Disc%", "Taxable", "GST%", "Amount"]
    items_data = [items_header]
    
    for idx, item in enumerate(invoice.get("items", []), 1):
        qty = item.get("quantity", 0)
        rate = item.get("rate", 0)
        disc = item.get("discount_percent", 0)
        taxable = qty * rate * (1 - disc/100)
        gst = item.get("gst_rate", 0)
        amount = taxable * (1 + gst/100)
        
        items_data.append([
            str(idx),
            item.get("item_name", ""),
            item.get("hsn_code", ""),
            f"{qty:.2f}",
            f"{rate:.2f}",
            f"{disc:.1f}%",
            f"{taxable:.2f}",
            f"{gst:.0f}%",
            f"{amount:.2f}"
        ])
    
    t = Table(items_data, colWidths=[25, 140, 50, 40, 50, 35, 55, 35, 55])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 3*mm))
    
    # Totals
    totals_data = [
        ["Subtotal:", f"Rs. {invoice.get('subtotal', 0):.2f}"],
        ["Discount:", f"Rs. {invoice.get('discount_amount', 0):.2f}"],
        ["Taxable Amount:", f"Rs. {invoice.get('taxable_amount', 0):.2f}"],
    ]
    
    if invoice.get("is_igst"):
        totals_data.append(["IGST:", f"Rs. {invoice.get('igst_amount', 0):.2f}"])
    else:
        totals_data.append(["CGST:", f"Rs. {invoice.get('cgst_amount', 0):.2f}"])
        totals_data.append(["SGST:", f"Rs. {invoice.get('sgst_amount', 0):.2f}"])
    
    if invoice.get("cess_amount", 0) > 0:
        totals_data.append(["CESS:", f"Rs. {invoice.get('cess_amount', 0):.2f}"])
    
    if invoice.get("round_off", 0) != 0:
        totals_data.append(["Round Off:", f"Rs. {invoice.get('round_off', 0):.2f}"])
    
    totals_data.append(["Grand Total:", f"Rs. {invoice.get('grand_total', 0):.2f}"])
    
    t = Table(totals_data, colWidths=[360, 100])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (-1, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 5*mm))
    
    # Amount in words
    elements.append(Paragraph(f"<b>Amount in Words:</b> {number_to_words(invoice.get('grand_total', 0))} Only", styles['Normal']))
    elements.append(Spacer(1, 5*mm))
    
    # QR Code
    if include_qr:
        qr_data = generate_gst_qr_data(invoice, company)
        qr_bytes = generate_qr_code(qr_data)
        qr_image = Image(io.BytesIO(qr_bytes), width=60, height=60)
        
        # Bank details and QR
        bank_qr_data = [
            ["Bank Details:", "", "Scan to Pay:"],
            [f"Bank: {company.get('bank_name', 'State Bank of India')}", "", ""],
            [f"A/C: {company.get('bank_account', '')}", "", ""],
            [f"IFSC: {company.get('bank_ifsc', '')}", "", ""],
        ]
        
        t = Table(bank_qr_data, colWidths=[200, 160, 100])
        t.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, 0), 'Helvetica-Bold'),
        ]))
        elements.append(t)
    
    elements.append(Spacer(1, 10*mm))
    
    # Signature
    sig_data = [
        ["Terms & Conditions:", "", f"For {company.get('name', 'HOOREN FOOD PRODUCTS')}"],
        ["1. Goods once sold will not be taken back", "", ""],
        ["2. Subject to Gujarat Jurisdiction", "", ""],
        ["", "", "Authorized Signatory"],
    ]
    
    t = Table(sig_data, colWidths=[250, 60, 150])
    t.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, 0), 'Helvetica-Bold'),
        ('ALIGN', (2, 0), (2, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(t)
    
    # Build PDF
    doc.build(elements)
    
    buffer.seek(0)
    return Response(
        content=buffer.getvalue(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=Invoice_{invoice.get('invoice_number', '')}.pdf"
        }
    )


def generate_html_invoice(invoice: dict, company: dict, branch: dict) -> str:
    """Generate HTML invoice as fallback"""
    
    items_html = ""
    for idx, item in enumerate(invoice.get("items", []), 1):
        qty = item.get("quantity", 0)
        rate = item.get("rate", 0)
        disc = item.get("discount_percent", 0)
        taxable = qty * rate * (1 - disc/100)
        gst = item.get("gst_rate", 0)
        amount = taxable * (1 + gst/100)
        
        items_html += f"""
        <tr>
            <td>{idx}</td>
            <td>{item.get("item_name", "")}</td>
            <td>{item.get("hsn_code", "")}</td>
            <td class="right">{qty:.2f}</td>
            <td class="right">{rate:.2f}</td>
            <td class="right">{disc:.1f}%</td>
            <td class="right">{gst:.0f}%</td>
            <td class="right">{amount:.2f}</td>
        </tr>
        """
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; font-size: 12px; margin: 20px; }}
            .header {{ text-align: center; margin-bottom: 20px; }}
            .company-name {{ font-size: 18px; font-weight: bold; }}
            .invoice-title {{ font-size: 14px; font-weight: bold; margin: 10px 0; border: 1px solid #000; padding: 5px; display: inline-block; }}
            table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
            th, td {{ border: 1px solid #000; padding: 5px; text-align: left; }}
            th {{ background-color: #f0f0f0; }}
            .right {{ text-align: right; }}
            .totals {{ width: 300px; margin-left: auto; }}
            .totals td {{ border: none; }}
            .grand-total {{ font-weight: bold; border-top: 2px solid #000 !important; }}
            .footer {{ margin-top: 30px; }}
            .signature {{ text-align: right; margin-top: 50px; }}
            @media print {{ body {{ margin: 0; }} }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="company-name">{company.get("name", "HOOREN FOOD PRODUCTS")}</div>
            <div>{company.get("address", "")}</div>
            <div>GSTIN: {company.get("gstin", "")} | State: {company.get("state", "")} ({company.get("state_code", "")})</div>
            <div class="invoice-title">TAX INVOICE</div>
        </div>
        
        <table style="border: none;">
            <tr style="border: none;">
                <td style="border: none; width: 50%;"><strong>Invoice No:</strong> {invoice.get("invoice_number", "")}</td>
                <td style="border: none; width: 50%; text-align: right;"><strong>Date:</strong> {invoice.get("invoice_date", "")}</td>
            </tr>
        </table>
        
        <table>
            <tr>
                <th colspan="2">Bill To</th>
            </tr>
            <tr>
                <td><strong>{invoice.get("customer_name", "")}</strong></td>
                <td>GSTIN: {invoice.get("customer_gstin", "N/A")}</td>
            </tr>
            <tr>
                <td>{invoice.get("customer_address", "")}</td>
                <td>State: {invoice.get("customer_state", "")} ({invoice.get("customer_state_code", "")})</td>
            </tr>
        </table>
        
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>Description</th>
                    <th>HSN</th>
                    <th class="right">Qty</th>
                    <th class="right">Rate</th>
                    <th class="right">Disc%</th>
                    <th class="right">GST%</th>
                    <th class="right">Amount</th>
                </tr>
            </thead>
            <tbody>
                {items_html}
            </tbody>
        </table>
        
        <table class="totals">
            <tr><td>Subtotal:</td><td class="right">Rs. {invoice.get("subtotal", 0):.2f}</td></tr>
            <tr><td>Discount:</td><td class="right">Rs. {invoice.get("discount_amount", 0):.2f}</td></tr>
            <tr><td>Taxable Amount:</td><td class="right">Rs. {invoice.get("taxable_amount", 0):.2f}</td></tr>
            <tr><td>CGST:</td><td class="right">Rs. {invoice.get("cgst_amount", 0):.2f}</td></tr>
            <tr><td>SGST:</td><td class="right">Rs. {invoice.get("sgst_amount", 0):.2f}</td></tr>
            <tr class="grand-total"><td>Grand Total:</td><td class="right">Rs. {invoice.get("grand_total", 0):.2f}</td></tr>
        </table>
        
        <p><strong>Amount in Words:</strong> {number_to_words(invoice.get("grand_total", 0))} Only</p>
        
        <div class="footer">
            <p><strong>Terms & Conditions:</strong></p>
            <p>1. Goods once sold will not be taken back</p>
            <p>2. Subject to Gujarat Jurisdiction</p>
        </div>
        
        <div class="signature">
            <p>For {company.get("name", "HOOREN FOOD PRODUCTS")}</p>
            <br><br>
            <p>Authorized Signatory</p>
        </div>
    </body>
    </html>
    """
    
    return html


def number_to_words(num: float) -> str:
    """Convert number to words (Indian format)"""
    ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
            "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
            "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
    
    if num == 0:
        return "Zero Rupees"
    
    num = round(num, 2)
    rupees = int(num)
    paise = int(round((num - rupees) * 100))
    
    def convert_less_than_thousand(n):
        if n == 0:
            return ""
        elif n < 20:
            return ones[n]
        elif n < 100:
            return tens[n // 10] + (" " + ones[n % 10] if n % 10 else "")
        else:
            return ones[n // 100] + " Hundred" + (" " + convert_less_than_thousand(n % 100) if n % 100 else "")
    
    def convert_indian(n):
        if n == 0:
            return ""
        
        result = ""
        
        # Crores
        if n >= 10000000:
            result += convert_less_than_thousand(n // 10000000) + " Crore "
            n %= 10000000
        
        # Lakhs
        if n >= 100000:
            result += convert_less_than_thousand(n // 100000) + " Lakh "
            n %= 100000
        
        # Thousands
        if n >= 1000:
            result += convert_less_than_thousand(n // 1000) + " Thousand "
            n %= 1000
        
        # Hundreds
        if n > 0:
            result += convert_less_than_thousand(n)
        
        return result.strip()
    
    result = convert_indian(rupees) + " Rupees"
    
    if paise > 0:
        result += " and " + convert_less_than_thousand(paise) + " Paise"
    
    return result


@router.get("/report/trial-balance")
async def generate_trial_balance_pdf(
    as_on_date: Optional[str] = None,
    branch_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Generate Trial Balance PDF"""
    
    from services.accounting_service import calculate_trial_balance
    
    data = await calculate_trial_balance(db, branch_id, as_on_date)
    
    company = await db.company_settings.find_one({}, {"_id": 0})
    if not company:
        company = {"name": "HOOREN FOOD PRODUCTS", "address": "Survey No 409, Ranuj, Patan, Gujarat"}
    
    # Generate HTML for simplicity
    items_html = ""
    for item in data.get("items", []):
        if item["debit"] > 0 or item["credit"] > 0:
            items_html += f"""
            <tr>
                <td>{item["ledger_name"]}</td>
                <td>{item["group_name"]}</td>
                <td class="right">{item["debit"]:.2f}</td>
                <td class="right">{item["credit"]:.2f}</td>
            </tr>
            """
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; font-size: 11px; margin: 20px; }}
            .header {{ text-align: center; margin-bottom: 20px; }}
            .company-name {{ font-size: 16px; font-weight: bold; }}
            .report-title {{ font-size: 14px; font-weight: bold; margin: 10px 0; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ border: 1px solid #000; padding: 4px; }}
            th {{ background-color: #f0f0f0; }}
            .right {{ text-align: right; }}
            .total-row {{ font-weight: bold; background-color: #e0e0e0; }}
            .balanced {{ color: green; }}
            .unbalanced {{ color: red; }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="company-name">{company.get("name", "HOOREN FOOD PRODUCTS")}</div>
            <div class="report-title">TRIAL BALANCE</div>
            <div>As on: {data.get("as_on_date", "")}</div>
        </div>
        
        <table>
            <thead>
                <tr>
                    <th>Particulars</th>
                    <th>Account Group</th>
                    <th class="right">Debit (Dr)</th>
                    <th class="right">Credit (Cr)</th>
                </tr>
            </thead>
            <tbody>
                {items_html}
            </tbody>
            <tfoot>
                <tr class="total-row">
                    <td colspan="2">TOTAL</td>
                    <td class="right">{data.get("total_debit", 0):.2f}</td>
                    <td class="right">{data.get("total_credit", 0):.2f}</td>
                </tr>
            </tfoot>
        </table>
        
        <p class="{'balanced' if data.get('is_balanced') else 'unbalanced'}">
            Status: {'BALANCED' if data.get('is_balanced') else f'NOT BALANCED (Difference: {data.get("difference", 0):.2f})'}
        </p>
    </body>
    </html>
    """
    
    return Response(content=html, media_type="text/html")
