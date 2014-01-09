from django.db import models


class Item(models.Model):
    text = models.TextField()
    list = models.ForeignKey('List')


class List(models.Model):
    pass