from django.urls import path
from . import views

urlpatterns = [
    # Public
    path('', views.home, name='home'),
    path('menu/', views.menu_page, name='menu'),
    path('order/', views.order_page, name='order'),
    path('place-order/', views.place_order, name='place_order'),
    path('order-confirmation/<str:order_id>/', views.order_confirmation, name='order_confirmation'),
    path('download-bill/<str:order_id>/', views.download_bill, name='download_bill'),
    path('contact/', views.contact_page, name='contact'),
    # Admin Panel
    path('admin-panel/login/', views.admin_login, name='admin_login'),
    path('admin-panel/logout/', views.admin_logout, name='admin_logout'),
    path('admin-panel/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/menu/', views.admin_menu, name='admin_menu'),
    path('admin-panel/menu/add-category/', views.add_category, name='add_category'),
    path('admin-panel/menu/delete-category/<int:cat_id>/', views.delete_category, name='delete_category'),
    path('admin-panel/menu/add-item/', views.add_menu_item, name='add_menu_item'),
    path('admin-panel/menu/delete-item/<int:item_id>/', views.delete_menu_item, name='delete_menu_item'),
    path('admin-panel/menu/toggle/<int:item_id>/', views.toggle_item_availability, name='toggle_availability'),
    path('admin-panel/orders/', views.admin_orders, name='admin_orders'),
    path('admin-panel/orders/update/<str:order_id>/', views.update_order_status, name='update_order_status'),
    path('admin-panel/tables/', views.admin_tables, name='admin_tables'),
    path('admin-panel/tables/add/', views.add_table, name='add_table'),
    path('admin-panel/tables/delete/<int:table_id>/', views.delete_table, name='delete_table'),
    path('admin-panel/messages/', views.admin_messages, name='admin_messages'),
]
