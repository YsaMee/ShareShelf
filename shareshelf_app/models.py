from types import SimpleNamespace

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils import timezone

LOCATION_CHOICES = [
    ('Library', 'Library'), ('Student Lounge', 'Student Lounge'),
    ('Main Lobby', 'Main Lobby'), ('Other campus spot', 'Other campus spot'),
]

PROGRAM_CHOICES = [
    ('BSCS', 'BS Computer Science'),
    ('BSIT', 'BS Information Technology'),
    ('BSIS', 'BS Information Systems'),
    ('BSECE', 'BS Electronics Engineering'),
    ('BSBA', 'BS Business Administration'),
    ('BS Arch', 'BS Architecture')
]

YEAR_LEVEL_CHOICES = [(1, '1st Year'), (2, '2nd Year'), (3, '3rd Year'), (4, '4th Year'), (5, '5th Year')]

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    full_name = models.CharField(max_length=150)
    program = models.CharField(max_length=50, choices=PROGRAM_CHOICES)
    school = models.CharField(max_length=150, default="Mapúa MCM")
    display_name = models.CharField(max_length=60, blank=True)
    year_level = models.PositiveSmallIntegerField(choices=YEAR_LEVEL_CHOICES, null=True, blank=True)
    bio = models.CharField(max_length=300, blank=True)
    pickup_spot = models.CharField(max_length=100, choices=LOCATION_CHOICES, blank=True)
    def __str__(self):
        return self.full_name

    @property
    def name(self):
        return self.display_name or self.full_name or self.user.get_full_name() or self.user.username

    @property
    def first_name(self):
        name = self.display_name or self.full_name
        return name.split()[0] if name else self.user.username

    @property
    def initials(self):
        parts = self.name.split()
        if len(parts) >= 2:
            return f"{parts[0][0]}{parts[-1][0]}".upper()
        return self.name[:2].upper() if self.name else "U"


class Item(models.Model):
    """OOP model for an item a student gives away or lends."""

    LISTING_CHOICES = [('give', 'Give away'), ('lend', 'Lend temporarily')]
    CATEGORY_CHOICES = [
        ('Stationery', 'Stationery'),
        ('Drafting & Arts (Architecture, Fine Arts)', 'Drafting & Arts (Architecture, Fine Arts)'),
        ('Books & Textbooks', 'Books & Textbooks'),
        ('Electronics', 'Electronics'),
        ('Other', 'Other'),
    ]
    CONDITION_CHOICES = [
        ('New', 'New'), ('Gently Used', 'Gently Used'), ('Functional', 'Functional'),
    ]
    LEND_LIMIT_CHOICES = [
        (7, 'Up to 1 week'), (14, 'Up to 2 weeks'), (30, 'Up to 1 month'),
    ]
    LOCATION_CHOICES = LOCATION_CHOICES

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shared_items')
    name = models.CharField(max_length=80)
    listing = models.CharField(max_length=8, choices=LISTING_CHOICES, default='give')
    qty = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(20)])
    category = models.CharField(max_length=80, choices=CATEGORY_CHOICES)
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES)
    lend_limit = models.PositiveSmallIntegerField(choices=LEND_LIMIT_CHOICES, blank=True, null=True)
    location = models.CharField(max_length=100, choices=LOCATION_CHOICES)
    description = models.CharField(max_length=500, blank=True)
    icon = models.CharField(max_length=30, default='package')
    tone = models.CharField(max_length=20, default='purple')
    paused = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return self.name

    @property
    def is_lend(self):
        return self.listing == 'lend'

    @property
    def listing_label(self):
        return self.get_listing_display()


class Request(models.Model):
    """OOP model for a student's request and its handoff lifecycle."""

    STATUS_CHOICES = [
        ('open', 'Open'), ('requested', 'Requested'), ('matched', 'Matched'),
        ('lent', 'Lent out'), ('returned', 'Returned'), ('fulfilled', 'Fulfilled'),
        ('cancelled', 'Cancelled'), ('declined', 'Declined'),
    ]
    PREFERENCE_CHOICES = [
        ('Flexible', 'Flexible'), ('New', 'New'),
        ('Gently Used', 'Gently Used'), ('Functional', 'Functional'),
    ]

    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shelf_requests')
    item = models.ForeignKey(Item, on_delete=models.SET_NULL, related_name='requests', null=True, blank=True)
    name = models.CharField(max_length=80)
    category = models.CharField(max_length=80, choices=Item.CATEGORY_CHOICES)
    preference = models.CharField(max_length=20, choices=PREFERENCE_CHOICES, default='Flexible')
    note = models.CharField(max_length=200, blank=True)
    needed_by = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=100, choices=Item.LOCATION_CHOICES, blank=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='open')
    is_lend = models.BooleanField(default=False)
    borrow_from = models.DateField(null=True, blank=True)
    return_by = models.DateField(null=True, blank=True)
    meetup_location = models.CharField(max_length=100, blank=True)
    meetup_date = models.DateField(null=True, blank=True)
    meetup_time = models.TimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return f'{self.name} ({self.get_status_display()})'

    @property
    def status_label(self):
        labels = {
            'open': 'Open', 'requested': 'Pending' if getattr(self, '_viewer_is_sharer', False) else 'Requested',
            'matched': 'Matched', 'lent': 'Lent out', 'returned': 'Returned',
            'fulfilled': 'Fulfilled', 'cancelled': 'Cancelled', 'declined': 'Declined',
        }
        return labels.get(self.status, self.get_status_display())

    @property
    def condition_label(self):
        return 'Any condition' if self.preference == 'Flexible' else self.preference

    @property
    def is_closed(self):
        return self.status in {'fulfilled', 'returned', 'cancelled', 'declined'}

    @property
    def other_party(self):
        owner_id = self.item.owner_id if self.item_id else None
        viewer_id = getattr(self, '_viewer_id', self.requester_id)
        return self.item.owner.profile if owner_id and viewer_id == self.requester_id else self.requester.profile

    @property
    def meetup(self):
        if not (self.meetup_location and self.meetup_date and self.meetup_time):
            return None
        day = self.meetup_date.strftime('%b %d').replace(' 0', ' ')
        label = f'{day}, {self.meetup_time.strftime("%I:%M %p").lstrip("0")}'
        return SimpleNamespace(location=self.meetup_location, label=label)


# Functional style: this pure predicate depends only on its arguments and has no side effects.
def item_matches_request(item, request_obj):
    return (
        item.owner_id != request_obj.requester_id
        and item.qty > 0
        and not item.paused
        and item.category == request_obj.category
        and (request_obj.preference == 'Flexible' or item.condition == request_obj.preference)
    )

