from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import (
    AcceptIncomingForm,
    BorrowForm,
    LoginForm,
    RequestPostForm,
    ShareItemForm,
    SignUpForm,
    ProfileForm,
    ShelfPasswordChangeForm,
)
from . import logic
from .models import Item, Request as ShelfRequest, UserProfile


def profile_context(request):
    """Add the signed-in student's profile to every rendered template."""
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
        except UserProfile.DoesNotExist:
            return {'profile': None, 'profile_form': None}
        return {'profile': profile, 'profile_form': ProfileForm(instance=profile)}
    return {'profile': None, 'profile_form': None}

@login_required(login_url='login')
def settings_view(request):
    password_form = ShelfPasswordChangeForm(request.user)
    if request.method == 'POST':
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile was updated.')
            next_url = request.POST.get('next')
            if next_url and url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
            ):
                return redirect(next_url)
            return redirect('settings')
        return render(request, 'shelf/settings.html', {
            'profile_form': form, 'open_modal': 'profile', 'password_form': password_form,
        })
    return render(request, 'shelf/settings.html', {'password_form': password_form})


@login_required(login_url='login')
@require_POST
def password_change_view(request):
    form = ShelfPasswordChangeForm(request.user, request.POST)
    if form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, 'Your password was changed.')
        return redirect('settings')
    return render(request, 'shelf/settings.html', {'password_form': form})

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
        context['handoff_matches'] = _matching_items(handoff) if handoff.status == 'open' else []
        context['handoff_overdue'] = handoff.status == 'lent' and handoff.pk in logic.find_overdue(
            [handoff], timezone.localdate()
        )
    return render(request, 'shelf/dashboard.html', context)


@login_required(login_url='login')
def browse_view(request):
    query = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()
    mode = request.GET.get('mode', '').strip()

    # Classmates' items that are active and available
    items_qs = Item.objects.filter(
        paused=False, qty__gt=0
    ).exclude(owner=request.user).select_related('owner', 'owner__profile')

    if query:
        items_qs = items_qs.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )

    if category and category != 'All':
        items_qs = items_qs.filter(category=category)

    if mode in ('give', 'lend'):
        items_qs = items_qs.filter(listing=mode)

    items = list(items_qs)

    posted = {item.id: _posted_label(item.created_at) for item in items}
    categories = ['All'] + [choice[0] for choice in Item.CATEGORY_CHOICES]

    listing_ctx = _listing_context()

    context = {
        'items': items,
        'query': query,
        'category': category if category else 'All',
        'categories': categories,
        'mode': mode,
        'posted': posted,
        'share_form': ShareItemForm(),
        'request_form': RequestPostForm(),
        'listing_choices': listing_ctx['listing_choices'],
        'listing_hints': listing_ctx['listing_hints'],
        'condition_prefs': listing_ctx['condition_prefs'],
        'max_note': listing_ctx['max_note'],
        'open_modal': request.GET.get('modal', ''),
    }
    return render(request, 'shelf/browse.html', context)


