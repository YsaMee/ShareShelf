from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (
    AcceptIncomingForm,
    LoginForm,
    RequestPostForm,
    ShareItemForm,
    SignUpForm,
)
from .models import Item, Request as ShelfRequest, UserProfile, item_matches_request


def profile_context(request):
    """Add the signed-in student's profile to every rendered template."""
    if request.user.is_authenticated:
        try:
            return {'profile': request.user.profile}
        except UserProfile.DoesNotExist:
            pass
    return {'profile': None}


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['email'].lower().strip()
        user = authenticate(request, username=email, password=form.cleaned_data['password'])
        if user is None:
            form.add_error(None, 'Invalid email or password.')
        else:
            login(request, user)
            messages.success(request, 'Logged in successfully!')
            return redirect('dashboard')
    return render(request, 'shelf/login.html', {'mode': 'login', 'form': form})


def signup_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = SignUpForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            email = form.cleaned_data['email']
            user = User.objects.create_user(username=email, email=email, password=form.cleaned_data['password'])
            UserProfile.objects.create(
                user=user, full_name=form.cleaned_data['name'], program=form.cleaned_data['program']
            )
        login(request, user)
        messages.success(request, f"Welcome to ShareShelf, {form.cleaned_data['name']}!")
        return redirect('dashboard')
    return render(request, 'shelf/login.html', {'mode': 'signup', 'form': form})


@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, 'Logged out successfully.')
    return redirect('login')


@login_required(login_url='login')
def dashboard_view(request):
    context = _dashboard_context(request.user)
    if request.GET.get('modal') in ('share', 'request'):
        context['open_modal'] = request.GET['modal']
    accept_id = request.GET.get('accept')
    if accept_id:
        accept = get_object_or_404(ShelfRequest, pk=accept_id, item__owner=request.user, status='requested')
        _mark_request_viewer(accept, request.user)
        context['accept'] = accept
        context['accept_form'] = AcceptIncomingForm(initial={'date': timezone.localdate()})
    request_id = request.GET.get('request')
    if request_id:
        handoff = get_object_or_404(ShelfRequest, pk=request_id, requester=request.user)
        context['handoff'] = _mark_request_viewer(handoff, request.user)
        context['handoff_matches'] = _matching_items(handoff)[:6] if handoff.status == 'open' else []
    return render(request, 'shelf/dashboard.html', context)


@login_required(login_url='login')
def browse_view(request):
    return HttpResponse('Browse backend is not implemented yet.', status=501)


@login_required(login_url='login')
def item_detail_view(request, item_id):
    return HttpResponse('Item detail backend is not implemented yet.', status=501)


@login_required(login_url='login')
@require_POST
def post_item_view(request):
    form = ShareItemForm(request.POST)
    if form.is_valid():
        item = form.save(commit=False)
        item.owner = request.user
        item.save()
        messages.success(request, 'Your item was added to the campus shelf.')
        return redirect('dashboard')
    return render(request, 'shelf/dashboard.html', _dashboard_context(
        request.user, share_form=form, open_modal='share'
    ))


@login_required(login_url='login')
@require_POST
def post_request_view(request):
    form = RequestPostForm(request.POST)
    if form.is_valid():
        shelf_request = form.save(commit=False)
        shelf_request.requester = request.user
        shelf_request.status = 'open'
        shelf_request.save()
        messages.success(request, 'Your request was posted.')
        return redirect('dashboard')
    return render(request, 'shelf/dashboard.html', _dashboard_context(
        request.user, request_form=form, open_modal='request'
    ))


@login_required(login_url='login')
@require_POST
def request_item_view(request, item_id):
    return HttpResponse('Requesting items through Browse is not implemented yet.', status=501)


