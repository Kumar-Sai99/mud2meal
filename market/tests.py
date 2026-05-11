from django.test import TestCase, Client
from django.contrib.auth.models import User
from .models import (
    Category, FarmerProfile, BuyerProfile,
    Crop, Enquiry
)


# ── BASE SETUP ────────────────────────────────────────
class BaseTestCase(TestCase):
    """
    Shared setup for all tests.
    Creates farmer, buyer, category and crop once.
    """
    def setUp(self):
        self.client = Client()

        # create category
        self.category = Category.objects.create(
            name='Vegetables', icon='🥦'
        )

        # create farmer user + profile
        self.farmer_user = User.objects.create_user(
            username   = 'testfarmer',
            password   = 'farmer@123',
            first_name = 'Test',
            last_name  = 'Farmer',
            email      = 'farmer@test.com',
        )
        self.farmer = FarmerProfile.objects.create(
            user     = self.farmer_user,
            phone    = '9876543210',
            district = 'NTR',
            state    = 'Andhra Pradesh',
        )

        # create buyer user + profile
        self.buyer_user = User.objects.create_user(
            username   = 'testbuyer',
            password   = 'buyer@123',
            first_name = 'Test',
            last_name  = 'Buyer',
            email      = 'buyer@test.com',
        )
        self.buyer = BuyerProfile.objects.create(
            user     = self.buyer_user,
            phone    = '9876543211',
            district = 'Warangal',
            state    = 'Telangana',
        )

        # create a crop
        self.crop = Crop.objects.create(
            farmer      = self.farmer,
            category    = self.category,
            name        = 'Tomato',
            price       = '30',
            unit        = 'kg',
            quantity    = '500',
            district    = 'NTR',
            state       = 'Andhra Pradesh',
            status      = 'available',
            is_featured = True,
        )


# ── PAGE LOAD TESTS ───────────────────────────────────
class PageLoadTests(BaseTestCase):

    def test_home_page(self):
        response = self.client.get('/home/')
        self.assertEqual(response.status_code, 200)
        print('✅ Home page loads correctly')

    def test_crop_list_page(self):
        response = self.client.get('/crops/')
        self.assertEqual(response.status_code, 200)
        print('✅ Crop list page loads correctly')

    def test_crop_detail_page(self):
        response = self.client.get(f'/crop/{self.crop.pk}/')
        self.assertEqual(response.status_code, 200)
        print('✅ Crop detail page loads correctly')

    def test_login_page(self):
        response = self.client.get('/login/')
        self.assertEqual(response.status_code, 200)
        print('✅ Login page loads correctly')

    def test_register_page(self):
        response = self.client.get('/register/')
        self.assertEqual(response.status_code, 200)
        print('✅ Register page loads correctly')

    def test_join_page(self):
        response = self.client.get('/join/')
        self.assertEqual(response.status_code, 200)
        print('✅ Join page loads correctly')


