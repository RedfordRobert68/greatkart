from django.shortcuts import render, redirect
from django.core.mail import send_mail, EmailMessage
from carts.models import CartItem
from .forms import OrderForm
import datetime
from .models import Order, Payment, OrderProduct
from django.http import HttpResponse, JsonResponse
from django.views import View
from store.models import Product
from django.template.loader import render_to_string
# from django.urls import reverse
import json

# STRIPE
# import stripe
# stripe.api_version = '2024-10-28.acacia'
# from django.conf import settings
# from django.views import generic
# from django.views.decorators.csrf import csrf_exempt
# import datetime

# stripe.api_key = settings.STRIPE_SECRET_KEY
# endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

def payments(request):
    body = json.loads(request.body)
    print(body)
    order = Order.objects.get(user=request.user, is_ordered=False, order_number=body['orderID'])
    
    # #Store transaction details inside Payment model
    payment = Payment(
        user = request.user,
        payment_id = body['transID'],
        payment_method = body['payment_method'],
        amount_paid = order.order_total,
        status = body['status'],
    )
    
    payment.save()

    order.payment = payment
    order.is_ordered = True
    order.save()

    # Move the cart items to Order Product table
    cart_items = CartItem.objects.filter(user=request.user)

    for item in cart_items:
        orderproduct = OrderProduct()
        orderproduct.order_id = order.id
        orderproduct.payment = payment
        orderproduct.user_id = request.user.id
        orderproduct.product_id = item.product_id
        orderproduct.quantity = item.quantity
        orderproduct.product_price = item.product.price
        orderproduct.ordered = True
        orderproduct.save()

        # You must save the product before adding variations with ManyToMany fields
        cart_item = CartItem.objects.get(id=item.id)
        product_variation = cart_item.variations.all()
        orderproduct = OrderProduct.objects.get(id=orderproduct.id)
        orderproduct.variations.set(product_variation)
        orderproduct.save()


        # Reduce the quantity/stock of the sold products
        product = Product.objects.get(id=item.product_id)
        product.stock -= item.quantity
        product.save()


    # Clear the cart
    CartItem.objects.filter(user=request.user).delete()

    # Send order received email to customer
    mail_subject = 'Thank you for your purchase!'
    message = render_to_string('orders/order_received_email.html', {
        'user': request.user,
        'order': order,
    })

    to_email = request.user.email
    send_email = EmailMessage(mail_subject, message, to=[to_email])
    send_email.send()


    # Send order number and transaction id back to sendData method via JsonResponse
    data = {
        'order_number': order.order_number,
        'transID': payment.payment_id,
    }

    return JsonResponse(data)

# def paymentSuccess(request):
#     context = {
#         'payment_status' : 'success', 
#     }
#     return render(request, 'orders/confirmation.html', context)

# def paymentCancel(request):
#     context = {
#         'payment_status' : 'cancel'
#     }
#     return render(request, 'orders/confirmation.html', context)


def place_order(request, total=0, quantity=0):
    current_user = request.user

    # If the cart count is less than or equal to 0, redirect back to store
    cart_items = CartItem.objects.filter(user=current_user)
    cart_count = cart_items.count()

    if cart_count <= 0:
        return redirect('store')
    
    grand_total = 0
    tax = 0

    for cart_item in cart_items:
        total += (cart_item.product.price * cart_item.quantity)
        quantity += cart_item.quantity

    tax = (6 * total)/100
    grand_total = total + tax
    
    if request.method == 'POST':
        form = OrderForm(request.POST)

        if form.is_valid():
            # Store all the billing information inside the Order table
            data = Order()
            data.user = current_user
            data.first_name = form.cleaned_data['first_name']
            data.last_name = form.cleaned_data['last_name']
            data.phone = form.cleaned_data['phone']
            data.email = form.cleaned_data['email']
            data.address_line_1 = form.cleaned_data['address_line_1']
            data.address_line_2 = form.cleaned_data['address_line_2']
            data.country = form.cleaned_data['country']
            data.state = form.cleaned_data['state']
            data.city = form.cleaned_data['city']
            # Add zip code on rebuild
            data.order_note = form.cleaned_data['order_note']
            data.order_total = grand_total
            data.tax = tax
            data.ip = request.META.get('REMOTE_ADDR')
            data.save()

            # Generate order number
            yr = int(datetime.date.today().strftime('%Y'))
            dt = int(datetime.date.today().strftime('%d'))
            mt = int(datetime.date.today().strftime('%m'))
            d = datetime.date(yr, mt, dt)
            current_date = d.strftime("%Y%m%d")
            order_number = current_date + str(data.id)
            data.order_number = order_number
            data.save()

            order = Order.objects.get(user=current_user, is_ordered=False, order_number=order_number)
            context = {
                'order': order,
                'cart_items': cart_items,
                'total': total,
                'tax': tax,
                'grand_total': grand_total,
            }

            return render(request, 'orders/payments.html', context)
        else:
            return redirect('checkout')
        