@login_required(login_url='login')
@require_POST
def change_qty_view(request, item_id):
    item = get_object_or_404(Item, pk=item_id, owner=request.user)
    step = request.POST.get('step')
    if step == 'up' and item.qty < 20:
        item.qty += 1
        item.save(update_fields=['qty'])
    elif step == 'down' and item.qty > 1:
        item.qty -= 1
        item.save(update_fields=['qty'])
    else:
        messages.error(request, 'Quantity cannot be changed further.')
    return redirect('dashboard')


@login_required(login_url='login')
@require_POST
def toggle_pause_view(request, item_id):
    item = get_object_or_404(Item, pk=item_id, owner=request.user)
    item.paused = not item.paused
    item.save(update_fields=['paused'])
    messages.success(request, 'Sharing paused.' if item.paused else 'Sharing resumed.')
    return redirect('dashboard')


@login_required(login_url='login')
@require_POST
def remove_item_view(request, item_id):
    item = get_object_or_404(Item, pk=item_id, owner=request.user)
    if ShelfRequest.objects.filter(item=item, status__in=('requested', 'matched', 'lent')).exists():
        messages.error(request, 'This item has an active handoff and cannot be removed yet.')
    else:
        item.delete()
        messages.success(request, 'Item removed from your shelf.')
    return redirect('dashboard')


@login_required(login_url='login')
@require_POST
def accept_incoming_view(request, request_id):
    form = AcceptIncomingForm(request.POST)
    if not form.is_valid():
        shelf_request = get_object_or_404(
            ShelfRequest.objects.select_related('item'), pk=request_id, item__owner=request.user, status='requested'
        )
        _mark_request_viewer(shelf_request, request.user)
        context = _dashboard_context(request.user, accept=shelf_request, accept_form=form)
        return render(request, 'shelf/dashboard.html', context)
    with transaction.atomic():
        shelf_request = get_object_or_404(
            ShelfRequest.objects.select_for_update(), pk=request_id,
            item__owner=request.user, status='requested',
        )
        item = Item.objects.select_for_update().get(pk=shelf_request.item_id)
        if item.paused or item.qty < 1:
            messages.error(request, 'This item is no longer available to accept.')
            return redirect('dashboard')
        item.qty -= 1
        item.save(update_fields=['qty'])
        shelf_request.status = 'matched'
        shelf_request.meetup_location = form.cleaned_data['location']
        shelf_request.meetup_date = form.cleaned_data['date']
        shelf_request.meetup_time = form.cleaned_data['time']
        shelf_request.save()
    messages.success(request, 'Request accepted and meetup scheduled.')
    return redirect('dashboard')


@login_required(login_url='login')
@require_POST
def decline_incoming_view(request, request_id):
    shelf_request = get_object_or_404(ShelfRequest, pk=request_id, item__owner=request.user, status='requested')
    shelf_request.status = 'declined'
    shelf_request.save(update_fields=['status', 'updated_at'])
    messages.success(request, 'Request declined.')
    return redirect('dashboard')


@login_required(login_url='login')
@require_POST
def complete_incoming_view(request, request_id):
    shelf_request = get_object_or_404(ShelfRequest, pk=request_id, item__owner=request.user, status='matched')
    shelf_request.status = 'lent' if shelf_request.is_lend else 'fulfilled'
    shelf_request.save(update_fields=['status', 'updated_at'])
    messages.success(request, 'Loan started.' if shelf_request.is_lend else 'Handoff marked complete.')
    return redirect('dashboard')


@login_required(login_url='login')
@require_POST
def mark_returned_view(request, request_id):
    with transaction.atomic():
        shelf_request = get_object_or_404(
            ShelfRequest.objects.select_for_update(), pk=request_id, item__owner=request.user, status='lent'
        )
        item = Item.objects.select_for_update().get(pk=shelf_request.item_id)
        item.qty = min(item.qty + 1, 20)
        item.save(update_fields=['qty'])
        shelf_request.status = 'returned'
        shelf_request.save(update_fields=['status', 'updated_at'])
    messages.success(request, 'Item marked as returned.')
    return redirect('dashboard')