@login_required(login_url='login')
def item_detail_view(request, item_id):
    item = get_object_or_404(
        Item.objects.select_related('owner', 'owner__profile'),
        pk=item_id
    )

    # Check if current user has an active request for this item
    requested = ShelfRequest.objects.filter(
        item=item,
        requester=request.user,
        status__in=('requested', 'matched', 'lent')
    ).exists()

    # Get optional open request if coming from matches
    open_req_id = request.GET.get('open_request') or request.GET.get('request')
    open_request = None
    if open_req_id:
        open_request = ShelfRequest.objects.filter(
            pk=open_req_id,
            requester=request.user,
            status='open'
        ).first()

    # Initialize borrow form for lent items
    borrow_form = None
    if item.is_lend:
        initial_data = {}
        if open_request:
            initial_data['open_request'] = open_request.id
        borrow_form = BorrowForm(item=item, initial=initial_data)

    listing_ctx = _listing_context()

    context = {
        'item': item,
        'requested': requested,
        'posted': _posted_label(item.created_at),
        'today': timezone.localdate(),
        'borrow_form': borrow_form,
        'open_request': open_request,
        'share_form': ShareItemForm(),
        'request_form': RequestPostForm(),
        'listing_choices': listing_ctx['listing_choices'],
        'listing_hints': listing_ctx['listing_hints'],
        'condition_prefs': listing_ctx['condition_prefs'],
        'max_note': listing_ctx['max_note'],
        'open_modal': request.GET.get('modal', ''),
    }
    return render(request, 'shelf/item_detail.html', context)


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
    item = get_object_or_404(Item, pk=item_id, paused=False, qty__gt=0)

    if item.owner == request.user:
        messages.error(request, "You cannot request your own item.")
        return redirect('item_detail', item_id=item.id)

    already_requested = ShelfRequest.objects.filter(
        item=item,
        requester=request.user,
        status__in=('requested', 'matched', 'lent')
    ).exists()

    if already_requested:
        messages.info(request, "You have already requested this item.")
        return redirect('item_detail', item_id=item.id)

    if item.is_lend:
        form = BorrowForm(request.POST, item=item)
        if not form.is_valid():
            open_req_id = form.data.get('open_request') or request.POST.get('open_request')
            open_request = None
            if open_req_id:
                open_request = ShelfRequest.objects.filter(pk=open_req_id, requester=request.user, status='open').first()

            listing_ctx = _listing_context()
            context = {
                'item': item,
                'requested': False,
                'posted': _posted_label(item.created_at),
                'today': timezone.localdate(),
                'borrow_form': form,
                'open_request': open_request,
                'share_form': ShareItemForm(),
                'request_form': RequestPostForm(),
                'listing_choices': listing_ctx['listing_choices'],
                'listing_hints': listing_ctx['listing_hints'],
                'condition_prefs': listing_ctx['condition_prefs'],
                'max_note': listing_ctx['max_note'],
                'open_modal': '',
            }
            return render(request, 'shelf/item_detail.html', context)

        # Valid Borrow Form
        borrow_from = form.cleaned_data['borrow_from']
        return_by = form.cleaned_data['return_by']
        note = form.cleaned_data['note']
        open_req_id = form.cleaned_data.get('open_request')

        if open_req_id:
            shelf_request = get_object_or_404(ShelfRequest, pk=open_req_id, requester=request.user, status='open')
            if logic.allowed_qty(shelf_request, 'seeker', 'requested') is None:
                messages.error(request, 'This request can no longer be sent.')
                return redirect('item_detail', item_id=item.id)
            shelf_request.item = item
            shelf_request.is_lend = True
            shelf_request.borrow_from = borrow_from
            shelf_request.return_by = return_by
            shelf_request.note = note or shelf_request.note
            shelf_request.status = 'requested'
            shelf_request.save()
        else:
            ShelfRequest.objects.create(
                requester=request.user,
                item=item,
                name=item.name,
                category=item.category,
                note=note,
                status='requested',
                is_lend=True,
                borrow_from=borrow_from,
                return_by=return_by,
                location=item.location
            )
        messages.success(request, f"Borrow request for '{item.name}' sent to owner.")

    else:
        # Give Away Item
        open_req_id = request.POST.get('open_request')
        if open_req_id:
            shelf_request = get_object_or_404(ShelfRequest, pk=open_req_id, requester=request.user, status='open')
            if logic.allowed_qty(shelf_request, 'seeker', 'requested') is None:
                messages.error(request, 'This request can no longer be sent.')
                return redirect('item_detail', item_id=item.id)
            shelf_request.item = item
            shelf_request.is_lend = False
            shelf_request.status = 'requested'
            shelf_request.save()
        else:
            ShelfRequest.objects.create(
                requester=request.user,
                item=item,
                name=item.name,
                category=item.category,
                status='requested',
                is_lend=False,
                location=item.location
            )
        messages.success(request, f"Request for '{item.name}' sent to owner.")

    return redirect('item_detail', item_id=item.id)


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
    # Confirm ownership first, then handle a stale or repeated form submit
    # without exposing Django's debug 404 page to the user.
    shelf_request = get_object_or_404(
        ShelfRequest.objects.select_related('item'), pk=request_id, item__owner=request.user
    )
    if shelf_request.status != 'requested':
        messages.error(request, 'This request is no longer pending. Refresh the dashboard and try again.')
        return redirect('dashboard')
    if not form.is_valid():
        _mark_request_viewer(shelf_request, request.user)
        context = _dashboard_context(request.user, accept=shelf_request, accept_form=form)
        return render(request, 'shelf/dashboard.html', context)
    with transaction.atomic():
        try:
            shelf_request = ShelfRequest.objects.select_for_update().get(
                pk=request_id, item__owner=request.user, status='requested',
            )
        except ShelfRequest.DoesNotExist:
            messages.error(request, 'This request is no longer pending. Refresh the dashboard and try again.')
            return redirect('dashboard')
        item = Item.objects.select_for_update().get(pk=shelf_request.item_id)
        new_qty = logic.allowed_qty(shelf_request, 'sharer', 'matched', item)
        if new_qty is None:
            messages.error(request, 'This item is no longer available to accept.')
            return redirect('dashboard')
        item.qty = new_qty
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
    if logic.allowed_qty(shelf_request, 'sharer', 'declined', shelf_request.item) is None:
        messages.error(request, 'This request can no longer be declined.')
        return redirect('dashboard')
    shelf_request.status = 'declined'
    shelf_request.save(update_fields=['status', 'updated_at'])
    messages.success(request, 'Request declined.')
    return redirect('dashboard')


