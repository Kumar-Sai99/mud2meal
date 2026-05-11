from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Enquiry, FarmerProfile, BuyerProfile


# ── AUTO CREATE PROFILE WHEN USER REGISTERS ──────────
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    When a new User is created, this signal fires automatically.
    But we only create profile if role is known — so we skip here
    and let register_view handle it. This is just a safety fallback.
    """
    pass


# ── NOTIFY FARMER WHEN ENQUIRY IS RECEIVED ───────────
@receiver(post_save, sender=Enquiry)
def notify_farmer_on_enquiry(sender, instance, created, **kwargs):
    """
    Fires every time an Enquiry is saved.
    If it's a NEW enquiry (created=True), print notification.
    Later we can replace print with email or real notification.
    """
    if created:
        farmer_user = instance.crop.farmer.user
        buyer_user  = instance.buyer.user
        crop_name   = instance.crop.name

        print(f"\n🔔 NEW ENQUIRY ALERT!")
        print(f"   Farmer : {farmer_user.username}")
        print(f"   Buyer  : {buyer_user.username}")
        print(f"   Crop   : {crop_name}")
        print(f"   Message: {instance.message[:50]}...")
        print(f"   Phone  : {instance.phone}\n")
        