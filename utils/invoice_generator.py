# utils/invoice_generator.py
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from django.conf import settings
import os
from datetime import datetime

class InvoiceGenerator:
    def __init__(self, order):
        self.order = order
        self.buffer = BytesIO()
        # Reduce margins to fit more content on one page
        self.doc = SimpleDocTemplate(
            self.buffer,
            pagesize=letter,
            rightMargin=36,    # Reduced from 72
            leftMargin=36,     # Reduced from 72
            topMargin=36,      # Reduced from 72
            bottomMargin=36,   # Reduced from 72
            title=f"Live Bakery Invoice {order.order_number}"  # Set PDF title
        )
        self.styles = getSampleStyleSheet()
        self.story = []
        
    def _add_header(self):
        from django.contrib.staticfiles import finders
        
        logo_path = finders.find('images/logo.png')
        
        # Prepare header content
        header_cells = []
        
        # Left cell: Logo and company info
        left_content = []
        if logo_path:
            try:
                # Reduce logo size to save space
                logo = Image(logo_path, width=1.0*inch, height=1.0*inch)
                left_content.append(logo)
            except Exception as e:
                print(f"Logo loading failed: {e}")
        
        # Add company details with smaller font
        company_info = [
            Paragraph("Live Bakery", ParagraphStyle(
                'CompanyName',
                parent=self.styles['Normal'],
                fontSize=10,
                textColor=colors.HexColor('#8f3232'),
                alignment=0
            )),
            Paragraph("Kamalbinayak, Bhaktapur", ParagraphStyle(
                'CompanyAddress',
                parent=self.styles['Normal'],
                fontSize=8,
                alignment=0
            )),
        ]
        
        for item in company_info:
            left_content.append(item)
        
        # Right cell: Invoice title and details with smaller font
        right_content = [
            Paragraph("INVOICE", ParagraphStyle(
                'InvoiceTitle',
                parent=self.styles['Heading1'],
                fontSize=22,  # Reduced from 28
                textColor=colors.HexColor('#8f3232'),
                alignment=2
            )),
            Paragraph(f"Invoice #: {self.order.order_number}", ParagraphStyle(
                'InvoiceDetails',
                parent=self.styles['Normal'],
                fontSize=9,  # Reduced from 10
                alignment=2
            )),
            Paragraph(f"Date: {datetime.now().strftime('%B %d, %Y')}", ParagraphStyle(
                'InvoiceDetails',
                parent=self.styles['Normal'],
                fontSize=9,
                alignment=2
            )),
        ]
        
        # Create table row
        header_data = [[left_content, right_content]]
        
        # Create table with appropriate column widths
        header_table = Table(header_data, colWidths=[2.5*inch, 3.5*inch])
        
        # Style the table
        header_style = TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('LEFTPADDING', (0, 0), (0, 0), 0),
            ('RIGHTPADDING', (1, 0), (1, 0), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),  # Reduced from 20
        ])
        
        header_table.setStyle(header_style)
        self.story.append(header_table)
        
        # Add separator line
        self.story.append(Spacer(1, 0.05*inch))
        line = Table([[""]], colWidths=[6*inch])
        line.setStyle(TableStyle([
            ('LINEBELOW', (0, 0), (0, 0), 1, colors.HexColor('#8f3232')),
        ]))
        self.story.append(line)
        self.story.append(Spacer(1, 0.15*inch))  # Further reduced from 0.2*inch

    def _add_customer_and_invoice_info(self):
        """Combine customer info and invoice details to save space"""
        
        # Get customer name
        customer_name = self.order.user.get_full_name() 
        if not customer_name or customer_name == '':
            customer_name = self.order.user.username
        
        # Create a table with 3 sections: Company, Customer, Invoice Details
        info_data = [
            ["BILL FROM:", "BILL TO:", "INVOICE DETAILS"],
            ["Live Bakery", f"{customer_name}", f"Invoice #: {self.order.order_number}"],
            ["Kamalbinayak, Bhaktapur", f"Phone: {self.order.phone_number}", f"Date: {datetime.now().strftime('%d/%m/%Y')}"],
            ["Phone: +977 9800000000", f"Email: {self.order.user.email}", f"Order Status: {self.order.get_status_display()}"],
            ["Email: orders@livebakery.com", f"Order Date: {self.order.created_at.strftime('%d/%m/%Y')}", f"Payment: {self.order.get_payment_method_display()}"],
        ]
        
        info_style = TableStyle([
            # Header row styling
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8f3232')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),  # Reduced from 10
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),  # Reduced from 8
            
            # Body styling
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),  # Reduced from 9
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),  # Reduced from 6
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),  # Reduced from 6
            ('TOPPADDING', (0, 0), (-1, -1), 3),  # Reduced from 4
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),  # Reduced from 4
        ])
        
        info_table = Table(info_data, colWidths=[1.9*inch, 1.9*inch, 2.2*inch])  # Adjusted widths
        info_table.setStyle(info_style)
        self.story.append(info_table)
        self.story.append(Spacer(1, 0.15*inch))  # Reduced from 0.2*inch
        
    def _add_order_items(self):
        """Add order items table with compact styling"""
        
        from django.apps import apps
        OrderItem = apps.get_model('orders', 'OrderItem')
        order_items = OrderItem.objects.filter(order=self.order)
        
        # Create table data
        items_data = [["Item", "Qty", "Unit Price", "Total"]]
        
        subtotal = 0
        
        for item in order_items:
            product_name = item.product.name
            if hasattr(item.product, 'is_cake') and item.product.is_cake and hasattr(item, 'cake_tiers') and item.cake_tiers:
                product_name += f" ({item.cake_tiers} tier)"
            
            item_total = item.get_total_price()
            subtotal += item_total
            
            # Truncate long product names if necessary
            if len(product_name) > 25:  # Reduced from 30
                product_name = product_name[:22] + "..."
            
            items_data.append([
                product_name,
                str(item.quantity),
                f"Rs. {item.price:.2f}",
                f"Rs. {item_total:.2f}"
            ])
        
        # Calculate delivery fee
        delivery_fee = 200 if self.order.delivery_type == 'delivery' else 0
        grand_total = subtotal + delivery_fee
        
        # Add summary rows with less spacing
        items_data.append(["", "", "Subtotal:", f"Rs. {subtotal:.2f}"])
        items_data.append(["", "", "Delivery Fee:", f"Rs. {delivery_fee:.2f}"])
        items_data.append(["", "", "TOTAL:", f"Rs. {grand_total:.2f}"])
        
        items_style = TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8f3232')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),  # Reduced from 10
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),  # Reduced from 8
            
            # Item rows
            ('FONTNAME', (0, 1), (-1, len(items_data)-4), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, len(items_data)-4), 8),  # Reduced from 9
            ('VALIGN', (0, 1), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, len(items_data)-4), 0.5, colors.grey),
            ('TOPPADDING', (0, 1), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 2),
            
            # Summary rows
            ('FONTNAME', (2, len(items_data)-3), (3, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (2, len(items_data)-3), (3, -1), 9),  # Reduced from 10
            ('ALIGN', (2, len(items_data)-3), (3, -1), 'RIGHT'),
            ('LINEABOVE', (2, len(items_data)-3), (3, len(items_data)-3), 0.5, colors.black),
            ('LINEABOVE', (2, -1), (3, -1), 1, colors.HexColor('#8f3232')),
            ('BACKGROUND', (2, -1), (3, -1), colors.HexColor('#f9fafb')),
        ])
        
        items_table = Table(items_data, colWidths=[2.8*inch, 0.4*inch, 1.2*inch, 1.2*inch])  # Adjusted widths
        items_table.setStyle(items_style)
        self.story.append(items_table)
        self.story.append(Spacer(1, 0.15*inch))  # Reduced from 0.2*inch
        
    def _add_delivery_info(self):
        """Add compact delivery information"""
        
        delivery_type_display = self.order.get_delivery_type_display()
        
        if self.order.delivery_type == 'delivery':
            delivery_info = f"<b>Delivery Information:</b><br/>Type: {delivery_type_display}<br/>Address: {self.order.delivery_address}<br/>Phone: {self.order.phone_number}"
        else:
            delivery_info = f"<b>Delivery Information:</b><br/>Type: {delivery_type_display}<br/>Phone: {self.order.phone_number}"
        
        if self.order.special_instructions:
            delivery_info += f"<br/>Special Instructions: {self.order.special_instructions}"
        
        delivery_paragraph = Paragraph(
            delivery_info,
            ParagraphStyle(
                'DeliveryInfo',
                parent=self.styles['Normal'],
                fontSize=8,  # Reduced from 9
                leading=10,  # Reduced from 11
                spaceBefore=6,  # Reduced from 8
                spaceAfter=6,  # Reduced from 8
                leftIndent=5,  # Reduced from 10
                textColor=colors.darkslategray
            )
        )
        
        self.story.append(delivery_paragraph)
        self.story.append(Spacer(1, 0.08*inch))  # Reduced from 0.1*inch
        
    def _add_footer(self):
        """Add compact footer with terms and thank you message"""
        
        # Combine terms and thank you in one paragraph
        footer_text = """
        <b>Terms & Conditions:</b><br/>
        1. All prices are in Nepali Rupees (Rs.)<br/>
        2. Goods once sold will not be taken back<br/>
        3. Delivery within 1-2 business days<br/>
        4. For any queries, contact: livebakery@gmail.com<br/>
        <br/>
        <i>Thank you for your order! We hope you enjoy our bakery products.</i>
        """
        
        footer_paragraph = Paragraph(
            footer_text,
            ParagraphStyle(
                'Footer',
                parent=self.styles['Normal'],
                fontSize=7,  # Reduced from 8
                leading=9,   # Reduced from 10
                alignment=0,  # Left aligned
                spaceBefore=8,  # Reduced from 10
                spaceAfter=5,   # Reduced from 10
                textColor=colors.darkslategray
            )
        )
        
        # Add a separator line
        self.story.append(Spacer(1, 0.03*inch))  # Reduced from 0.05*inch
        line = Table([[""]], colWidths=[6*inch])
        line.setStyle(TableStyle([
            ('LINEABOVE', (0, 0), (0, 0), 0.5, colors.grey),
        ]))
        self.story.append(line)
        self.story.append(Spacer(1, 0.03*inch))  # Reduced from 0.05*inch
        
        self.story.append(footer_paragraph)
        
    def generate(self):
        # Add all sections to the PDF in compact layout
        self._add_header()
        self._add_customer_and_invoice_info()  # Combined section
        self._add_order_items()
        self._add_delivery_info()
        self._add_footer()
        
        # Build PDF with proper metadata
        self.doc.build(self.story)
        
        # Get PDF value from buffer
        pdf = self.buffer.getvalue()
        self.buffer.close()
        return pdf