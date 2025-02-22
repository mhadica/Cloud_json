from rest_framework import serializers
from .models import Payment

class PaymentSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id',
            'razorpay_order_id',
            'razorpay_payment_id',
            'amount',
            'amount_in_paisa',
            'currency',
            'status',
            'status_display',
            'created_at',
            'updated_at'
        ]