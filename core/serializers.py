from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from .models import (
    Category, Task, TaskCategory, Badge, UserBadge,
    Streak, SharedPlan, SharedPlanMember, SharedPlanTask,
    CalendarSync
)

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')
        read_only_fields = ('id',)

class AuthTokenSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(style={'input_type': 'password'}, trim_whitespace=False)

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            user = authenticate(request=self.context.get('request'),
                              username=username, password=password)

            if not user:
                msg = 'Unable to log in with provided credentials.'
                raise serializers.ValidationError(msg, code='authorization')
        else:
            msg = 'Must include "username" and "password".'
            raise serializers.ValidationError(msg, code='authorization')

        attrs['user'] = user
        return attrs

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name', 'color_hex', 'created_at')
        read_only_fields = ('id', 'created_at')

class TaskSerializer(serializers.ModelSerializer):
    categories = CategorySerializer(many=True, read_only=True)
    subtasks = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = (
            'id', 'title', 'description', 'due_date', 'is_all_day',
            'priority', 'status', 'parent_task', 'categories',
            'subtasks', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_subtasks(self, obj):
        subtasks = Task.objects.filter(parent_task=obj)
        return TaskSerializer(subtasks, many=True).data

class TaskCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskCategory
        fields = ('id', 'task', 'category', 'created_at')
        read_only_fields = ('id', 'created_at')

class BadgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Badge
        fields = ('id', 'code', 'name', 'description', 'icon_url')
        read_only_fields = ('id',)

class UserBadgeSerializer(serializers.ModelSerializer):
    badge = BadgeSerializer(read_only=True)

    class Meta:
        model = UserBadge
        fields = ('id', 'badge', 'awarded_at')
        read_only_fields = ('id', 'awarded_at')

class StreakSerializer(serializers.ModelSerializer):
    class Meta:
        model = Streak
        fields = ('id', 'date', 'tasks_completed', 'is_completed_day')
        read_only_fields = ('id',)

class SharedPlanMemberSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = SharedPlanMember
        fields = ('id', 'user', 'permission', 'invited_at')
        read_only_fields = ('id', 'invited_at')

class SharedPlanSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    members = SharedPlanMemberSerializer(source='sharedplanmember_set', many=True, read_only=True)

    class Meta:
        model = SharedPlan
        fields = ('id', 'name', 'owner', 'members', 'created_at')
        read_only_fields = ('id', 'created_at')

class SharedPlanTaskSerializer(serializers.ModelSerializer):
    task = TaskSerializer(read_only=True)

    class Meta:
        model = SharedPlanTask
        fields = ('id', 'task', 'created_at')
        read_only_fields = ('id', 'created_at')

class CalendarSyncSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalendarSync
        fields = ('id', 'provider', 'provider_user_id', 'synced_at')
        read_only_fields = ('id', 'synced_at') 