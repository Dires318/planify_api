from django.shortcuts import render
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from django.db.models import Q
from django.contrib.auth import logout, get_user_model, authenticate
from django.conf import settings
from .models import (
    Category, Task, TaskCategory, Badge, UserBadge,
    Streak, SharedPlan, SharedPlanMember, SharedPlanTask,
    CalendarSync
)
from .serializers import (
    CategorySerializer, TaskSerializer, TaskCategorySerializer,
    BadgeSerializer, UserBadgeSerializer, StreakSerializer,
    SharedPlanSerializer, SharedPlanMemberSerializer,
    SharedPlanTaskSerializer, CalendarSyncSerializer,
    UserSerializer, AuthTokenSerializer
)
from django.views.decorators.csrf import ensure_csrf_cookie
from datetime import datetime, timedelta

User = get_user_model()

def set_auth_cookies(response, access_token, refresh_token):
    """Helper function to set auth cookies"""
    # Set access token cookie
    response.set_cookie(
        'access_token',
        str(access_token),
        expires=datetime.now() + timedelta(minutes=settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].minutes),
        secure=settings.SIMPLE_JWT['AUTH_COOKIE_SECURE'],
        httponly=settings.SIMPLE_JWT['AUTH_COOKIE_HTTP_ONLY'],
        samesite=settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE'],
        path=settings.SIMPLE_JWT['AUTH_COOKIE_PATH']
    )
    
    # Set refresh token cookie
    response.set_cookie(
        'refresh_token',
        str(refresh_token),
        expires=datetime.now() + timedelta(days=settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].days),
        secure=settings.SIMPLE_JWT['AUTH_COOKIE_SECURE'],
        httponly=settings.SIMPLE_JWT['AUTH_COOKIE_HTTP_ONLY'],
        samesite=settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE'],
        path=settings.SIMPLE_JWT['AUTH_COOKIE_PATH']
    )

def unset_auth_cookies(response):
    """Helper function to unset auth cookies"""
    response.delete_cookie('access_token')
    response.delete_cookie('refresh_token')

# Create your views here.

class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Task.objects.filter(
            Q(user=self.request.user) |
            Q(sharedplantask__shared_plan__members=self.request.user)
        ).distinct()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        task = self.get_object()
        task.status = 'completed'
        task.save()

        # Update streak
        today = timezone.now().date()
        streak, created = Streak.objects.get_or_create(
            user=request.user,
            date=today,
            defaults={'tasks_completed': 0, 'is_completed_day': False}
        )
        streak.tasks_completed += 1
        streak.is_completed_day = True
        streak.save()

        return Response({'status': 'task completed'})

    @action(detail=True, methods=['post'])
    def snooze(self, request, pk=None):
        task = self.get_object()
        task.status = 'snoozed'
        task.save()
        return Response({'status': 'task snoozed'})

class TaskCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = TaskCategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TaskCategory.objects.filter(task__user=self.request.user)

class BadgeViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BadgeSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Badge.objects.all()

class UserBadgeViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserBadgeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserBadge.objects.filter(user=self.request.user)

class StreakViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = StreakSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Streak.objects.filter(user=self.request.user)

