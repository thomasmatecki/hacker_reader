from django.contrib.contenttypes.fields import GenericForeignKey
from django.db import models


class Story(models.Model):
  item_id = models.IntegerField(unique=True)
  title = models.CharField(max_length=255)
  by = models.CharField(max_length=55)
  descendants = models.IntegerField()
  score = models.IntegerField()
  url = models.URLField(null=True)
  text = models.TextField(null=True)

class Comment(models.Model):
  item_id = models.IntegerField(unique=True)

  parent_type = models.ForeignKey(
    "contenttypes.ContentType", 
    on_delete=models.CASCADE,
  )
  parent_id = models.PositiveIntegerField()
  parent = GenericForeignKey('parent_type', 'parent_id')
  
  by = models.CharField(max_length=55, null=True)
  text = models.TextField(null=True)




