from django.shortcuts import render
from store.models import Product, ReviewRating


def home(request):
    products = Product.objects.all().filter(is_available=True).order_by('created_date')

    # Get the reviews
    for product in products:
        reviews = ReviewRating.objects.filter(product_id=product.id, status=True)

    context = {
        'products': products,
        'reviews': reviews,
    }

    return render(request, 'home.html', context)





from django.http import JsonResponse
import os

def env_test(request):
    return JsonResponse({
        "SECRET_KEY": os.environ.get("SECRET_KEY"),
        "DEBUG": os.environ.get("DEBUG"),
        "ALLOWED_HOSTS": os.environ.get("ALLOWED_HOSTS"),
    })
