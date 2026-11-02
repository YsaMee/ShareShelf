from django.db import models
from django.contrib.auth.models import User

PROGRAM_CHOICES = [
    ('BSCS', 'BS Computer Science'),
    ('BSIT', 'BS Information Technology'),
    ('BSIS', 'BS Information Systems'),
    ('BSECE', 'BS Electronics Engineering'),
    ('BSBA', 'BS Business Administration'),
]

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    full_name = models.CharField(max_length=150)
    program = models.CharField(max_length=50, choices=PROGRAM_CHOICES)
    school = models.CharField(max_length=150, default="Mapúa MCM")

    def __str__(self):
        return self.full_name

    @property
    def name(self):
        return self.full_name or self.user.get_full_name() or self.user.username

    @property
    def first_name(self):
        return self.full_name.split()[0] if self.full_name else self.user.username

    @property
    def initials(self):
        parts = self.name.split()
        if len(parts) >= 2:
            return f"{parts[0][0]}{parts[-1][0]}".upper()
        return self.name[:2].upper() if self.name else "U"