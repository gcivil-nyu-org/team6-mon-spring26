from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from households.models import Household, HouseholdMember
from accounts.models import Profile

User = get_user_model()

class HouseholdSwitchingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password123", email="test@example.com")
        self.client = Client()
        self.client.login(username="testuser", password="password123")
        
        self.household1 = Household.objects.create(name="House 1")
        self.household2 = Household.objects.create(name="House 2")
        
        # Add user to both households
        HouseholdMember.objects.create(user=self.user, household=self.household1)
        HouseholdMember.objects.create(user=self.user, household=self.household2)
        
        self.profile = self.user.profile
        self.profile.active_household = self.household1
        self.profile.save()

    def test_switch_household_success(self):
        """Test successfully switching to another household the user belongs to."""
        response = self.client.get(reverse('switch_household', args=[self.household2.id]))
        
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.active_household, self.household2)
        self.assertRedirects(response, reverse('dashboard'))

    def test_switch_household_invalid_id(self):
        """Test switching to a household the user does NOT belong to."""
        other_user = User.objects.create_user(username="otheruser", password="password123", email="other@example.com")
        other_household = Household.objects.create(name="Other House")
        
        response = self.client.get(reverse('switch_household', args=[other_household.id]))
        
        self.profile.refresh_from_db()
        # Should NOT change
        self.assertEqual(self.profile.active_household, self.household1)
        self.assertRedirects(response, reverse('dashboard'))

    def test_switch_household_referer_redirect(self):
        """Test that switching redirects back to the referer if available."""
        referer_url = reverse('chores_list')
        response = self.client.get(
            reverse('switch_household', args=[self.household2.id]),
            HTTP_REFERER=referer_url
        )
        
        self.assertRedirects(response, referer_url)
