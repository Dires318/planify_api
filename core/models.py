from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Category(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    color_hex = models.CharField(max_length=7, default='#90A4AE')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Categories"
        unique_together = ('user', 'name')

    def __str__(self):
        return f"{self.name} ({self.user.username})"

class Task(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('snoozed', 'Snoozed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    due_date = models.DateTimeField(null=True, blank=True)
    is_all_day = models.BooleanField(default=False)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='normal')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    parent_task = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subtasks')
    categories = models.ManyToManyField(Category, through='TaskCategory')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.user.username})"

class TaskCategory(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Task Categories"
        unique_together = ('task', 'category')

class Badge(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField()
    icon_url = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class UserBadge(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    awarded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'badge')

class Streak(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    tasks_completed = models.IntegerField(default=0)
    is_completed_day = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'date')

    def __str__(self):
        return f"{self.user.username} - {self.date}"

class SharedPlan(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_plans')
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    members = models.ManyToManyField(User, through='SharedPlanMember', related_name='shared_plans')

    def __str__(self):
        return f"{self.name} (Owner: {self.owner.username})"

class SharedPlanMember(models.Model):
    PERMISSION_CHOICES = [
        ('view', 'View'),
        ('edit', 'Edit'),
    ]

    shared_plan = models.ForeignKey(SharedPlan, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    permission = models.CharField(max_length=10, choices=PERMISSION_CHOICES, default='view')
    invited_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('shared_plan', 'user')

class SharedPlanTask(models.Model):
    shared_plan = models.ForeignKey(SharedPlan, on_delete=models.CASCADE)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('shared_plan', 'task')

class CalendarSync(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    provider = models.CharField(max_length=50)
    provider_user_id = models.CharField(max_length=255)
    access_token = models.TextField()
    refresh_token = models.TextField(null=True, blank=True)
    synced_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'provider')
