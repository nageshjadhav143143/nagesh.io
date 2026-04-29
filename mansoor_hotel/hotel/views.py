from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import Category, MenuItem, Order, OrderItem, Table, ContactMessage
import json
import qrcode
import io
import base64
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table as RLTable, TableStyle, Spacer, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
import datetime

def is_admin(user):
    return user.is_staff or user.is_superuser

# ─── PUBLIC VIEWS ───────────────────────────────────────────────────────────

def home(request):
    featured_items = MenuItem.objects.filter(is_featured=True, is_available=True)[:6]
    categories = Category.objects.filter(is_active=True)
    return render(request, 'hotel/home.html', {'featured_items': featured_items, 'categories': categories})

def menu_page(request):
    categories = Category.objects.filter(is_active=True).prefetch_related('items')
    category_id = request.GET.get('category')
    selected_category = None
    items = MenuItem.objects.filter(is_available=True)
    if category_id:
        selected_category = get_object_or_404(Category, id=category_id)
        items = items.filter(category=selected_category)
    return render(request, 'hotel/menu.html', {
        'categories': categories, 'items': items, 'selected_category': selected_category
    })

def order_page(request):
    categories = Category.objects.filter(is_active=True).prefetch_related('items')
    tables = Table.objects.filter(is_occupied=False)
    return render(request, 'hotel/order.html', {'categories': categories, 'tables': tables})

