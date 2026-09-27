from rest_framework import serializers

from .models import DownloadRecord, DownloadTemplate


class DownloadTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DownloadTemplate
        fields = "__all__"


class DownloadRecordSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source="book.title", read_only=True)
    template_name = serializers.CharField(source="template.name", read_only=True, default="-")
    created_by_name = serializers.CharField(source="created_by.username", read_only=True, default="-")

    class Meta:
        model = DownloadRecord
        fields = "__all__"