@login_required(login_url='login')
@require_POST
def complete_incoming_view(request, request_id):
    shelf_request = get_object_or_404(ShelfRequest, pk=request_id, item__owner=request.user, status='matched')
    target = 'lent' if shelf_request.is_lend else 'fulfilled'
    if logic.allowed_qty(shelf_request, 'sharer', target, shelf_request.item) is None:
        messages.error(request, 'This handoff can no longer be completed.')
        return redirect('dashboard')
    shelf_request.status = target
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
        new_qty = logic.allowed_qty(shelf_request, 'sharer', 'returned', item)
        if new_qty is None:
            messages.error(request, 'This item can no longer be marked as returned.')
            return redirect('dashboard')
        item.qty = new_qty
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
        item = Item.objects.select_for_update().get(pk=shelf_request.item_id) if shelf_request.item_id else None
        new_qty = logic.allowed_qty(shelf_request, 'seeker', 'cancelled', item)
        if new_qty is None:
            messages.error(request, 'This request can no longer be cancelled.')
            return redirect('dashboard')
        if item and new_qty != item.qty:
            item.qty = new_qty
            item.save(update_fields=['qty'])
        shelf_request.status = 'cancelled'
        shelf_request.save(update_fields=['status', 'updated_at'])
    messages.success(request, 'Request cancelled.')
    return redirect('dashboard')


@login_required(login_url='login')
@require_POST
def confirm_handoff_view(request, request_id):
    shelf_request = get_object_or_404(ShelfRequest, pk=request_id, requester=request.user, status='matched')
    target = 'lent' if shelf_request.is_lend else 'fulfilled'
    if logic.allowed_qty(shelf_request, 'seeker', target, shelf_request.item) is None:
        messages.error(request, 'This handoff can no longer be confirmed.')
        return redirect('dashboard')
    shelf_request.status = target
    shelf_request.save(update_fields=['status', 'updated_at'])
    messages.success(request, 'Borrowing started.' if shelf_request.is_lend else 'Handoff confirmed. Thanks!')
    return redirect('dashboard')


