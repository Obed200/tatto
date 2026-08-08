from django.db import models


class SiteSettings(models.Model):
    whatsapp_community_link = models.URLField(blank=True)
    telegram_community_link = models.URLField(blank=True)
    contact_phone = models.CharField(max_length=30, blank=True)
    support_email = models.EmailField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Site settings"
        verbose_name_plural = "Site settings"

    def __str__(self):
        return "Tatto Mark Investment community links"

    @classmethod
    def load(cls):
        settings, _ = cls.objects.get_or_create(pk=1)
        return settings


class Announcement(models.Model):
    title = models.CharField(max_length=120)
    message = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
