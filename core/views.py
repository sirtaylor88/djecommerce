from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required # for function based view
from django.contrib.auth.mixins import LoginRequiredMixin # for class based view
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, View
from django.utils import timezone

from .forms import CheckoutForm

from .models import Item, OrderItem, Order, BillingAddress

import stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

# Create your views here.
class HomeView(ListView):
    model         = Item
    paginate_by   = 10
    ordering      = ['-id'] # minus = descending
    template_name = "home.html"

class OrderSummaryView(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            context = {
                "object": order
            }
            return render(self.request, "order_summary.html", context)
        except ObjectDoesNotExist:
            messages.error(self.request, "You do not have an active order.")
            return redirect("/")

class ItemDetailView(DetailView):
    model         = Item
    template_name = "product.html"

class CheckoutView(View):
    def get(self, *args, **kwargs):
        # form
        form = CheckoutForm()
        context = {
            "form": form
        }
        return render(self.request, "checkout.html", context)

    def post(self, *args, **kwargs):
        # form
        form = CheckoutForm(self.request.POST or None)
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            if form.is_valid():
                street_address = form.cleaned_data.get("street_address")
                apartment_address = form.cleaned_data.get("apartment_address")
                country = form.cleaned_data.get("country")
                postal_code = form.cleaned_data.get("postal_code")
                # TODO: add functionality for these fields
                # same_shipping_address = form.cleaned_data.get("same_shipping_address")
                # save_info = form.cleaned_data.get("save_info")
                payment_option = form.cleaned_data.get("payment_option")
                billing_address = BillingAddress(
                    user              = self.request.user,
                    street_address    = street_address,
                    apartment_address = apartment_address,
                    country           = country,
                    postal_code       = postal_code
                )
                billing_address.save()
                order.billing_address = billing_address
                order.save()
                # TODO: Add redirect to the selected payment option
                return redirect("core:checkout")
            messages.warning(self.request, "Failed checkout")
            return redirect("core:checkout")
        except ObjectDoesNotExist:
            messages.error(self.request, "You do not have an active order.")
            return redirect("core:order-summary")

class PaymentView(View):
    def get(self, *args, **kwargs):
        # order
        return render(self.request, "payment.html")

    def post(self, *args, **kwargs):
        token = self.request.POST.get("stripeToken")
        order = Qrder.objects.get(user=self.request.user, ordered=False)
        stripe.Charge.create(
            amount        = order.get_total() * 100, # value in cents
            currency      = "eur",
            source        = token
        )
        order.ordered = True

def products(request):
    template = "products.html"
    context = {
        "items": Item.objects.all()
    }
    return render(request, template, context)

@login_required
def add_to_cart(request, slug):
    item       = get_object_or_404(Item, slug=slug)
    order_item, created = OrderItem.objects.get_or_create(
        item=item,
        user=request.user,
        ordered=False
    )
    order_qs   = Order.objects.filter(
        user=request.user,
        ordered=False
    )

    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item.quantity += 1
            order_item.save()
            messages.info(request, "This item quantity was updated.")
            return redirect("core:order-summary")
        else:
            order.items.add(order_item)
            messages.info(request, "This item was added to your cart.")
            return redirect("core:order-summary")
    else:
        order = Order.objects.create(
            user=request.user,
            ordered_date= timezone.now()
        )
        order.items.add(order_item)
        messages.info(request, "This item was added to your cart.")
        return redirect("core:order-summary")

@login_required
def remove_from_cart(request, slug):
    item       = get_object_or_404(Item, slug=slug)
    order_qs   = Order.objects.filter(
        user=request.user,
        ordered=False
    )
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            order.items.remove(order_item)
            messages.info(request, "This item was removed from your cart.")
            return redirect("core:order-summary")
        else:
            messages.info(request, "This item was not in your cart.")
            return redirect("core:product", slug=slug)

    else:
        messages.info(request, "You don't have an active order.")
        return redirect("core:product", slug=slug)

@login_required
def remove_single_item_from_cart(request, slug):
    item       = get_object_or_404(Item, slug=slug)
    order_qs   = Order.objects.filter(
        user=request.user,
        ordered=False
    )
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            if order_item.quantity > 1:
                order_item.quantity -= 1
                order_item.save()
                messages.info(request, "This item quantity was updated.")
            else:
                order.items.remove(order_item)
                messages.info(request, "This item was removed from your cart.")
            return redirect("core:order-summary")
        else:
            messages.info(request, "This item was not in your cart.")
            return redirect("core:order-summary")

    else:
        messages.info(request, "You don't have an active order.")
        return redirect("core:order-summary")

