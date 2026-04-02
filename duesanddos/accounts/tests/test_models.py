from django.test import TestCase
from accounts.models import CustomUser, Profile, UploadToPath
from unittest.mock import Mock, patch

TEST_PASSWORD = "TestPass123!"


class CustomUserModelTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="testuser",
            email="test@example.com",
            password=TEST_PASSWORD,
        )

    def test_str_returns_username(self):
        self.assertEqual(str(self.user), "testuser")


class ProfileModelTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="testuser",
            email="test@example.com",
            password=TEST_PASSWORD,
        )
        self.profile = Profile.objects.create(user=self.user)

    def test_str_returns_formatted_string(self):
        self.assertEqual(str(self.profile), "testuser's profile")

    def test_default_bio_is_empty(self):
        self.assertEqual(self.profile.bio, "")

    def test_default_notifications_enabled_is_true(self):
        self.assertTrue(self.profile.notifications_enabled)

    def test_default_avatar_is_falsy(self):
        self.assertFalse(self.profile.avatar)

    def test_save_deletes_old_avatar_when_avatar_changes(self):
        old_file = Mock()
        old_file.name = "profile_pics/old.gif"
        old_file.storage.delete = Mock()

        new_file = Mock()

        with patch("accounts.models.Profile.objects.get") as mock_get, patch(
            "django.db.models.Model.save", return_value=None
        ):
            mock_get.return_value = Mock(avatar=old_file)
            self.profile.avatar = new_file
            self.profile.save()

        old_file.storage.delete.assert_called_once_with("profile_pics/old.gif")


class UploadToPathTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="uploadtest",
            email="upload@example.com",
            password=TEST_PASSWORD,
        )
        self.profile = Profile.objects.create(user=self.user)

    def test_upload_path_has_correct_category(self):
        uploader = UploadToPath("test_cat")
        path = uploader(self.profile, "photo.jpg")
        self.assertTrue(path.startswith("test_cat/"))

    def test_upload_path_includes_user_pk(self):
        uploader = UploadToPath("test_cat")
        path = uploader(self.profile, "photo.jpg")
        self.assertIn(f"uid_{self.user.pk}", path)

    def test_upload_path_ends_with_jpg(self):
        uploader = UploadToPath("test_cat")
        path = uploader(self.profile, "photo.png")
        self.assertTrue(path.endswith(".png"))

    def test_upload_path_no_extension_defaults_to_jpg(self):
        uploader = UploadToPath("test_cat")
        path = uploader(self.profile, "noext")
        self.assertTrue(path.endswith(".jpg"))

    def test_deconstruct_returns_correct_path(self):
        uploader = UploadToPath("mycat")
        name, args, kwargs = uploader.deconstruct()
        self.assertEqual(name, "accounts.models.UploadToPath")
        self.assertEqual(args, ["mycat"])
        self.assertEqual(kwargs, {})

    def test_upload_path_falls_back_to_unknown_without_user_or_user_id(self):
        class DummyInstance:
            pass

        uploader = UploadToPath("test_cat")
        path = uploader(DummyInstance(), "photo.jpg")
        self.assertIn("uid_unknown", path)
