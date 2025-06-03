from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'categories', views.CategoryViewSet, basename='category')
router.register(r'tasks', views.TaskViewSet, basename='task')
router.register(r'task-categories', views.TaskCategoryViewSet, basename='task-category')
router.register(r'badges', views.BadgeViewSet, basename='badge')
router.register(r'user-badges', views.UserBadgeViewSet, basename='user-badge')
router.register(r'streaks', views.StreakViewSet, basename='streak')
router.register(r'shared-plans', views.SharedPlanViewSet, basename='shared-plan')
router.register(r'shared-plan-tasks', views.SharedPlanTaskViewSet, basename='shared-plan-task')
router.register(r'calendar-sync', views.CalendarSyncViewSet, basename='calendar-sync')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/login/', views.login_view, name='login'),
    path('auth/logout/', views.logout_view, name='logout'),
    path('auth/register/', views.register_view, name='register'),
    path('auth/refresh/', views.refresh_token_view, name='refresh_token'),
    path('auth/user/', views.get_current_user, name='current_user'),
] 