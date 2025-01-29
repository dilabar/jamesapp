from django.db import models

from agency.models import User

# Create your models here.
class CallRate(models.Model):
    """
    Table to define dynamic rates for calls (e.g., per second).
    """
    name = models.CharField(max_length=100, blank=True, null=True)
    price_per_second = models.DecimalField(max_digits=6, decimal_places=4)
    is_active = models.BooleanField(default=True)  # Flag for active/inactive rates

    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"{self.name} : {self.price_per_second}/s ({status})"
    

class Bill(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # Link to user
    month = models.PositiveIntegerField()  # Month (1 = January, 12 = December)
    year = models.PositiveIntegerField()  # Year (e.g., 2025)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)


    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'month', 'year'], name='unique_user_month_year')
        ]

    def __str__(self):
        return f"Bill for {self.user.username} - {self.month}/{self.year}"

