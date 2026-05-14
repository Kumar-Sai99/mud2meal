from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User



# ── AUTO CREATE PROFILE WHEN USER REGISTERS ──────────
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    When a new User is created, this signal fires automatically.
    But we only create profile if role is known — so we skip here
    and let register_view handle it. This is just a safety fallback.
    """
    pass


        