class SharedPlanViewSet(viewsets.ModelViewSet):
    serializer_class = SharedPlanSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SharedPlan.objects.filter(
            Q(owner=self.request.user) |
            Q(members=self.request.user)
        ).distinct()

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['post'])
    def add_member(self, request, pk=None):
        shared_plan = self.get_object()
        if shared_plan.owner != request.user:
            return Response(
                {'error': 'Only the owner can add members'},
                status=status.HTTP_403_FORBIDDEN
            )

        user_id = request.data.get('user_id')
        permission = request.data.get('permission', 'view')

        try:
            member = SharedPlanMember.objects.create(
                shared_plan=shared_plan,
                user_id=user_id,
                permission=permission
            )
            return Response(SharedPlanMemberSerializer(member).data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

class SharedPlanTaskViewSet(viewsets.ModelViewSet):
    serializer_class = SharedPlanTaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SharedPlanTask.objects.filter(
            shared_plan__members=self.request.user
        )

class CalendarSyncViewSet(viewsets.ModelViewSet):
    serializer_class = CalendarSyncSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CalendarSync.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

@api_view(['POST'])
@permission_classes([AllowAny])  # Allow unauthenticated access
@ensure_csrf_cookie
def login_view(request):
    username = request.data.get('username')
    password = request.data.get('password')
    
    if not username or not password:
        return Response(
            {'detail': 'Please provide both username and password.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = authenticate(username=username, password=password)
    
    if user is None:
        return Response(
            {'detail': 'Invalid credentials.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    refresh = RefreshToken.for_user(user)
    response = Response({
        'detail': 'Successfully logged in.',
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name
        }
    })
    
    # Set access token cookie
    response.set_cookie(
        'access_token',
        str(refresh.access_token),
        expires=datetime.now() + settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'],
        secure=settings.SIMPLE_JWT['AUTH_COOKIE_SECURE'],
        httponly=settings.SIMPLE_JWT['AUTH_COOKIE_HTTP_ONLY'],
        samesite=settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE'],
        path=settings.SIMPLE_JWT['AUTH_COOKIE_PATH'],
        domain=None  # Allow cookies to work on localhost
    )
    
    # Set refresh token cookie
    response.set_cookie(
        'refresh_token',
        str(refresh),
        expires=datetime.now() + settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'],
        secure=settings.SIMPLE_JWT['AUTH_COOKIE_SECURE'],
        httponly=settings.SIMPLE_JWT['AUTH_COOKIE_HTTP_ONLY'],
        samesite=settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE'],
        path=settings.SIMPLE_JWT['AUTH_COOKIE_PATH'],
        domain=None  # Allow cookies to work on localhost
    )
    
    # Set CSRF token cookie
    response.set_cookie(
        'csrftoken',
        request.META.get('CSRF_COOKIE', ''),
        secure=settings.SIMPLE_JWT['AUTH_COOKIE_SECURE'],
        httponly=False,  # CSRF token needs to be accessible by JavaScript
        samesite=settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE'],
        path=settings.SIMPLE_JWT['AUTH_COOKIE_PATH'],
        domain=None  # Allow cookies to work on localhost
    )
    
    return response

@api_view(['POST'])
@ensure_csrf_cookie
@permission_classes([AllowAny])
def logout_view(request):
    refresh_token = request.COOKIES.get('refresh_token')
    if refresh_token:
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            response = Response({'detail': 'Successfully logged out.'})
            unset_auth_cookies(response)
            return response
        except Exception as e:
            print(e)
            return Response(
                {'detail': 'Error during logout.'},
                status=status.HTTP_400_BAD_REQUEST
            )
    else:
        return Response(
            {'detail': 'No refresh token found.'},
            status=status.HTTP_200_OK
        )

@api_view(['POST'])
@permission_classes([AllowAny])  # Allow unauthenticated access
@ensure_csrf_cookie
def register_view(request):
    username = request.data.get('username')
    password = request.data.get('password')
    email = request.data.get('email')
    first_name = request.data.get('first_name')
    last_name = request.data.get('last_name')
    
    if not all([username, password, email]):
        return Response(
            {'detail': 'Please provide all required fields.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if User.objects.filter(username=username).exists():
        return Response(
            {'detail': 'Username already exists.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if User.objects.filter(email=email).exists():
        return Response(
            {'detail': 'Email already exists.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=first_name or '',
        last_name=last_name or ''
    )
    
    refresh = RefreshToken.for_user(user)
    response = Response({
        'detail': 'Successfully registered.',
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name
        }
    })
    
    # Set cookies with proper configuration
    response.set_cookie(
        'access_token',
        str(refresh.access_token),
        expires=datetime.now() + settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'],
        secure=settings.SIMPLE_JWT['AUTH_COOKIE_SECURE'],
        httponly=settings.SIMPLE_JWT['AUTH_COOKIE_HTTP_ONLY'],
        samesite=settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE'],
        path=settings.SIMPLE_JWT['AUTH_COOKIE_PATH'],
        domain=None  # Allow cookies to work on localhost
    )
    
    response.set_cookie(
        'refresh_token',
        str(refresh),
        expires=datetime.now() + settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'],
        secure=settings.SIMPLE_JWT['AUTH_COOKIE_SECURE'],
        httponly=settings.SIMPLE_JWT['AUTH_COOKIE_HTTP_ONLY'],
        samesite=settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE'],
        path=settings.SIMPLE_JWT['AUTH_COOKIE_PATH'],
        domain=None  # Allow cookies to work on localhost
    )
    
    return response

@api_view(['POST'])
@permission_classes([AllowAny])  # Allow unauthenticated access
@ensure_csrf_cookie
def refresh_token_view(request):
    try:
        refresh_token = request.COOKIES.get('refresh_token')
        if not refresh_token:
            return Response(
                {'detail': 'No refresh token found.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        token = RefreshToken(refresh_token)
        response = Response({'detail': 'Token refreshed successfully.'})
        
        # Set cookies with proper configuration
        response.set_cookie(
            'access_token',
            str(token.access_token),
            expires=datetime.now() + settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'],
            secure=settings.SIMPLE_JWT['AUTH_COOKIE_SECURE'],
            httponly=settings.SIMPLE_JWT['AUTH_COOKIE_HTTP_ONLY'],
            samesite=settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE'],
            path=settings.SIMPLE_JWT['AUTH_COOKIE_PATH'],
            domain=None  # Allow cookies to work on localhost
        )
        
        response.set_cookie(
            'refresh_token',
            str(token),
            expires=datetime.now() + settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'],
            secure=settings.SIMPLE_JWT['AUTH_COOKIE_SECURE'],
            httponly=settings.SIMPLE_JWT['AUTH_COOKIE_HTTP_ONLY'],
            samesite=settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE'],
            path=settings.SIMPLE_JWT['AUTH_COOKIE_PATH'],
            domain=None  # Allow cookies to work on localhost
        )
        
        return response
    except Exception as e:
        return Response(
            {'detail': 'Invalid refresh token.'},
            status=status.HTTP_401_UNAUTHORIZED
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_user(request):
    """Get the current authenticated user's information"""
    user = request.user
    return Response({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'date_joined': user.date_joined,
        'last_login': user.last_login
    })
