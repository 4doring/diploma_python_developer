from django.urls import path
from django_rest_passwordreset.views import (
    reset_password_confirm,
    reset_password_request_token,
)

from apps.catalog.views import PartnerOrders, PartnerState, PartnerUpdate
from apps.contacts.views import ContactView
from apps.orders.views import PartnerOrderStatusView
from apps.users.views import (
    AccountDetails,
    ConfirmAccount,
    LoginAccount,
    RegisterAccount,
)

app_name = 'users'

urlpatterns = [
    path('partner/update', PartnerUpdate.as_view(), name='partner-update'),
    path('partner/state', PartnerState.as_view(), name='partner-state'),
    path('partner/orders', PartnerOrders.as_view(), name='partner-orders'),
    path('partner/order/state', PartnerOrderStatusView.as_view(), name='partner-order-state'),
    path('register', RegisterAccount.as_view(), name='user-register'),
    path('register/confirm', ConfirmAccount.as_view(), name='user-register-confirm'),
    path('details', AccountDetails.as_view(), name='user-details'),
    path('contact', ContactView.as_view(), name='user-contact'),
    path('login', LoginAccount.as_view(), name='user-login'),
    path('password_reset', reset_password_request_token, name='password-reset'),
    path('password_reset/confirm', reset_password_confirm, name='password-reset-confirm'),
]