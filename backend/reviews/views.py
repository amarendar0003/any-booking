from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect

from services.models import Service
from .forms import ReviewForm
from .models import Review


def add_review(request, slug):
    service = get_object_or_404(Service, slug=slug, is_active=True)
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.service = service
            review.status = Review.STATUS_PENDING
            review.save()
            messages.success(
                request,
                'Thanks! Your review has been submitted and is awaiting approval.',
            )
    return redirect('service_detail', slug=slug)
