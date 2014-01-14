from django.db import models


class Item(models.Model):
    text = models.TextField()
    list = models.ForeignKey('List')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class List(models.Model):
    pass