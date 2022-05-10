import aiohttp
import os
from bs4 import BeautifulSoup
import requests
import zipfile
import random
from flibusta_logger import logger


class Catalog:
    """Класс работающий с каталогом книг
    """

    def __init__(self, query=None, book_url=None) -> None:
        """Инициализация класса Catalog

        Args:
            query (string, optional): запрос к каталогу.
            book_url (string, optional): для получения описания книги.
        """
        self.catalog_url = 'https://www.flibusta.site/catalog/catalog.zip'
        self.query = query

    async def download_catalog_zip(self):
        """Скачиваем catalog.zip с flibusta.site
        """
        try:
            response = requests.get(self.catalog_url)
            logger.info(f'Код ответа: {response.status_code}')
        except Exception as error:
            logger.warning(
                f'Не удалось сделать запрос к серверу с каталогом.\nОшибка: {error}')
        try:
            with open('./files/catalog.zip', 'wb') as file:
                file.write(response.content)
            logger.debug('Удалось сохранить каталог книг')
        except Exception as error:
            logger.warning(
                f'Не удалось получить каталог книг.\nОшибка: {error}')

    async def unzip_catalog(self):
        """Распаковка catalog.zip и удаление архива
        """
        catalog_arch = './files/catalog.zip'
        try:
            with zipfile.ZipFile(catalog_arch, 'r') as file:
                file.extract('catalog.txt', './files/')
            logger.debug('Каталог книг успешно распакован')
        except Exception as error:
            logger.warning(
                f'Не удалось распаковать каталог с книгами\nОшибка: {error}')
        if os.path.exists(catalog_arch):
            os.remove(catalog_arch)
            logger.debug('Zip архив удален')

    async def search_query(self, query):
        """Поиск кинг по запросу пользователя
        """
        answer = []
        try:
            words = query.split(' ')
            with open("./files/catalog.txt", "r") as file:
                for line in file:
                    for i in range(0, len(words)):
                        if words[i].lower() not in line.lower():
                            break
                        else:
                            if words[i].lower() == words[-1].lower() and words[i].lower() in line.lower():
                                answer.append(line)
            clear_answer = list(set(answer))
            logger.debug(
                f'Запрос выполнен успешно. Количество строк ответа {len(clear_answer)}')
        except Exception as error:
            clear_answer = []
            logger.warning(f'Не удалось выполнить запрос.\nОшибка: {error}')

        return clear_answer

    async def get_book_response(self, query, random_book):
        """Собираем ответ пользователя в словарь и отдаем пользователю.

        Args:
            random_book (list, optional): При поиске случайной книги. Defaults to None.

        Returns:
            list: Список книг с описанием
        """
        books = []
        if random_book == None:
            response = await self.search_query(query)
        else:
            response = random_book
        for book in response:
            book_data = book.split(';')
            book_author_fn = f'{book_data[1]}'
            book_author_ln = f'{book_data[0]}'
            book_author_mn = f'{book_data[2]}'
            book_name = f'{book_data[3]} {book_data[4]}'
            book_lang = f'{book_data[5]}'
            book_year = book_data[6]
            book_series = book_data[7]
            book_link = f'https://www.flibusta.site/b/{book_data[8]}'
            book_summary = ''
            books.append({
                'book_author_fn': book_author_fn.strip(),
                'book_author_ln': book_author_ln.strip(),
                'book_author_mn': book_author_mn.strip(),
                'book_name': book_name.strip(),
                'book_lang': book_lang.strip(),
                'book_year': book_year.strip(),
                'book_series': book_series.strip(),
                'book_link': book_link.strip(),
                'book_summary': book_summary
            })

        return books

    async def random_book(self):
        """Получаем случайную книгу из каталога

        Returns:
            list: информация о случайной книге
        """
        with open('./files/catalog.txt', 'r') as file:
            data = file.readlines()

        random_book = [data[random.randint(1, len(data))]]
        book_data = await self.get_book_response(query=None, random_book=random_book)
        
        return book_data

    async def get_book_summary(self, book_url):
        """Получаем аннотацию о книге

        Args:
            book_url (str): ссылка на книгу

        Returns:
            str: аннотация
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(book_url) as response:
                    html = await response.text()

            soup = BeautifulSoup(html, 'lxml')
            summary = soup.find('h2').find_next().text
            if 'поиск' in summary:
                summary = 'отсутствует'
            logger.debug(
                f'Удалось получить информацию о книге по ссылке: {book_url}')
        except Exception as error:
            summary  = ''
            logger.warning(
                f'Не удалось получить инфо о книге.\nURL =  {book_url}.\nОшибка: {error}')

        return summary
