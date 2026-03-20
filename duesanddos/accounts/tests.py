from accounts.models import CustomUser, Profile, Household
from django.test import TestCase, Client
from django.urls import reverse

class RegistrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.registration_url = reverse('register')
        self.login_url = reverse('login')

    def test_registration_page_loads(self):
        """Check if the signup page is accessible"""
        response = self.client.get(self.registration_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/register.html')

    def test_profile_created_on_registration(self):
        """Verify that a Profile object is created alongside the User"""
        user_data = {
            'username': 'profileuser',
            'firstName': 'Profile',
            'lastName': 'Test',
            'email': 'profile@nyu.edu',
            'password': 'ComplexPassword123!',
            'confirmPassword': 'ComplexPassword123!'
        }
        # 1. First, send the post request to create the user
        self.client.post(self.registration_url, data=user_data)
        
        # 2. THEN, query the database inside the function
        user = CustomUser.objects.get(username='profileuser')
        self.assertTrue(Profile.objects.filter(user=user).exists())

    def test_successful_registration(self):
        """Test creating a new user through the form"""
        user_data = {
            'username': 'testuser',
            'firstName': 'Test',
            'lastName': 'User',
            'email': 'test@nyu.edu',
            'password': 'ComplexPassword123!',
            'confirmPassword': 'ComplexPassword123!'
        }
        response = self.client.post(self.registration_url, data=user_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(CustomUser.objects.filter(username='testuser').exists())

    def test_registration_invalid_password_match(self):
        """Test that mismatched passwords return an error"""
        user_data = {
            'username': 'failuser',
            'firstName': 'Fail',
            'lastName': 'User',
            'email': 'fail@nyu.edu',
            'password': 'Password123',
            'confirmPassword': 'DifferentPassword456'
        }
        response = self.client.post(self.registration_url, data=user_data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(CustomUser.objects.filter(username='failuser').exists())

    def test_create_household_success(self):
        # 1. Create a user and log them in so request.user is available
        user = CustomUser.objects.create_user(
            username='householdadmin', 
            email='admin@nyu.edu', 
            password='ComplexPassword123!'
        )
        self.client.login(username='householdadmin', password='ComplexPassword123!')
        
        user_data = {
            'name': 'My New Home',
            'description': 'A test household'
        }
        
        # 2. Perform the post request
        response = self.client.post(reverse('create_household'), data=user_data)
        
        # 3. Debugging: If this fails, print errors to see why
        if response.status_code != 302:
            print(response.context['form'].errors)
            
        # 4. Assertions
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Household.objects.filter(name='My New Home').exists())