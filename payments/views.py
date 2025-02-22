# payments/views.py
import razorpay
import logging
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from decimal import Decimal, InvalidOperation
from .models import Payment
from razorpay.errors import SignatureVerificationError
from .serializers import PaymentSerializer
from django.utils import timezone
from datetime import timedelta

# Initialize logger
logger = logging.getLogger(__name__)

class InitiatePaymentView(APIView):
    def post(self, request):
        try:
            # Log the incoming request data
            logger.info(f"Request data: {request.data}")
            # ... rest of your view code

            # Validate amount
            amount = request.data.get('amount')
            if not amount:
                return Response(
                    {'error': 'Amount is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                amount = Decimal(str(amount))
                if amount <= 0:
                    return Response(
                        {'error': 'Amount must be greater than 0'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except InvalidOperation:
                return Response(
                    {'error': 'Invalid amount format'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Initialize Razorpay client
            client = razorpay.Client(
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
            )
            
            # Convert amount to paisa
            amount_in_paisa = int(amount * 100)
            
            # Create a Razorpay order
            order = client.order.create({
                'amount': amount_in_paisa,
                'currency': 'INR',
                'payment_capture': 1
            })

            # Save the payment record in the database
            payment_record = Payment.objects.create(
                razorpay_order_id=order['id'],
                amount=amount,
                amount_in_paisa=amount_in_paisa
            )

            # Return the Razorpay order details to the frontend
            return Response({
                'order_id': order['id'],
                'amount': amount_in_paisa,
                'key': settings.RAZORPAY_KEY_ID
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error in InitiatePaymentView: {str(e)}")
            logger.error(f"Request data: {request.data}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )

class PaymentSuccessView(APIView):
    permission_classes = []  # Allow unauthenticated access
    
    def post(self, request):
        try:
            data = request.data
            client = razorpay.Client(
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
            )
            
            # Verify the payment signature
            client.utility.verify_payment_signature({
                'razorpay_order_id': data['razorpay_order_id'],
                'razorpay_payment_id': data['razorpay_payment_id'],
                'razorpay_signature': data['razorpay_signature']
            })
            
            # Update the payment record in the database
            payment = Payment.objects.get(razorpay_order_id=data['razorpay_order_id'])
            payment.status = 'S'  # 'S' for success
            payment.razorpay_payment_id = data['razorpay_payment_id']
            payment.razorpay_signature = data['razorpay_signature']
            payment.save()
            
            # Serialize the payment record for the response
            serializer = PaymentSerializer(payment)
            
            return Response({
                'status': 'success',
                'message': 'Payment verified successfully',
                'payment': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Payment.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Invalid order ID'
            }, status=status.HTTP_400_BAD_REQUEST)
        except SignatureVerificationError:
            return Response({
                'status': 'error',
                'message': 'Invalid signature'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error in PaymentSuccessView: {str(e)}")
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PaymentListAPI(generics.ListAPIView):
    permission_classes = []  # Allow unauthenticated access
    serializer_class = PaymentSerializer
    queryset = Payment.objects.all()
    
    def get_queryset(self):
        queryset = super().get_queryset()
        order_id = self.request.query_params.get('order_id')
        status = self.request.query_params.get('status')
        payment_id = self.request.query_params.get('payment_id')
        
        if order_id:
            queryset = queryset.filter(razorpay_order_id=order_id)
        if status:
            queryset = queryset.filter(status=status)
        if payment_id:
            queryset = queryset.filter(razorpay_payment_id=payment_id)
            
        return queryset.order_by('-created_at')

class TransactionDetailsAPI(APIView):
    permission_classes = []  # Allow unauthenticated access
    
    def get(self, request):
        try:
            # Get query parameters with defaults
            hours = request.query_params.get('hours', 24)  # Default to last 24 hours
            limit = request.query_params.get('limit', 10)  # Default to 10 transactions
            
            try:
                hours = int(hours)
                limit = int(limit)
            except ValueError:
                return Response({
                    'status': 'error',
                    'message': 'Invalid hours or limit parameter'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get successful transactions within the time period
            time_threshold = timezone.now() - timedelta(hours=hours)
            transactions = Payment.objects.filter(
                status='S',  # Only successful transactions
                created_at__gte=time_threshold
            ).order_by('-created_at')[:limit]
            
            # Format the response
            transaction_list = []
            for payment in transactions:
                transaction_list.append({
                    'order_id': payment.razorpay_order_id,
                    'payment_id': payment.razorpay_payment_id,
                    'amount': str(payment.amount),
                    'currency': payment.currency,
                    'status': payment.get_status_display(),
                    'timestamp': payment.created_at.isoformat()
                })
            
            response_data = {
                'status': 'success',
                'count': len(transaction_list),
                'transactions': transaction_list
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in TransactionDetailsAPI: {str(e)}")
            return Response({
                'status': 'error',
                'message': 'An error occurred while fetching transaction details'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
