from django.db import models
from django.contrib.auth.models import User
from django.db.models import Avg


class Category(models.Model):
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=10, blank=True)
    def __str__(self): return self.name
    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Categories'


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
    def __str__(self): return f"{self.user.username} — Farmer"


class BuyerProfile(models.Model):
    user             = models.OneToOneField(User, on_delete=models.CASCADE, related_name='buyer')
    phone            = models.CharField(max_length=15, blank=True)
    district         = models.CharField(max_length=100, blank=True)
    state            = models.CharField(max_length=100, blank=True)
    delivery_address = models.TextField(blank=True)
    def __str__(self): return f"{self.user.username} — Buyer"


class Crop(models.Model):
    UNIT_CHOICES   = [('kg','Kilogram'),('quintal','Quintal'),('ton','Ton'),('dozen','Dozen'),('piece','Piece')]
    STATUS_CHOICES = [('available','Available'),('sold','Sold'),('unavailable','Unavailable')]

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
    emoji       = models.CharField(max_length=10, blank=True)
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    is_featured = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta: ordering = ['-created_at']
    def __str__(self): return f"{self.name} by {self.farmer.user.username}"

    @property
    def avg_rating(self):
        r = self.ratings.aggregate(avg=Avg('stars'))['avg']
        return round(r, 1) if r else None

    @property
    def rating_count(self): return self.ratings.count()

    @property
    def wishlist_count(self): return self.wishlisted_by.count()



class Enquiry(models.Model):
    crop    = models.ForeignKey(Crop, on_delete=models.CASCADE, related_name='enquiries')
    buyer   = models.ForeignKey(BuyerProfile, on_delete=models.CASCADE, related_name='enquiries')
    message = models.TextField()
    phone   = models.CharField(max_length=15, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    def __str__(self): return f"{self.buyer.user.username} → {self.crop.name}"
    class Meta:
        ordering = ['-created']
        verbose_name_plural = 'Enquiries'


class EnquiryReply(models.Model):
    enquiry = models.OneToOneField(Enquiry, on_delete=models.CASCADE, related_name='reply')
    message = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    def __str__(self): return f"Reply to {self.enquiry}"


class ChatRoom(models.Model):
    farmer  = models.ForeignKey(FarmerProfile, on_delete=models.CASCADE, related_name='chat_rooms')
    buyer   = models.ForeignKey(BuyerProfile,  on_delete=models.CASCADE, related_name='chat_rooms')
    crop    = models.ForeignKey(Crop, on_delete=models.CASCADE, related_name='chat_rooms')
    created = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ['farmer', 'buyer', 'crop']
        ordering        = ['-created']
    def __str__(self): return f"{self.buyer.user.username} ↔ {self.farmer.user.username} — {self.crop.name}"
    def get_room_name(self): return f"chat_{self.pk}"


class ChatMessage(models.Model):
    room      = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender    = models.ForeignKey(User, on_delete=models.CASCADE)
    message   = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read   = models.BooleanField(default=False)
    class Meta: ordering = ['timestamp']
    def __str__(self): return f"{self.sender.username}: {self.message[:30]}"


class Rating(models.Model):
    crop    = models.ForeignKey(Crop, on_delete=models.CASCADE, related_name='ratings')
    buyer   = models.ForeignKey(BuyerProfile, on_delete=models.CASCADE, related_name='ratings')
    stars   = models.PositiveSmallIntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    review  = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ('crop', 'buyer')
        ordering = ['-created']
    def __str__(self): return f"{self.buyer.user.username} rated {self.crop.name} {self.stars}★"


class Wishlist(models.Model):
    buyer = models.ForeignKey(BuyerProfile, on_delete=models.CASCADE, related_name='wishlist')
    crop  = models.ForeignKey(Crop, on_delete=models.CASCADE, related_name='wishlisted_by')
    added = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ('buyer', 'crop')
        ordering = ['-added']
    def __str__(self): return f"{self.buyer.user.username} ♥ {self.crop.name}"


class Order(models.Model):
    DELIVERY_CHOICES = [
        ('pickup', 'Self Pickup'),
        ('delivery', 'Home Delivery'),
    ]
    PAYMENT_CHOICES = [
        ('cod', 'Cash on Delivery'),
        ('upi', 'UPI'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('dispatched', 'Dispatched'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    crop        = models.ForeignKey(Crop, on_delete=models.CASCADE, related_name='orders')
    buyer       = models.ForeignKey(BuyerProfile, on_delete=models.CASCADE, related_name='orders')
    farmer      = models.ForeignKey(FarmerProfile, on_delete=models.CASCADE, related_name='orders')
    quantity    = models.PositiveIntegerField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    delivery    = models.CharField(max_length=20, choices=DELIVERY_CHOICES)
    payment     = models.CharField(max_length=20, choices=PAYMENT_CHOICES)
    address     = models.TextField(blank=True)  # for home delivery
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    note        = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta: ordering = ['-created_at']
    def __str__(self): return f"Order #{self.pk} — {self.crop.name} by {self.buyer.user.username}"