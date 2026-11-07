from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone
from projects.models import Project

class Task(models.Model):
    """
    SRS FR-05, FR-06, FR-07, FR-09:
    Task entity with Kanban lifecycle, priority, estimation, and optimistic versioning.
    """
    STATUS_BACKLOG = 'Backlog'
    STATUS_TODO = 'To Do'
    STATUS_IN_PROGRESS = 'In Progress'
    STATUS_REVIEW = 'Review'
    STATUS_DONE = 'Done'

    STATUS_CHOICES = [
        (STATUS_BACKLOG, 'Backlog'),
        (STATUS_TODO, 'To Do'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_REVIEW, 'Review'),
        (STATUS_DONE, 'Done'),
    ]

    PRIORITY_LOW = 'Low'
    PRIORITY_MEDIUM = 'Medium'
    PRIORITY_HIGH = 'High'
    PRIORITY_CRITICAL = 'Critical'

    PRIORITY_CHOICES = [
        (PRIORITY_LOW, 'Low'),
        (PRIORITY_MEDIUM, 'Medium'),
        (PRIORITY_HIGH, 'High'),
        (PRIORITY_CRITICAL, 'Critical'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tasks')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_BACKLOG, db_index=True)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default=PRIORITY_MEDIUM, db_index=True)
    estimate_hours = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    due_date = models.DateField(null=True, blank=True, db_index=True)
    version = models.PositiveIntegerField(default=1)  # For optimistic concurrency (SAD §3.7)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['id']
        indexes = [
            models.Index(fields=['project', 'status']),
            models.Index(fields=['project', 'due_date']),
        ]

    @property
    def actual_hours(self):
        """Sum of retained time entries (SRS FR-10)."""
        if '_actual_hours_total' in self.__dict__:
            return self.__dict__['_actual_hours_total'] or Decimal('0.00')
        total = self.time_entries.aggregate(models.Sum('hours'))['hours__sum']
        return total or Decimal('0.00')

    @property
    def is_overdue(self):
        if self.due_date and self.status != self.STATUS_DONE:
            return self.due_date < timezone.now().date()
        return False

    def __str__(self):
        return f"[{self.project.name} #{self.id}] {self.title} ({self.status})"


class TimeEntry(models.Model):
    """
    SRS FR-10: Time logging.
    Logged positive time in 0.25-hour increments against a task.
    """
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='time_entries')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='time_entries')
    hours = models.DecimalField(max_digits=5, decimal_places=2)
    date = models.DateField(default=timezone.now)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.user.email}: {self.hours}h on Task #{self.task.id}"


class Comment(models.Model):
    """
    SRS FR-12: Task comments in chronological order.
    """
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='task_comments')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.author.email} on Task #{self.task.id} at {self.created_at}"
