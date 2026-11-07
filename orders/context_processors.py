from .models import Order


def new_order_count(request):
    if (
        request.path.startswith('/quan-ly/')
        and getattr(request, 'user', None)
        and request.user.is_authenticated
    ):
        return {'new_order_count': Order.objects.filter(status='new').count()}
    return {'new_order_count': 0}