def place_order(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            customer_name = data.get('customer_name')
            customer_email = data.get('customer_email')
            customer_phone = data.get('customer_phone')
            table_id = data.get('table_id')
            payment_method = data.get('payment_method', 'cash')
            special_instructions = data.get('special_instructions', '')
            cart_items = data.get('cart_items', [])

            if not cart_items:
                return JsonResponse({'success': False, 'error': 'Cart is empty'})

            table = None
            if table_id:
                table = Table.objects.get(id=table_id)
                table.is_occupied = True
                table.save()

            order = Order.objects.create(
                customer_name=customer_name,
                customer_email=customer_email,
                customer_phone=customer_phone,
                table=table,
                payment_method=payment_method,
                special_instructions=special_instructions,
            )

            for item_data in cart_items:
                menu_item = MenuItem.objects.get(id=item_data['id'])
                OrderItem.objects.create(
                    order=order,
                    menu_item=menu_item,
                    quantity=item_data['quantity'],
                    price=menu_item.price,
                )

            order.calculate_total()

            # Send thank you email
            try:
                send_thank_you_email(order)
            except Exception as e:
                pass  # Email fails silently in demo

            return JsonResponse({
                'success': True,
                'order_id': order.order_id,
                'total': str(order.total),
                'redirect': f'/order-confirmation/{order.order_id}/'
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid method'})

def send_thank_you_email(order):
    subject = f'Thank You for Your Order! - {order.order_id}'
    items_list = '\n'.join([f"  • {item.quantity}x {item.menu_item.name} - ₹{item.subtotal}" for item in order.order_items.all()])
    message = f"""
Dear {order.customer_name},

🙏 Thank you for dining at Golden Crown Hotel!

Your order has been successfully placed.

Order Details:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Order ID: {order.order_id}
Date: {order.created_at.strftime('%d %B %Y, %I:%M %p')}

Items Ordered:
{items_list}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Subtotal:    ₹{order.subtotal}
GST (5%):    ₹{order.tax}
TOTAL:       ₹{order.total}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Payment Method: {order.get_payment_method_display()}

We hope you enjoy your meal! Your satisfaction is our priority.

With warm regards,
Golden Crown Hotel
📞 +91 98765 43210
📍 123 Hotel Street, City - 400001
    """
    send_mail(subject, message, 'goldencrownhotel@gmail.com', [order.customer_email])

def order_confirmation(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)
    # Generate QR code for payment
    qr_data = f"upi://pay?pa=goldencrownhotel@upi&pn=Golden Crown Hotel&am={order.total}&cu=INR&tn=Order {order.order_id}"
    qr = qrcode.QRCode(version=1, box_size=8, border=4)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1a1a2e", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    qr_code_b64 = base64.b64encode(buffer.getvalue()).decode()
    return render(request, 'hotel/order_confirmation.html', {'order': order, 'qr_code': qr_code_b64})

def download_bill(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Bill_{order.order_id}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    story = []

    # Header style
    header_style = ParagraphStyle('Header', parent=styles['Title'], fontSize=28, textColor=colors.HexColor('#C8960C'), alignment=TA_CENTER, spaceAfter=5)
    sub_style = ParagraphStyle('Sub', parent=styles['Normal'], fontSize=11, textColor=colors.HexColor('#666'), alignment=TA_CENTER, spaceAfter=3)
    bold_center = ParagraphStyle('BoldCenter', parent=styles['Normal'], fontSize=12, fontName='Helvetica-Bold', alignment=TA_CENTER)

    story.append(Paragraph("🏨 GOLDEN CROWN HOTEL", header_style))
    story.append(Paragraph("123 Hotel Street, City - 400001 | +91 98765 43210", sub_style))
    story.append(Paragraph("goldencrownhotel@gmail.com | www.goldencrownhotel.com", sub_style))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#C8960C')))
    story.append(Spacer(1, 10))
    story.append(Paragraph("TAX INVOICE", bold_center))
    story.append(Spacer(1, 10))

    # Order info table
    info_data = [
        ['Order ID:', order.order_id, 'Date:', order.created_at.strftime('%d/%m/%Y %I:%M %p')],
        ['Customer:', order.customer_name, 'Phone:', order.customer_phone],
        ['Email:', order.customer_email, 'Payment:', order.get_payment_method_display()],
    ]
    if order.table:
        info_data.append(['Table:', f"Table {order.table.number}", 'Status:', order.get_status_display()])

    info_table = RLTable(info_data, colWidths=[1.2*inch, 2.2*inch, 1.2*inch, 2.2*inch])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('TEXTCOLOR', (0,0), (0,-1), colors.HexColor('#C8960C')),
        ('TEXTCOLOR', (2,0), (2,-1), colors.HexColor('#C8960C')),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [colors.HexColor('#FFF9F0'), colors.white]),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 15))

    # Items table
    items_data = [['#', 'Item', 'Qty', 'Unit Price', 'Amount']]
    for i, item in enumerate(order.order_items.all(), 1):
        items_data.append([str(i), item.menu_item.name, str(item.quantity), f"₹{item.price}", f"₹{item.subtotal}"])

    items_table = RLTable(items_data, colWidths=[0.4*inch, 3.5*inch, 0.6*inch, 1.2*inch, 1.1*inch])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a1a2e')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#C8960C')),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('ALIGN', (2,0), (-1,-1), 'CENTER'),
        ('ALIGN', (3,0), (-1,-1), 'RIGHT'),
        ('ALIGN', (4,0), (-1,-1), 'RIGHT'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#FFF9F0')]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#ddd')),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 10))

    # Totals
    totals_data = [
        ['', '', 'Subtotal:', f"₹{order.subtotal}"],
        ['', '', 'GST (5%):', f"₹{order.tax}"],
        ['', '', 'TOTAL:', f"₹{order.total}"],
    ]
    totals_table = RLTable(totals_data, colWidths=[0.4*inch, 3.5*inch, 1.8*inch, 1.1*inch])
    totals_table.setStyle(TableStyle([
        ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 11),
        ('ALIGN', (2,0), (-1,-1), 'RIGHT'),
        ('BACKGROUND', (2,2), (3,2), colors.HexColor('#C8960C')),
        ('TEXTCOLOR', (2,2), (3,2), colors.white),
        ('FONTNAME', (2,2), (3,2), 'Helvetica-Bold'),
        ('FONTSIZE', (2,2), (3,2), 13),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(totals_table)
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#C8960C')))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Thank you for dining with us! We hope to serve you again soon. 🙏", ParagraphStyle('Thanks', parent=styles['Normal'], fontSize=12, alignment=TA_CENTER, textColor=colors.HexColor('#C8960C'), fontName='Helvetica-Bold')))
    story.append(Paragraph("GSTIN: 27AABCU9603R1ZV", ParagraphStyle('GSTIN', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER, textColor=colors.grey)))

    doc.build(story)
    return response

def contact_page(request):
    if request.method == 'POST':
        ContactMessage.objects.create(
            name=request.POST.get('name'),
            email=request.POST.get('email'),
            subject=request.POST.get('subject'),
            message=request.POST.get('message'),
        )
        messages.success(request, 'Your message has been sent! We will get back to you soon.')
        return redirect('contact')
    return render(request, 'hotel/contact.html')

# ─── ADMIN VIEWS ─────────────────────────────────────────────────────────────

def admin_login(request):
    if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
        return redirect('admin_dashboard')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user and (user.is_staff or user.is_superuser):
            login(request, user)
            return redirect('admin_dashboard')
        else:
            messages.error(request, 'Invalid credentials or insufficient permissions.')
    return render(request, 'admin_panel/login.html')

def admin_logout(request):
    logout(request)
    return redirect('admin_login')

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    today = timezone.now().date()
    total_orders = Order.objects.count()
    today_orders = Order.objects.filter(created_at__date=today).count()
    total_revenue = Order.objects.filter(payment_status='paid').aggregate(Sum('total'))['total__sum'] or 0
    today_revenue = Order.objects.filter(created_at__date=today, payment_status='paid').aggregate(Sum('total'))['total__sum'] or 0
    pending_orders = Order.objects.filter(status__in=['pending', 'confirmed', 'preparing']).count()
    total_items = MenuItem.objects.count()
    recent_orders = Order.objects.order_by('-created_at')[:5]
    unread_messages = ContactMessage.objects.filter(is_read=False).count()
    return render(request, 'admin_panel/dashboard.html', {
        'total_orders': total_orders, 'today_orders': today_orders,
        'total_revenue': total_revenue, 'today_revenue': today_revenue,
        'pending_orders': pending_orders, 'total_items': total_items,
        'recent_orders': recent_orders, 'unread_messages': unread_messages,
    })

@login_required
@user_passes_test(is_admin)
def admin_menu(request):
    categories = Category.objects.all().prefetch_related('items')
    items = MenuItem.objects.all().select_related('category').order_by('-created_at')
    return render(request, 'admin_panel/menu.html', {'categories': categories, 'items': items})

@login_required
@user_passes_test(is_admin)
def add_category(request):
    if request.method == 'POST':
        Category.objects.create(
            name=request.POST['name'],
            icon=request.POST.get('icon', '🍽️'),
            description=request.POST.get('description', ''),
        )
        messages.success(request, 'Category added successfully!')
    return redirect('admin_menu')

@login_required
@user_passes_test(is_admin)
def delete_category(request, cat_id):
    cat = get_object_or_404(Category, id=cat_id)
    cat.delete()
    messages.success(request, 'Category deleted!')
    return redirect('admin_menu')

@login_required
@user_passes_test(is_admin)
def add_menu_item(request):
    if request.method == 'POST':
        item = MenuItem.objects.create(
            category_id=request.POST['category'],
            name=request.POST['name'],
            description=request.POST.get('description', ''),
            price=request.POST['price'],
            is_veg=request.POST.get('is_veg') == 'on',
            is_featured=request.POST.get('is_featured') == 'on',
            is_available=request.POST.get('is_available') == 'on',
        )
        if 'image' in request.FILES:
            item.image = request.FILES['image']
            item.save()
        messages.success(request, 'Menu item added successfully!')
    return redirect('admin_menu')

@login_required
@user_passes_test(is_admin)
def delete_menu_item(request, item_id):
    item = get_object_or_404(MenuItem, id=item_id)
    item.delete()
    messages.success(request, 'Menu item deleted!')
    return redirect('admin_menu')

@login_required
@user_passes_test(is_admin)
def toggle_item_availability(request, item_id):
    item = get_object_or_404(MenuItem, id=item_id)
    item.is_available = not item.is_available
    item.save()
    return JsonResponse({'status': 'ok', 'available': item.is_available})

@login_required
@user_passes_test(is_admin)
def admin_orders(request):
    status_filter = request.GET.get('status', '')
    orders = Order.objects.all().order_by('-created_at')
    if status_filter:
        orders = orders.filter(status=status_filter)
    return render(request, 'admin_panel/orders.html', {'orders': orders, 'status_filter': status_filter, 'status_choices': Order.STATUS_CHOICES})

@login_required
@user_passes_test(is_admin)
def update_order_status(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)
    if request.method == 'POST':
        order.status = request.POST['status']
        order.payment_status = request.POST.get('payment_status', order.payment_status)
        order.save()
        if order.status == 'paid' or order.payment_status == 'paid':
            if order.table:
                order.table.is_occupied = False
                order.table.save()
        messages.success(request, f'Order {order.order_id} updated!')
    return redirect('admin_orders')

@login_required
@user_passes_test(is_admin)
def admin_tables(request):
    tables = Table.objects.all().order_by('number')
    return render(request, 'admin_panel/tables.html', {'tables': tables})

@login_required
@user_passes_test(is_admin)
def add_table(request):
    if request.method == 'POST':
        Table.objects.create(number=request.POST['number'], capacity=request.POST.get('capacity', 4))
        messages.success(request, 'Table added!')
    return redirect('admin_tables')

@login_required
@user_passes_test(is_admin)
def delete_table(request, table_id):
    table = get_object_or_404(Table, id=table_id)
    table.delete()
    messages.success(request, 'Table removed!')
    return redirect('admin_tables')

@login_required
@user_passes_test(is_admin)
def admin_messages(request):
    msgs = ContactMessage.objects.all().order_by('-created_at')
    ContactMessage.objects.filter(is_read=False).update(is_read=True)
    return render(request, 'admin_panel/messages.html', {'messages_list': msgs})
