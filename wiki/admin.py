from django.contrib import admin
from models import WikiPage, SchemaDataIndex, WikiPageRevision

admin.site.register(WikiPage)
admin.site.register(SchemaDataIndex)
admin.site.register(WikiPageRevision)