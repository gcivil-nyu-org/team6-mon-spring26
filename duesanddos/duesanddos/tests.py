from django.test import TestCase
from unittest.mock import patch
from duesanddos.custom_storages import MediaStorage


class CustomStoragesTests(TestCase):
    @patch("storages.backends.s3boto3.S3Boto3Storage.__init__", return_value=None)
    def test_media_storage_properties(self, mock_init):
        """
        Test that MediaStorage has the correct properties.
        Mocking __init__ to avoid connecting to S3 during instantiation.
        """
        storage = MediaStorage()
        self.assertEqual(storage.location, "media")
        self.assertTrue(storage.file_overwrite)
