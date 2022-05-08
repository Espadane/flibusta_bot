# -*- coding: utf-8 -*-
import feedparser
from flibusta_logger import logger
import os
import json
from catalog import Catalog


catalog = Catalog()


class Notifer:
    """Класс для работы с уведомлениям на новые книги.
    Принимает user_id для записи в файл расписания и время расписания.
    """

    def __init__(self, user_id=None, notify_time=None) -> None:
        self.feed_url = 'https://www.flibusta.site/new/rss'
        self.user_id = user_id
        self.notify_time = notify_time

    async def get_new_books_list(self):
        """Получаем данные о новых книжках на сайте через RSS

        Returns:
            list: получаем список новых книг с описанием и ссылкой.
        """
        new_books_list = []
        data = feedparser.parse(self.feed_url)
        books = data['entries']
        for book in books:
            book_name = book['title_detail']['value'].strip()
            book_link = book['link'].strip()
            # берем не из rss чтобы было точнее.
            book_summary = await catalog.get_book_summary(book_url=book_link)
            new_books_list.append({
                'book_name': book_name,
                'book_summary': book_summary.strip(),
                'book_link': book_link
            })
        logger.debug(
            f'Список новых книг получен. Новых книг - {len(new_books_list)}')

        return new_books_list

    async def write_new_books_to_json(self):
        """Записываем полученые по RSS книги в файл.
        Если файл не существует записываем полностью.
        Если файл есть сверяем с известными данными, перезаписываем файл и создаем файл со списком новых книг для последующей отправки пользователям.
        """
        new_books = await self.get_new_books_list()
        if not os.path.exists('./files/new_books.json'):
            with open('./files/new_books.json', 'w') as file:
                json.dump(new_books, file, ensure_ascii=False, indent=4)
        else:
            lists_dif = self.compare_lists(new_books)
            if lists_dif != []:
                try:
                    os.remove('./files/new_books.json')
                    with open('./files/new_books.json', 'w') as file:
                        json.dump(new_books, file,
                                  ensure_ascii=False, indent=4)
                    with open('./files/list_dif.json', 'w') as file:
                        json.dump(lists_dif, file,
                                  ensure_ascii=False, indent=4)
                    logger.debug(
                        'Файл с книгами обновлен, файл с новыми книгами создан.')
                except Exception as error:
                    logger.warning(
                        f'Создание файлов обновлений не удалось.\nОшибка: {error}')

    def load_books_list_from_json(self):
        """Читаем список книг из файла

        Returns:
            list: список книг полученых по RSS из файла
        """
        with open('./files/new_books.json', 'r') as file:
            books_from_file = json.load(file)

        return books_from_file

    def compare_lists(self, new_books):
        """Сравниваем список старых новых книг и список новых книг

        Args:
            new_books (list): список книг полученый по RSS

        Returns:
            list: список новых книг 
        """
        books_from_file = self.load_books_list_from_json()
        lists_dif = []
        for element in new_books:
            if element not in books_from_file:
                lists_dif.append(element)
        logger.debug(f'Новых позиций в списке книг - {len(lists_dif)}')
        return lists_dif

    def set_user_schedule(self, user_id, notify_time):
        """Если файла с расписанием нет - создаем
        Если пользователь уже создавал расписание - изменяем время
        Если пользователь установил время впервые, добавляем в json

        Args:
            user_id (str): идентификатор пользователя
            notify_time (str): время когда надо присылать новости
        """
        user_timer = {'user_id': user_id,
                      'notify_time': notify_time}
        data = []
        if not os.path.exists('./files/schedule.json'):
            with open('./files/schedule.json', 'w') as file:
                data.append(user_timer)
                json.dump(data, file, ensure_ascii=False, indent=4)
        else:
            with open('./files/schedule.json', 'r') as file:
                data = json.load(file)
            is_found = False
            for d in data:
                if user_id in d['user_id']:
                    d['notify_time'] = notify_time
                    is_found = True
                    break
            if is_found == False:
                data.append(user_timer)
            with open('./files/schedule.json', 'w') as file:
                json.dump(data, file, ensure_ascii=False, indent=4)

    async def get_user_id_to_send(self, notify_time):
        """получаем список пользователей которым надо отправить уведомление о новых книжках

        Args:
            notify_time (str): время уведомления

        Returns:
            list: список пользователей для отправки уведомлений
        """
        user_id_to_send = []
        with open('./files/schedule.json') as file:
            user_schedule = json.load(file)
        for i in user_schedule:
            if i['notify_time'] == notify_time:
                user_id_to_send.append(int(i['user_id']))

        return user_id_to_send

    async def get_dif_books(self):
        """Получаем новые книжки из файла

        Returns:
            list: список новых книг
        """
        try:
            with open('./files/list_dif.json') as file:
                dif_books = list(json.load(file))
        except:
            dif_books = []

        return dif_books

    async def delete_diff_books(sefl):
        """Удаляем список новых книг ночью, на всякий случай
        """
        try:
            os.remove('./files/list_dif.json')
        except:
            logger.warning('странно файла с новыми книжками нет.')