@login_required(login_url='login')
@require_POST
def cancel_request_view(request, request_id):
    with transaction.atomic():
        shelf_request = get_object_or_404(
            ShelfRequest.objects.select_for_update(), pk=request_id, requester=request.user
        )
        if shelf_request.is_closed or shelf_request.status == 'lent':
            messages.error(request, 'This request can no longer be cancelled.')
            return redirect('dashboard')
        if shelf_request.status == 'matched' and shelf_request.item_id:
            item = Item.objects.select_for_update().get(pk=shelf_request.item_id)
            item.qty = min(item.qty + 1, 20)
            item.save(update_fields=['qty'])
        shelf_request.status = 'cancelled'
        shelf_request.save(update_fields=['status', 'updated_at'])
    messages.success(request, 'Request cancelled.')
    return redirect('dashboard')


@login_required(login_url='login')
@require_POST
def confirm_handoff_view(request, request_id):
    shelf_request = get_object_or_404(ShelfRequest, pk=request_id, requester=request.user, status='matched')
    shelf_request.status = 'lent' if shelf_request.is_lend else 'fulfilled'
    shelf_request.save(update_fields=['status', 'updated_at'])
    messages.success(request, 'Borrowing started.' if shelf_request.is_lend else 'Handoff confirmed. Thanks!')
    return redirect('dashboard')


@login_required(login_url='login')
@require_POST
def ask_for_match_view(request, request_id, item_id):
    shelf_request = get_object_or_404(ShelfRequest, pk=request_id, requester=request.user, status='open')
    item = get_object_or_404(Item, pk=item_id, paused=False, qty__gt=0)
    if not item_matches_request(item, shelf_request):
        messages.error(request, 'That item is not an available match for your request.')
        return redirect('dashboard')
    if item.is_lend:
        messages.info(request, 'Borrowing through Browse will be added later.')
        return redirect('dashboard')
    shelf_request.item = item
    shelf_request.is_lend = False
    shelf_request.status = 'requested'
    shelf_request.save(update_fields=['item', 'is_lend', 'status', 'updated_at'])
    messages.success(request, 'Your request was sent to the student sharing this item.')
    return redirect('dashboard')

def _greeting_for_hour(hour):
    """Functional style: a pure function maps an hour to a greeting."""
    if hour < 12:
        return 'Good morning'
    if hour < 17:
        return 'Good afternoon'
    return 'Good evening'


def _posted_label(created_at):
    days = (timezone.localdate() - timezone.localtime(created_at).date()).days
    if days <= 0:
        return 'Posted today'
    if days == 1:
        return 'Posted yesterday'
    if days < 7:
        return f'Posted {days} days ago'
    return f'Posted {timezone.localtime(created_at):%b %d}'


def _mark_request_viewer(shelf_request, user):
    shelf_request._viewer_id = user.id
    shelf_request._viewer_is_sharer = bool(shelf_request.item_id and shelf_request.item.owner_id == user.id)
    return shelf_request


def _matching_items(shelf_request):
    candidates = Item.objects.filter(
        category=shelf_request.category, listing='give', paused=False, qty__gt=0,
    ).exclude(owner_id=shelf_request.requester_id).select_related('owner', 'owner__profile')
    return [item for item in candidates if item_matches_request(item, shelf_request)]


def _listing_context():
    return {
        'listing_choices': Item.LISTING_CHOICES,
        'listing_hints': {
            'give': 'Give a classmate an item you no longer need.',
            'lend': 'Loan an item for a short time and get it back.',
        },
        'condition_prefs': [
            ('Flexible', 'Any condition is okay.'),
            ('New', 'Only new items.'),
            ('Gently Used', 'Gently used items are okay.'),
            ('Functional', 'A functional item is enough.'),
        ],
        'max_note': 200,
    }


