from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from posts.models import Post, Group
from http import HTTPStatus
from django.urls import reverse
from django.core.cache import cache

User = get_user_model()


class StaticURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )

    def setUp(self):
        cache.clear()
        self.guest_client = Client()
        self.userx = User.objects.create_user(username='HasNoName')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_url_for_guest(self):
        """URL-адрес открывается успешно"""
        pages = (
            '/',
            f'/group/{self.group.slug}/',
            f'/profile/{self.user}/',
            f'/posts/{self.post.id}/'
        )
        for page in pages:
            response = self.guest_client.get(page)
            self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_url_for_authorized(self):
        """URL-адрес открывается успешно"""
        pages = (
            '/create/',
        )
        for page in pages:
            response = self.authorized_client.get(page)
            self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_url_comment_for_authorized(self):
        """Добавление комментариев возможно только для
         авторизованного пользователя"""
        link = '/posts/' + str(self.post.id) + '/comment/'
        response = self.authorized_client.get(link)
        self.assertRedirects(
            response,
            reverse(
                'posts:post_detail',
                kwargs=({'post_id': self.post.pk}))
        )

    def test_url_comment_for_guest(self):
        """Добавление комментариев возможно только для
         авторизованного пользователя"""
        link = '/posts/' + str(self.post.id) + '/comment/'
        response = self.guest_client.get(link)
        self.assertRedirects(
            response,
            f'/auth/login/?next=/posts/{self.post.id}/comment/'
        )

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            'posts/index.html': '/',
            'posts/group_list.html': f'/group/{self.group.slug}/',
            'posts/profile.html': f'/profile/{self.user.username}/',
            'posts/post_detail.html': f'/posts/{self.post.id}/',
        }
        for template, address in templates_url_names.items():
            with self.subTest(address=address):
                response = self.client.get(address)
                self.assertTemplateUsed(response, template)

    def test_urls_uses_for_edit(self):
        """URL-адрес /create/ открывается корректно."""
        response = self.authorized_client.get('/create/')
        self.assertTemplateUsed(response, 'posts/create_post.html')

    def test_urls_post_edit_works_correct(self):
        """URL-адрес /edit/ работает корректно."""
        link = '/posts/' + str(self.post.id) + '/edit/'
        response = self.authorized_client.get(link)
        self.assertTemplateUsed(response, 'posts/create_post.html')
        response_not_authorized = self.guest_client.get(link)
        self.assertEqual(response_not_authorized.status_code, HTTPStatus.FOUND)
        new_user = User.objects.create_user(username='NewUser')
        new_authorized_client = Client()
        new_authorized_client.force_login(new_user)
        response_not_author = new_authorized_client.get(link)
        self.assertRedirects(
            response_not_author,
            reverse(
                'posts:post_detail',
                kwargs=({'post_id': self.post.pk}))
        )
