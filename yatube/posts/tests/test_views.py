from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from posts.models import Post, Group, Follow
from django.core.cache import cache

NUMBERS_OF_POSTS = 13
User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')
        cls.user = User.objects.create_user(username='auth', password='1234')
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
        self.authorized_client = Client()
        self.authorized_client.login(username='auth', password='1234')

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон"""
        templates_pages_names = {
            reverse('posts:main'): 'posts/index.html',
            reverse('posts:groups', kwargs={'slug': self.group.slug}): (
                'posts/group_list.html'
            ),
            reverse('posts:profile', kwargs={'username': self.user.username}): (
                'posts/profile.html'
            ),
            reverse(
                'posts:post_detail',
                kwargs={'post_id': f'{self.post.id}'}
            ): (
                'posts/post_detail.html'
            ),
            reverse(
                'posts:post_edit',
                kwargs={'post_id': f'{self.post.id}'}
            ): (
                'posts/create_post.html'
            ),
            reverse('posts:post_create'): 'posts/create_post.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_404_page_template(self):
        """Страница 404 использует соответствующий шаблон"""
        response = self.authorized_client.get('/error1234')
        self.assertTemplateUsed(response, 'core/404.html')

    def test_home_page_show_correct_context(self):
        """Шаблон home сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:main'))
        first_object = response.context['page_obj'][0]
        self.assertEqual(first_object.text, self.post.text)
        self.assertEqual(first_object.author.username, self.post.author.username)
        self.assertIsNone(first_object.group)

    def test_create_new_post(self):
        """Проверка, что при создании поста с указанием группы
        он появляется на главной странице и странице группы"""
        new_post = Post.objects.create(
            author=self.user,
            text='Тестовый пост',
            group=self.group
        )
        other_group = Group.objects.create(
            title='Другая тестовая группа',
            slug='other_test_slug',
            description='Другое тестовое описание',
        )
        self.assertIn(new_post, Post.objects.all())
        self.assertIn(new_post, Post.objects.filter(group=self.group))
        self.assertNotIn(new_post, Post.objects.filter(group=other_group))

    def test_subscription(self):
        """Тестирование подписки на пользователя"""
        response = self.authorized_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.author.username}
            )
        )
        self.assertRedirects(
            response,
            reverse(
                'posts:profile',
                kwargs={'username': self.author.username}
            )
        )
        self.assertEqual(self.author.following.filter(user=self.user).exists(), True)

    def test_following_posts(self):
        """Пользователь видит пост автора, на которого подписан
        в избранной ленте"""
        self.authorized_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.author.username}
            )
        )
        new_post = Post.objects.create(
            author=self.author,
            text='Пост, подписка',
            group=self.group
        )
        follower = Follow.objects.filter(user=self.user).values_list(
            'author_id', flat=True
        )
        self.assertIn(new_post, Post.objects.filter(author_id__in=follower))
        self.authorized_client.get(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': self.author.username}
            )
        )
        follower = Follow.objects.filter(user=self.user).values_list(
            'author_id', flat=True
        )
        self.assertNotIn(new_post, Post.objects.filter(author_id__in=follower))

    def test_unsubscription(self):
        """Тестирование отписки на пользователя"""
        self.authorized_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.author.username}
            )
        )
        response = self.authorized_client.get(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': self.author.username}
            )
        )
        self.assertRedirects(
            response,
            reverse(
                'posts:profile',
                kwargs={'username': self.author.username}
            )
        )
        self.assertEqual(self.author.following.filter(user=self.user).exists(), False)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='paginator_user')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug_2',
            description='Тестовое описание',
        )

        posts = [Post(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group
        ) for _ in range(NUMBERS_OF_POSTS)]
        cls.post = Post.objects.bulk_create(posts)

    def setUp(self):
        self.client = Client()

    def test_first_page_contains_ten_posts(self):
        """Тестирование первой страницы паджинатра"""
        response = self.client.get(reverse('posts:main'))
        self.assertEqual(len(response.context['page_obj']), 10)

    def test_second_page_contains_three_posts(self):
        """Тестирование вторй страницы паджинатра"""
        response = self.client.get(reverse('posts:main') + '?page=2')
        self.assertEqual(len(response.context['page_obj']), 3)