def _dashboard_context(user, share_form=None, request_form=None, accept=None,
                       accept_form=None, handoff=None, open_modal=''):
    """Procedural view helper: gather page data before rendering the dashboard."""
    today = timezone.localdate()
    all_items = list(Item.objects.filter(owner=user).select_related('owner', 'owner__profile'))
    incoming_requests = ShelfRequest.objects.filter(
        item__owner=user,
        status__in=('requested', 'matched', 'lent'),
    ).select_related('requester', 'requester__profile', 'item', 'item__owner', 'item__owner__profile')

    incoming = []
    for shelf_request in incoming_requests:
        _mark_request_viewer(shelf_request, user)
        item = shelf_request.item
        incoming.append({
            'request': shelf_request,
            'item': item,
            'can_accept': shelf_request.status == 'requested' and not item.paused and item.qty > 0,
            'posted': _posted_label(shelf_request.created_at),
            'overdue': bool(shelf_request.status == 'lent' and shelf_request.return_by and shelf_request.return_by < today),
        })

    incoming_new = sum(1 for row in incoming if row['request'].status == 'requested')
    shelf_rows = []
    for item in all_items:
        item_requests = ShelfRequest.objects.filter(item=item)
        if item_requests.filter(status='lent').exists():
            status = 'Lent out'
        elif item_requests.filter(status='matched').exists():
            status = 'Reserved'
        elif item.paused:
            status = 'Paused'
        elif item.qty:
            status = 'Available'
        else:
            status = 'None left'
        shelf_rows.append({
            'item': item, 'status': status,
            'can_decrease': item.qty > 1, 'can_increase': item.qty < 20,
        })

    own_requests = list(ShelfRequest.objects.filter(requester=user).select_related(
        'requester', 'requester__profile', 'item', 'item__owner', 'item__owner__profile'
    ))
    request_rows = []
    for shelf_request in own_requests:
        _mark_request_viewer(shelf_request, user)
        request_rows.append({
            'request': shelf_request,
            'posted': _posted_label(shelf_request.created_at),
            'matches': _matching_items(shelf_request)[:6] if shelf_request.status == 'open' else [],
            'overdue': bool(shelf_request.status == 'lent' and shelf_request.return_by and shelf_request.return_by < today),
        })

    done_requests = [r for r in ShelfRequest.objects.filter(item__owner=user)
                     if r.status in ('fulfilled', 'lent', 'returned')]
    context = {
        'greeting': _greeting_for_hour(timezone.localtime().hour),
        'stats': {
            'items_shared': len(all_items),
            'shared_today': sum(1 for item in all_items if timezone.localtime(item.created_at).date() == today),
            'available': sum(1 for item in all_items if item.qty > 0 and not item.paused),
            'open_requests': sum(1 for r in own_requests if r.status in ('open', 'requested')),
            'matched': sum(1 for r in own_requests if r.status == 'matched'),
            'students_helped': len({r.requester_id for r in done_requests}),
            'helped_today': sum(1 for r in done_requests if timezone.localtime(r.updated_at).date() == today),
            'waiting_on_you': incoming_new,
        },
        'incoming': incoming,
        'new_incoming': incoming_new,
        'shelf': shelf_rows,
        'shelf_limit': 5,
        'shelf_hidden': max(0, len(shelf_rows) - 5),
        'requests': request_rows,
        'request_limit': 5,
        'requests_hidden': max(0, len(request_rows) - 5),
        'share_form': share_form or ShareItemForm(),
        'request_form': request_form or RequestPostForm(),
        'listing_hints': _listing_context()['listing_hints'],
        'listing_choices': Item.LISTING_CHOICES,
        'condition_prefs': _listing_context()['condition_prefs'],
        'max_note': 200,
        'accept': accept,
        'accept_form': accept_form or AcceptIncomingForm(),
        'handoff': handoff,
        'handoff_matches': _matching_items(handoff)[:6] if handoff and handoff.status == 'open' else [],
        'handoff_overdue': bool(handoff and handoff.return_by and handoff.return_by < today),
        'open_modal': open_modal,
        'dashboard_url': '/dashboard/',
    }
    if handoff:
        _mark_request_viewer(handoff, user)
    return context
