from django.db import models

# payments/models.py
class Payment(models.Model):
    STATUS_CHOICES = [
        ('P', 'Pending'),
        ('S', 'Success'),
        ('F', 'Failed'),
    ]
    
    razorpay_order_id = models.CharField(max_length=255)
    razorpay_payment_id = models.CharField(max_length=255, blank=True)
    razorpay_signature = models.CharField(max_length=255, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    amount_in_paisa = models.IntegerField(null=True)
    currency = models.CharField(max_length=3, default='INR')
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='P')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment {self.id} - {self.get_status_display()}"