@login_required(login_url='login')
@require_POST
def ask_for_match_view(request, request_id, item_id):
    shelf_request = get_object_or_404(ShelfRequest, pk=request_id, requester=request.user, status='open')
    item = get_object_or_404(Item, pk=item_id, paused=False, qty__gt=0)
    if not logic.is_match(item, shelf_request):
        messages.error(request, 'That item is not an available match for your request.')
        return redirect('dashboard')
    if logic.allowed_qty(shelf_request, 'seeker', 'requested') is None:
        messages.error(request, 'This request can no longer be sent.')
        return redirect('dashboard')
    shelf_request.item = item
    shelf_request.is_lend = False
    shelf_request.status = 'requested'
    shelf_request.save(update_fields=['item', 'is_lend', 'status', 'updated_at'])
    messages.success(request, 'Your request was sent to the student sharing this item.')
    return redirect('dashboard')

def _greeting_for_hour(hour):
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


def _matches_by_request(open_requests, limit=6):
    """Suggested items for each open request: {request id: [items]}.

    The database only narrows the candidates down to the right categories;
    Prolog's matches/2 rule decides which items actually match. One Prolog call
    covers every request on the page.
    """
    open_requests = [r for r in open_requests if r.status == 'open']
    if not open_requests:
        return {}
    candidates = {
        item.pk: item
        for item in Item.objects.filter(
            category__in={r.category for r in open_requests}, paused=False, qty__gt=0,
        ).select_related('owner', 'owner__profile')
    }
    found = {r.pk: [] for r in open_requests}
    for request_id, item_id in logic.find_matches(candidates.values(), open_requests):
        if len(found[request_id]) < limit:
            found[request_id].append(candidates[item_id])
    return found


def _matching_items(shelf_request):
    return _matches_by_request([shelf_request]).get(shelf_request.pk, [])


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
    today = timezone.localdate()
    all_items = list(Item.objects.filter(owner=user).select_related('owner', 'owner__profile'))
    incoming_requests = ShelfRequest.objects.filter(
        item__owner=user,
        status__in=('requested', 'matched', 'lent'),
    ).select_related('requester', 'requester__profile', 'item', 'item__owner', 'item__owner__profile')

    own_requests = list(ShelfRequest.objects.filter(requester=user).select_related(
        'requester', 'requester__profile', 'item', 'item__owner', 'item__owner__profile'
    ))
    incoming_requests = list(incoming_requests)
    on_loan = [r for r in [*incoming_requests, *own_requests, *([handoff] if handoff else [])] if r.status == 'lent']
    overdue_ids = logic.find_overdue(on_loan, today)
    matches = _matches_by_request(own_requests)

    incoming = []
    for shelf_request in incoming_requests:
        _mark_request_viewer(shelf_request, user)
        item = shelf_request.item
        incoming.append({
            'request': shelf_request,
            'item': item,
            'can_accept': shelf_request.status == 'requested' and not item.paused and item.qty > 0,
            'posted': _posted_label(shelf_request.created_at),
            'overdue': shelf_request.pk in overdue_ids,
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

    request_rows = []
    # Finished requests (fulfilled, returned, cancelled, declined) drop off the list.
    # They stay in the database, so the stats and history still count them.
    for shelf_request in (r for r in own_requests if not r.is_closed):
        _mark_request_viewer(shelf_request, user)
        request_rows.append({
            'request': shelf_request,
            'posted': _posted_label(shelf_request.created_at),
            'matches': matches.get(shelf_request.pk, []),
            'overdue': shelf_request.pk in overdue_ids,
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
        'handoff_matches': _matching_items(handoff) if handoff and handoff.status == 'open' else [],
        'handoff_overdue': bool(handoff and handoff.pk in overdue_ids),
        'open_modal': open_modal,
        'dashboard_url': '/dashboard/',
        'today': today,
        'current_time': timezone.localtime().strftime('%H:%M'),
    }
    if handoff:
        _mark_request_viewer(handoff, user)
    return context
