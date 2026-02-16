from django.db import models

class TelegramUser(models.Model):
    """Модель для хранения пользователей Telegram"""
    chat_id = models.BigIntegerField(unique=True, verbose_name="Chat ID")
    username = models.CharField(max_length=255, blank=True, null=True, verbose_name="Username")
    first_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Имя")
    last_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Фамилия")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    
    class Meta:
        verbose_name = "Telegram пользователь"
        verbose_name_plural = "Telegram пользователи"
    
    def __str__(self):
        return f"@{self.username}" if self.username else f"Chat {self.chat_id}"
