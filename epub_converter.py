import requests
from bs4 import BeautifulSoup
import html2epub
import os
import shutil
import re
from flibusta_logger import logger

path_to_epub = '/place/here/absolute/path/'

class EpubConverter:
    """Класс конвертера книг из html по ссылке в EPUB.
    Получает ссылку на книгу и короткое имя для сохранения файла.
    """

    def __init__(self, book_link=None, short_book_name=None) -> None:
        pass

    def get_book_data(self):
        """Получаем имя книги, автора и главы для корректного сохранения файла epub

        Returns:
            str, str, list: имя автора, название книги, список глав
        """
        try:
            self.response = requests.get(self.book_read_link)
        except Exception as error:
            logger.warning(
                f'Не получилось достучаться до страницы книги: {self.short_book_name}\n{self.book_read_link}.\n{self.response.status_code}\nОшибка: {error}')
        self.soup = BeautifulSoup(self.response.text, 'lxml')
        try:
            links = self.soup.find_all('a')
            chapters = []
            for link in links:
                if re.search(r'/a/\d+', str(link)):
                    book_author = link.text
                elif re.search(r'/b/\d+\"', str(link)):
                    book_name = link.text
            headers = self.soup.find_all('h3')
            for header in headers[1:-1]:
                chapters.append(header.text)
            return book_author, book_name, chapters
        except Exception as error:
            logger.warning(
                f'Не удалось получить данные о книге {self.book_read_link}. Ошибка: {error}')

    def get_html_chapters(self):
        """Сохранение каждой главы в отдельный html файл. Изображения заменяются на заглушку, потому что библиотека конвертации не корректно обрабатывает ссылки и выдает ошибку. Так же добавляется в каждый файл кодировка для правильного отображения кирилицы. 
        """
        book = self.soup.find_all(class_='book')
        if not os.path.exists(f'./files/{self.short_book_name}'):
            os.mkdir(f'./files/{self.short_book_name}')
        i = 0
        for b in book[1:]:
            if '<h3 class="book">' in str(b):
                i += 1
                with open(f'./files/{self.short_book_name}/{i}.html', 'a') as file:
                    file.write(f'<head><meta charset="UTF-8"></head>\n')
            text = re.sub(
                r'<img.+/>', '\n"тут в книге должна быть картинка, но по техническим причинам ее нет"\n', str(b))
            with open(f'./files/{self.short_book_name}/{i}.html', 'a') as file:
                file.write(text)

    def make_epub(self, short_book_name, book_link):
        # в файле usr/local/lib/python3.9/site-packages/html2epub/epub_templates/toc.html заменить <title>目录</title> и  <h2>目录</h2> на "Содержание"
        """Изготавливаем epub из html файлов по главам. После конвертации удаляем папку с html

        Returns:
            str: возвращаем короткое имя книги для идентификации файла epub
        """
        self.short_book_name = short_book_name
        self.book_read_link = f'{book_link}/read'
        book_author, book_name, chapters = self.get_book_data()
        self.get_html_chapters()
        epub = html2epub.Epub(
            title=book_name, creator=book_author, publisher=book_author)
        if chapters == []:
            chapter = html2epub.create_chapter_from_file(
                f'./files/{self.short_book_name}/0.html', title=f'Начало')
            epub.add_chapter(chapter)
        else:
            for i in range(0, len(chapters)):
                chapter = html2epub.create_chapter_from_file(
                    f'./files/{self.short_book_name}/{i+1}.html', title=f'{chapters[i]}')
                epub.add_chapter(chapter)
        try:
            epub.create_epub(
                output_directory=path_to_epub, epub_name=self.short_book_name) #абсолютный путь до папки files внутри папки с ботом
        except Exception as error:
            logger.warning(
                f'Не удалось сделать EPUB. {self.book_read_link}\nОшибка: {error}')
        shutil.rmtree(f'./files/{self.short_book_name}')

        return self.short_book_name