def order_complete(request):
    order_number = request.GET.get('order_number')
    transID = request.GET.get('payment_id')

    try:
        order = Order.objects.get(order_number=order_number, is_ordered=True)
        ordered_products = OrderProduct.objects.filter(order_id=order.id)

        subtotal = 0
        for i in ordered_products:
            subtotal += i.product_price * i.quantity
        payment = Payment.objects.get(payment_id=transID)

        context = {
            'order': order,
            'ordered_products': ordered_products,
            'order_number': order.order_number,
            'transID': payment.payment_id, 
            'payment': payment,
            'subtotal': subtotal,
        }
        return render(request, 'orders/order_complete.html', context)
    
    except (Payment.DoesNotExist, Order.DoesNotExist):
        return redirect('home')


   
        

# for payments

# class CreateCheckoutSessionView(generic.View):
#     def post(self, request, *args, **kwargs):    
#         host = self.request.get_host()
#         order_id = self.request.POST.get('order-id')
#         order = Order.objects.get(id=order_id)

#         checkout_session = stripe.checkout.Session.create(
#             payment_method_types=['card'],
#             line_items=[
#                 {
#                    'price_data': {
#                        'currency': 'usd',
#                        'unit_amount': int(order.order_total * 100), 
#                        'product_data': {
#                            'name': order.order_number,
#                            # 'images': ['https://i.imgur.com/EHyR2nP.png'],
#                        },
#                    },
#                    'quantity' : 1,
#                 },
#             ],
#             metadata = {
#                 "order_id": order.id,
#             },
#             mode='payment',
#             # success_url="http://localhost:8000/orders/payment-success",
#             # cancel_url="http://localhost:8000/orders/payment-cancel",
#             success_url="http://{}{}".format(host,reverse('orders:payment-success')),
#             cancel_url="http://{}{}".format(host,reverse('orders:payment-cancel')),
#             # automatic_tax={'enabled': True},
#         )
#         return redirect(checkout_session.url, code=303)
    


# Using Django
# @csrf_exempt
# def my_webhook_view(request):
#     payload = request.body
#     sig_header = request.META['HTTP_STRIPE_SIGNATURE']
#     event = None

#     try:
#         event = stripe.Webhook.construct_event(
#             payload, sig_header, endpoint_secret
#         )
#     except ValueError as e:
#         # Invalid payload
#         return HttpResponse(status=400)
#     except stripe.error.SignatureVerificationError as e:
#         # Invalid signature
#         return HttpResponse(status=400)

#     # Handle the checkout.session.completed event

#     if event['type'] == 'checkout.session.completed':
#         session = event['data']['object']

#         customer_email = session["customer_details"]["email"]
#         # order_id = ["metadata"]["order_id"]
#         # order = Order.objects.get(id=order_id)

#         send_mail(
#             subject="Here is your order number",
#             message="Here is your order. Thank you for your purchase.",
#             recipient_list=[customer_email], 
#             from_email="bob@bob.com"
#         )

#         print(session)

        #TODO - Decide whether or not to send files

    #     if session.payment_status == "paid":
    #         # Fulfill the purchase
    #         # line_item = session.list_line_items(session.id, limit=1).data[0]
    #         # order_id = line_item['description']
    #         fulfill_order()

    # # Passed signature verification
        # fullfill_order(session)
        # print(session)
    # return HttpResponse(status=200)
    

# class StripeIntentView(View):
#     def post(self, request, *args, **kwargs):
#         host = self.request.get_host()
#         try:
#             req_json = json.loads(request.body)
#             customer = stripe.Customer.create(email=req_json['email'])
#             order_id = self.request.POST.get('order-id')
#             order = Order.objects.get(id=order_id)
#             intent = stripe.PaymentIntent.create(
#                 amount=int(order.order_total * 100),
#                 currency='usd',
#                 customer=customer['id'],
#                 metadata={
#                     "order_id": order.id
#                 }
#             )
#             return JsonResponse({
#                 'clientSecret': intent['client_secret']
#             })
#         except Exception as e:
#             return JsonResponse({ 'error': str(e) })

# def fulfill_checkout():
#     pass
    # order = Order.objects.get(id=order_id)
    # order.ordered = True
    # order.orderedDate = datetime.datetime.now()
    # order.save()

    # for item in order.items.all():
    #     product_var = ProductVariation.objects.get(id=item.product.id)
    #     product_var.stock -= item.quantity
    #     product_var.save


