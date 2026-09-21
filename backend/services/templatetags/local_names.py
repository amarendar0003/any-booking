"""
Template tags for resolving region-aware display names.

The current region is determined (in priority order) from:
  1. request.GET['state']  → State ID
  2. request.GET['country'] → Country ID
  3. The service's own city.state / city.country (on detail pages)
  4. Falls back to the default English name

Usage in templates:
  {% load local_names %}
  {{ category|local_cat_name:request }}
  {{ attribute|local_attr_name:request }}
"""
from django import template
from django.core.cache import cache
from services.models import Country, State, RegionalCategoryConfig, AttributeLocalName

register = template.Library()


def _resolve_region(request):
    """Returns (country_obj, state_obj) from request GET params or None."""
    country, state = None, None
    country_id = request.GET.get('country')
    state_id = request.GET.get('state')
    if country_id:
        country = Country.objects.filter(pk=country_id).first()
    if state_id:
        state = State.objects.filter(pk=state_id).first()
        if state and not country:
            country = state.country
    return country, state


@register.filter
def local_cat_name(category, request):
    """{{ category|local_cat_name:request }} — returns localized category name."""
    if category is None:
        return ''
    country, state = _resolve_region(request)
    return category.get_local_display_name(country=country, state=state)


@register.filter
def local_cat_desc(category, request):
    """{{ category|local_cat_desc:request }} — returns localized category description."""
    if category is None:
        return ''
    country, state = _resolve_region(request)
    return category.get_local_description(country=country, state=state)


@register.filter
def local_attr_name(attribute, request):
    """{{ attribute|local_attr_name:request }} — returns localized attribute label."""
    if attribute is None:
        return ''
    country, state = _resolve_region(request)
    if state:
        override = AttributeLocalName.objects.filter(
            attribute=attribute, country=country, state=state
        ).first()
        if override:
            return override.local_name
    if country:
        override = AttributeLocalName.objects.filter(
            attribute=attribute, country=country, state=None
        ).first()
        if override:
            return override.local_name
    return attribute.name


@register.simple_tag(takes_context=True)
def service_cat_name(context, category):
    """
    {% service_cat_name category %} — resolves name using the service's own city region
    (for detail pages where the service object is in context, not GET params).
    """
    service = context.get('service')
    country = state = None
    if service and service.city:
        country = service.city.country
        state = service.city.state
    elif category:
        request = context.get('request')
        if request:
            country, state = _resolve_region(request)
    if category:
        return category.get_local_display_name(country=country, state=state)
    return ''