# ── AUTH TESTS ────────────────────────────────────────
class AuthTests(BaseTestCase):

    def test_farmer_login(self):
        response = self.client.post('/login/', {
            'username': 'testfarmer',
            'password': 'farmer@123',
        })
        self.assertEqual(response.status_code, 302)
        print('✅ Farmer login works')

    def test_buyer_login(self):
        response = self.client.post('/login/', {
            'username': 'testbuyer',
            'password': 'buyer@123',
        })
        self.assertEqual(response.status_code, 302)
        print('✅ Buyer login works')

    def test_wrong_password(self):
        response = self.client.post('/login/', {
            'username': 'testfarmer',
            'password': 'wrongpassword',
        })
        self.assertIn(response.status_code, [200, 302])
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        print('✅ Wrong password correctly rejected')

    def test_register_farmer(self):
        response = self.client.post('/register/', {
            'username'  : 'newfarmer',
            'email'     : 'newfarmer@test.com',
            'first_name': 'New',
            'last_name' : 'Farmer',
            'password1' : 'farm@1234',
            'password2' : 'farm@1234',
            'phone'     : '9999999999',
            'district'  : 'Guntur',
            'state'     : 'Andhra Pradesh',
            'role'      : 'farmer',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='newfarmer').exists())
        self.assertTrue(
            FarmerProfile.objects.filter(user__username='newfarmer').exists()
        )
        print('✅ Farmer registration works')

    def test_register_buyer(self):
        response = self.client.post('/register/', {
            'username'  : 'newbuyer',
            'email'     : 'newbuyer@test.com',
            'first_name': 'New',
            'last_name' : 'Buyer',
            'password1' : 'buy@1234',
            'password2' : 'buy@1234',
            'phone'     : '8888888888',
            'district'  : 'Hyderabad',
            'state'     : 'Telangana',
            'role'      : 'buyer',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='newbuyer').exists())
        self.assertTrue(
            BuyerProfile.objects.filter(user__username='newbuyer').exists()
        )
        print('✅ Buyer registration works')

    def test_duplicate_username(self):
        response = self.client.post('/register/', {
            'username'  : 'testfarmer',  # already exists
            'email'     : 'another@test.com',
            'first_name': 'Another',
            'last_name' : 'User',
            'password1' : 'test@1234',
            'password2' : 'test@1234',
            'phone'     : '7777777777',
            'district'  : 'NTR',
            'state'     : 'AP',
            'role'      : 'buyer',
        })
        # should NOT create new user
        self.assertEqual(
            User.objects.filter(username='testfarmer').count(), 1
        )
        print('✅ Duplicate username correctly rejected')


# ── CROP TESTS ────────────────────────────────────────
class CropTests(BaseTestCase):

    def test_crop_created(self):
        self.assertEqual(Crop.objects.count(), 1)
        self.assertEqual(self.crop.name, 'Tomato')
        print('✅ Crop created correctly')

    def test_crop_search(self):
        response = self.client.get('/crops/?q=Tomato')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tomato')
        print('✅ Crop search works')

    def test_crop_filter_by_category(self):
        response = self.client.get(f'/crops/?category={self.category.id}')
        self.assertEqual(response.status_code, 200)
        print('✅ Crop filter by category works')

    def test_add_crop_as_farmer(self):
        self.client.login(username='testfarmer', password='farmer@123')
        response = self.client.post('/farmer-dashboard/', {
            'action'     : 'add_crop',
            'name'       : 'Brinjal',
            'price'      : '25',
            'unit'       : 'kg',
            'quantity'   : '200',
            'description': 'Fresh brinjal',
            'district'   : 'NTR',
            'state'      : 'AP',
            'status'     : 'available',
            'is_featured': '0',
            'category'   : self.category.id,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Crop.objects.filter(name='Brinjal').exists())
        print('✅ Farmer can add crop')

    def test_buyer_cannot_add_crop(self):
        self.client.login(username='testbuyer', password='buyer@123')
        response = self.client.get('/farmer-dashboard/')
        self.assertEqual(response.status_code, 302)
        print('✅ Buyer correctly blocked from farmer dashboard')


# ── ENQUIRY TESTS ─────────────────────────────────────
class EnquiryTests(BaseTestCase):

    def test_buyer_can_send_enquiry(self):
        self.client.login(username='testbuyer', password='buyer@123')
        response = self.client.post(f'/crop/{self.crop.pk}/', {
            'message': 'I want to buy 100kg of tomatoes',
            'phone'  : '9876543210',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Enquiry.objects.count(), 1)
        print('✅ Buyer can send enquiry')

    def test_enquiry_linked_to_correct_crop(self):
        self.client.login(username='testbuyer', password='buyer@123')
        self.client.post(f'/crop/{self.crop.pk}/', {
            'message': 'Test enquiry message',
            'phone'  : '9876543210',
        })
        enquiry = Enquiry.objects.first()
        self.assertEqual(enquiry.crop, self.crop)
        self.assertEqual(enquiry.buyer, self.buyer)
        print('✅ Enquiry linked to correct crop and buyer')

    def test_unauthenticated_cannot_enquire(self):
        response = self.client.post(f'/crop/{self.crop.pk}/', {
            'message': 'Test',
            'phone'  : '9876543210',
        })
        self.assertEqual(Enquiry.objects.count(), 0)
        print('✅ Unauthenticated user cannot send enquiry')