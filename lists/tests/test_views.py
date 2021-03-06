from django.template.response import TemplateResponse
from django.test import TestCase

from django.core.urlresolvers import resolve
from django.http import HttpRequest
from django.template.loader import render_to_string
from django.utils.html import escape

from lists.forms import (
    ItemForm, EMPTY_LIST_ERROR, DUPLICATE_ITEM_ERROR, ExistingListItemForm
)
from lists.views import home_page
from lists.models import Item, List


class HomePageTest(TestCase):
    maxDiff = None

    def test_root_url_resolves_to_home_page_view(self):
        found = resolve('/')
        self.assertEqual(found.func, home_page)

    def test_home_page_returns_correct_html(self):
        request = HttpRequest()
        response = home_page(request)
        expected_html = TemplateResponse(request, 'home.html', {'form': ItemForm()}).render().content.decode()
        self.assertMultiLineEqual(response.content.decode(), expected_html)

    def test_home_page_only_saves_items_when_necessary(self):
        request = HttpRequest()
        home_page(request)
        self.assertEqual(Item.objects.all().count(), 0)

    def test_home_page_renders_home_template(self):
        response = self.client.get('/')
        self.assertTemplateUsed(response, 'home.html')

    def test_home_page_uses_item_form(self):
        response = self.client.get('/')
        self.assertIsInstance(response.context['form'], ItemForm)


class ListViewTests(TestCase):

    def test_displays_all_items(self):
        list_ = List.objects.create()
        Item.objects.create(text='itemey 1', list=list_)
        Item.objects.create(text='itemey 2', list=list_)

        response = self.client.get('/lists/%d/' % (list_.id,))

        self.assertContains(response, 'itemey 1')
        self.assertContains(response, 'itemey 2')

    def test_uses_list_tempate(self):
        list_ = List.objects.create()
        response = self.client.get('/lists/%d/' % (list_.id,))
        self.assertTemplateUsed(response, 'list.html')

    def test_displays_only_items_for_that_list(self):
        correct_list = List.objects.create()
        Item.objects.create(text='itemey 1', list=correct_list)
        Item.objects.create(text='itemey 2', list=correct_list)
        other_list = List.objects.create()
        Item.objects.create(text='other list item 1', list=other_list)
        Item.objects.create(text='other list item 2', list=other_list)

        response = self.client.get('/lists/%d/' % (correct_list.id,))

        self.assertContains(response, 'itemey 1')
        self.assertContains(response, 'itemey 2')
        self.assertNotContains(response, 'other list item 2')
        self.assertNotContains(response, 'other list item 1')

    def test_passes_correct_list_to_template(self):
        other_list = List.objects.create()
        correct_list = List.objects.create()
        response = self.client.get('/lists/%d/' % (correct_list.id,))
        self.assertEqual(response.context['list'], correct_list)

    def test_can_save_a_POST_request_to_an_existing_list(self):
        other_list = List.objects.create()
        correct_list = List.objects.create()

        self.client.post(
            '/lists/%d/' % (correct_list.id, ),
            data={'text': 'A new item for an existing list'}
        )

        self.assertEqual(Item.objects.all().count(), 1)
        new_item = Item.objects.all()[0]
        self.assertEqual(new_item.text, 'A new item for an existing list')
        self.assertEqual(new_item.list, correct_list)

    def test_POST_redirects_to_list_view(self):
        other_list = List.objects.create()
        correct_list = List.objects.create()

        response = self.client.post(
            '/lists/%d/' % (correct_list.id,),
            data={'text': 'A new item for an existing list'}
        )

        self.assertRedirects(response, '/lists/%d/' % (correct_list.id, ))

    def post_invalid_input(self):
        list_ = List.objects.create()
        return self.client.post(
            '/lists/%d/' % (list_.id,),
            data={'text': ''}
        )

    def test_invalid_input_means_nothing_saved_to_db(self):
        self.post_invalid_input()
        self.assertEqual(Item.objects.all().count(), 0)

    def test_invalid_input_renders_list_template(self):
        response = self.post_invalid_input()
        self.assertTemplateUsed(response, 'list.html')

    def test_invalid_input_renders_form_with_errors(self):
        response = self.post_invalid_input()
        self.assertIsInstance(response.context['form'], ExistingListItemForm)
        self.assertContains(response, escape(EMPTY_LIST_ERROR))

    def test_duplicate_item_validation_errors_end_up_on_lists_page(self):
        list1 = List.objects.create()
        item1 = Item.objects.create(list=list1, text='textey')
        response = self.client.post(
            '/lists/%d/' % (list1.id,),
            data={'text': 'textey'}
        )
        expected_error = escape(DUPLICATE_ITEM_ERROR)
        self.assertContains(response,expected_error)
        self.assertTemplateUsed(response, 'list.html')
        self.assertEqual(Item.objects.all().count(), 1)

    def test_displays_item_form(self):
        list_ = List.objects.create()
        response = self.client.get('/lists/%d/' % (list_.id,))
        self.assertIsInstance(response.context['form'], ExistingListItemForm)
        self.assertContains(response, 'name="text"')


class NewListTest(TestCase):

    def test_saving_a_POST_request(self):
        self.client.post(
            '/lists/new',
            data={'text': 'A new list item'}
        )
        self.assertEqual(Item.objects.all().count(), 1)
        new_item = Item.objects.all()[0]
        self.assertEqual(new_item.text, 'A new list item')

    def test_redirects_after_POST(self):
        response = self.client.post(
            '/lists/new',
            data={'text': 'A new list item'}
        )
        new_list = List.objects.all()[0]
        self.assertRedirects(response, '/lists/%d/' % (new_list.id,))

    def test_validation_errors_sent_back_to_home_page_template(self):
        response = self.client.post('/lists/new', data={'text': ''})
        self.assertEqual(Item.objects.all().count(), 0)
        self.assertEqual(List.objects.all().count(), 0)
        self.assertTemplateUsed(response, 'home.html')
        self.assertContains(response, escape(EMPTY_LIST_ERROR))
        self.assertIsInstance(response.context['form'], ItemForm)


class NewItemTest(TestCase):

    def test_can_save_a_POST_request_to_an_existing_list(self):
        other_list = List.objects.create()
        correct_list = List.objects.create()

        self.client.post(
            '/lists/%d/' % (correct_list.id,),
            data={'text': 'A new item for an existing list'}
        )

        self.assertEqual(Item.objects.all().count(), 1)
        new_item = Item.objects.all()[0]
        self.assertEqual(new_item.text, 'A new item for an existing list')
        self.assertEqual(new_item.list, correct_list)

    def test_redirects_to_list_view(self):
        other_list = List.objects.create()
        correct_list = List.objects.create()
        response = self.client.post(
            '/lists/%d/' % (correct_list.id,),
            data={'text': 'A new item for an existing list'}
        )

        self.assertRedirects(response, '/lists/%d/' % (correct_list.id,))