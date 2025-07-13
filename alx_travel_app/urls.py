# alx_travel_app_0x01/urls.py (Main project URLs)
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from rest_framework.authtoken.views import obtain_auth_token
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Swagger/OpenAPI configuration
schema_view = get_schema_view(
    openapi.Info(
        title="Airbnb Clone API",
        default_version='v1',
        description="""
        A comprehensive API for managing property listings and bookings.
        
        ## Features
        - User authentication with custom user model
        - Property/Listing management with advanced filtering
        - Booking system with status management
        - Review and rating system
        - Messaging between users
        - Notification system
        - Payment tracking
        
        ## Authentication
        Use Token authentication by including `Authorization: Token <your_token>` in headers.
        Get your token by POSTing to `/api/auth/token/` with email and password.
        """,
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@airbnbclone.local"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny,],
)

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # API endpoints
    path('api/', include('listings.urls')),
    path('api/auth/', include('rest_framework.urls')),
    path('api/auth/token/', obtain_auth_token, name='api_token_auth'),
    
    # API Documentation
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('swagger.json', schema_view.without_ui(cache_timeout=0), name='schema-json'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
