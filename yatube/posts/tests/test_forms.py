from posts.forms import PostForm
from posts.models import Post, Group, Comment
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse, reverse_lazy
from http import HTTPStatus

User = get_user_model()


class FormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='this title',
            slug='test_slug',
            description='this description',
        )
        cls.other_group = Group.objects.create(
            title='other group',
            slug='other_group',
            description='other description',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
        )
        cls.form = PostForm()

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(FormTests.post.author)

    def test_create_post(self):
        """Создание нового поста"""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'text text',
            'group': self.group.id,
        }
        response_not_auth = self.guest_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=False
        )
        self.assertEqual(response_not_auth.status_code, HTTPStatus.FOUND)
        self.assertEqual(Post.objects.count(), posts_count)

        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )

        self.assertRedirects(
            response,
            reverse(
                'posts:profile',
                kwargs={'username': self.post.author}
            )
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        last_post = Post.objects.all().first()
        self.assertEqual(last_post.group.id, form_data['group'])
        self.assertEqual(last_post.text, form_data['text'])

    def test_edit_post(self):
        """Создание нового поста"""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'edited text',
            'group': self.other_group.id,
        }

        response = self.authorized_client.post(
            reverse_lazy(
                'posts:post_edit',
                kwargs=({'post_id': self.post.pk})
            ),
            data=form_data,
            follow=True
        )

        self.assertRedirects(
            response,
            reverse(
                'posts:post_detail',
                kwargs=({'post_id': self.post.pk})
            )
        )
        edited_post = Post.objects.all()[0]
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertEqual(edited_post.author, self.user)
        self.assertEqual(edited_post.text, form_data['text'])
        self.assertEqual(edited_post.group_id, self.other_group.id)
        self.assertNotEqual(edited_post.group_id, self.group.id)

    def test_create_comment(self):
        """Создание нового комментария"""
        comments_count = Comment.objects.filter(post=self.post.pk).count()
        form_data = {
            'text': 'text text',
        }
        response = self.authorized_client.post(
            reverse(
                'posts:add_comment',
                kwargs=({'post_id': self.post.pk})
            ),
            data=form_data,
            follow=True
        )
        self.assertEqual(
            Comment.objects.filter(post=self.post.pk).count(),
            comments_count + 1
        )
        self.assertRedirects(
            response,
            reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.pk}
            )
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        last_comment = Comment.objects.all().first()
        self.assertEqual(last_comment.post.pk, self.post.pk)
        self.assertEqual(last_comment.text, form_data['text'])

        response_not_auth = self.guest_client.post(
            reverse(
                'posts:add_comment',
                kwargs=({'post_id': self.post.pk})
            ),
            data=form_data,
            follow=False
        )
        self.assertEqual(response_not_auth.status_code, HTTPStatus.FOUND)
