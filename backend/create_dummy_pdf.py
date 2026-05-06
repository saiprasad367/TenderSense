from reportlab.pdfgen import canvas

c = canvas.Canvas("dummy.pdf")
c.drawString(100, 750, "Tender Title: Test")
c.drawString(100, 730, "Eligibility: 100 Crore")
c.save()
