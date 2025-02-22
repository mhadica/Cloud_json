from django.urls import path
from .views import (
    InitiatePaymentView,
    PaymentSuccessView,
    PaymentListAPI,
    TransactionDetailsAPI
)

urlpatterns = [
    path('initiate/', InitiatePaymentView.as_view(), name='initiate_payment'),
    path('success/', PaymentSuccessView.as_view(), name='payment_success'),
    path('transactions/', PaymentListAPI.as_view(), name='payment_list'),
    path('transaction-details/', TransactionDetailsAPI.as_view(), name='transaction_details'),
]