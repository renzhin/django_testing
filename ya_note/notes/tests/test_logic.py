from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from pytils.translit import slugify

from notes.forms import WARNING
from notes.models import Note


User = get_user_model()


class TestLogic(TestCase):
    NOTE_TITLE = 'Тестовый заголовок'
    NOTE_TITLE_FORM = 'Текст заголовка для формы'
    NOTE_TEXT = 'Содержимое заметки'
    NOTE_TEXT_FORM = 'Текст заметки для формы'
    NOTE_SLUG_FORM = 'text_zametki'
    NOTE_SLUG_NEW = 'text_new_zametki'
    USERNAME_AUTHOR = 'Лев Толстой'
    USERNAME_READER = 'Клифорд Саймак'

    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create(username=cls.USERNAME_AUTHOR)
        cls.reader = User.objects.create(username=cls.USERNAME_READER)
        cls.author_client = Client()
        cls.reader_client = Client()
        cls.author_client.force_login(cls.author)
        cls.reader_client.force_login(cls.reader)
        cls.note1 = Note.objects.create(
            title=cls.NOTE_TITLE,
            text=cls.NOTE_TEXT,
            slug=cls.NOTE_SLUG_NEW,
            author=cls.author
        )
        cls.form_data = {
            'title': cls.NOTE_TITLE_FORM,
            'text': cls.NOTE_TEXT_FORM,
            'slug': cls.NOTE_SLUG_FORM
        }
        cls.form_not_uniq_data = {
            'title': cls.NOTE_TITLE_FORM,
            'text': cls.NOTE_TEXT_FORM,
            'slug': cls.NOTE_SLUG_NEW
        }
        cls.NOTE_ADD_URL = reverse('notes:add')
        cls.NOTE_SUCCESS_URL = reverse('notes:success')
        cls.NOTE_DELETE_URL = reverse('notes:delete', args=(cls.note1.slug,))
        cls.NOTE_EDIT_URL = reverse('notes:edit', args=(cls.note1.slug,))

    def setUp(self):
        self.notes_count_before = Note.objects.count()

    def test_anonymous_user_cant_create_note(self):
        self.client.post(self.NOTE_ADD_URL, data=self.form_data)
        notes_count_after = Note.objects.count()
        self.assertEqual(self.notes_count_before, notes_count_after)

    def test_user_can_create_note(self):
        response = self.author_client.post(
            self.NOTE_ADD_URL,
            data=self.form_data
        )
        self.assertRedirects(response, self.NOTE_SUCCESS_URL)
        notes_count_after = Note.objects.count()
        self.assertEqual(notes_count_after, self.notes_count_before + 1)
        note_for_test = Note.objects.latest('id')
        self.assertEqual(note_for_test.title, self.NOTE_TITLE_FORM)
        self.assertEqual(note_for_test.text, self.NOTE_TEXT_FORM)
        self.assertEqual(note_for_test.author, self.author)

    def test_empty_slug(self):
        self.form_data.pop('slug')
        response = self.author_client.post(
            self.NOTE_ADD_URL,
            data=self.form_data
        )
        notes_count_after = Note.objects.count()
        self.assertRedirects(response, self.NOTE_SUCCESS_URL)
        self.assertEqual(notes_count_after, self.notes_count_before + 1)
        note_for_test = Note.objects.latest('id')
        expected_slug = slugify(self.form_data['title'])
        self.assertEqual(note_for_test.slug, expected_slug)

    def test_not_unique_slug(self):
        response = self.author_client.post(
            self.NOTE_ADD_URL,
            data=self.form_not_uniq_data
        )
        notes_count_after = Note.objects.count()
        self.assertFormError(
            response, 'form', 'slug', errors=(self.note1.slug + WARNING)
        )
        self.assertEqual(self.notes_count_before, notes_count_after)

    def test_author_can_edit_note(self):
        response = self.author_client.post(self.NOTE_EDIT_URL, self.form_data)
        self.assertRedirects(response, self.NOTE_SUCCESS_URL)
        self.note1.refresh_from_db()
        self.assertEqual(self.note1.title, self.form_data['title'])
        self.assertEqual(self.note1.text, self.form_data['text'])
        self.assertEqual(self.note1.slug, self.form_data['slug'])

    def test_other_user_cant_edit_note(self):
        self.client.force_login(self.reader)
        response = self.client.post(self.NOTE_EDIT_URL, self.form_data)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        note_from_db = Note.objects.get(id=self.note1.id)
        self.assertEqual(self.note1.title, note_from_db.title)
        self.assertEqual(self.note1.text, note_from_db.text)
        self.assertEqual(self.note1.slug, note_from_db.slug)

    def test_author_can_delete_note(self):
        response = self.author_client.post(self.NOTE_DELETE_URL)
        notes_count_after = Note.objects.count()
        self.assertRedirects(response, self.NOTE_SUCCESS_URL)
        self.assertEqual(self.notes_count_before, notes_count_after + 1)

    def test_other_user_cant_delete_note(self):
        response = self.reader_client.post(self.NOTE_DELETE_URL)
        notes_count_after = Note.objects.count()
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertEqual(self.notes_count_before, notes_count_after)
