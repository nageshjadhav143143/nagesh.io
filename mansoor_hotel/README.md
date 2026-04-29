# 🏨 Golden Crown Hotel - Hotel Management System

## Quick Start

### 1. Install Requirements
```bash
pip install django pillow qrcode reportlab
```

### 2. Run Migrations
```bash
python manage.py migrate
```

### 3. Create Admin User (already done)
```bash
python manage.py createsuperuser
```
**Default Credentials:** `admin` / `admin123`

### 4. Start the Server
```bash
python manage.py runserver
```

---

## 🌐 URLs

| Page | URL |
|------|-----|
| **Home** | http://localhost:8000/ |
| **Menu** | http://localhost:8000/menu/ |
| **Order** | http://localhost:8000/order/ |
| **Contact** | http://localhost:8000/contact/ |
| **Admin Dashboard** | http://localhost:8000/admin-panel/dashboard/ |
| **Admin Login** | http://localhost:8000/admin-panel/login/ |

---

## ✨ Features

- 🏠 **Professional Website** - Home, Menu, Order, Contact pages
- 🛒 **Online Ordering** - Cart system with quantity controls
- 📱 **QR Code Payment** - Auto-generated UPI QR code for payments
- 📄 **PDF Bill Generation** - Professional tax invoice download
- ✉️ **Email Confirmation** - Thank you email sent on order placement
- 🎛️ **Admin Dashboard** - Full management panel with:
  - Add/Remove menu categories
  - Add/Remove menu items (with images)
  - Toggle item availability
  - Order status management
  - Table management
  - Customer messages

---

## 📧 Email Configuration (for production)
Edit `hotel_project/settings.py`:
```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
```

## 🔑 Admin Login
- **Username:** admin
- **Password:** admin123

