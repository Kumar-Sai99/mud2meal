from django.db import models
from django.contrib.auth.models import User


# ── CATEGORY ────────────────────────────────────────
class Category(models.Model):
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=10, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering            = ['name']
        verbose_name_plural = 'Categories'


# ── FARMER PROFILE ───────────────────────────────────
class FarmerProfile(models.Model):
    user        = models.OneToOneField(User, on_delete=models.CASCADE, related_name='farmer')
    phone       = models.CharField(max_length=15, blank=True)
    address     = models.TextField(blank=True)
    district    = models.CharField(max_length=100, blank=True)
    state       = models.CharField(max_length=100, blank=True)
    photo       = models.ImageField(upload_to='farmers/', blank=True, null=True)
    bio         = models.TextField(blank=True)
    farm_id     = models.CharField(max_length=100, blank=True)
    specialty   = models.CharField(max_length=200, blank=True)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} — Farmer"


# ── BUYER PROFILE ────────────────────────────────────
class BuyerProfile(models.Model):
    user             = models.OneToOneField(User, on_delete=models.CASCADE, related_name='buyer')
    phone            = models.CharField(max_length=15, blank=True)
    district         = models.CharField(max_length=100, blank=True)
    state            = models.CharField(max_length=100, blank=True)
    delivery_address = models.TextField(blank=True)

    def __str__(self):
        return f"{self.user.username} — Buyer"


# ── CROP ─────────────────────────────────────────────
class Crop(models.Model):
    UNIT_CHOICES = [
        ('kg',      'Kilogram'),
        ('quintal', 'Quintal'),
        ('ton',     'Ton'),
        ('dozen',   'Dozen'),
        ('piece',   'Piece'),
    ]
    STATUS_CHOICES = [
        ('available',   'Available'),
        ('sold',        'Sold'),
        ('unavailable', 'Unavailable'),
    ]
    farmer      = models.ForeignKey(FarmerProfile, on_delete=models.CASCADE, related_name='crops')
    category    = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='crops')
    name        = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price       = models.CharField(max_length=100)
    unit        = models.CharField(max_length=20, choices=UNIT_CHOICES, default='kg')
    quantity    = models.CharField(max_length=100, blank=True)
    location    = models.CharField(max_length=200, blank=True)
    district    = models.CharField(max_length=100, blank=True)
    state       = models.CharField(max_length=100, blank=True)
    photo       = models.ImageField(upload_to='crops/', blank=True, null=True)
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    is_featured = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} by {self.farmer.user.username}"

    class Meta:
        ordering = ['-created_at']


# ── ENQUIRY ──────────────────────────────────────────
class Enquiry(models.Model):
    crop    = models.ForeignKey(Crop, on_delete=models.CASCADE, related_name='enquiries')
    buyer   = models.ForeignKey(BuyerProfile, on_delete=models.CASCADE, related_name='enquiries')
    message = models.TextField()
    phone   = models.CharField(max_length=15, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.buyer.user.username} enquired about {self.crop.name}"

    class Meta:
        ordering            = ['-created']
        verbose_name_plural = 'Enquiries'


# ── ENQUIRY REPLY ─────────────────────────────────────
class EnquiryReply(models.Model):
    enquiry = models.OneToOneField(
        Enquiry, on_delete=models.CASCADE, related_name='reply'
    )
    message = models.TextField()
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reply to {self.enquiry}"