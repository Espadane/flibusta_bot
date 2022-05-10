import weasyprint
import requests
from bs4 import BeautifulSoup
import os
from flibusta_logger import logger
import shutil


class PdfConverter:
    """Класс конвертера книг из html по ссылке в pdf.
    Получает ссылку на книгу и короткое имя для сохранения файла.
    """

    def __init__(self, book_link=None, book_name=None) -> None:
        pass

    def make_pdf(self, book_name, book_link):
        """Делаем pdf из HTML. Сохраням HTML в папку, удаляем лишние данные, добавляем кодировку для отображения кирилицы. После конвертации удаляем папку с HTML

        Returns:
            str: возвращаем короткое имя книги для идентифицаии файла
        """
        self.book_read_link = f'{book_link}/read'
        self.book_name = book_name
        try:
            response = requests.get(self.book_read_link)
        except Exception as error:
            logger.warning(
                f'Не получилось достучаться до страницы книги: {book_name}\n{book_link}.\n{self.response.status_code}\nОшибка: {error}')
        soup = BeautifulSoup(response.text, 'lxml')
        book = soup.find_all(class_='book')
        if book != []:
            if not os.path.exists(f'./files/{self.book_name}'):
                os.mkdir(f'./files/{self.book_name}')
            with open(f'./files/{self.book_name}/{self.book_name}.html', 'a') as file:
                file.write(
                    f'<head><meta charset="UTF-8">\n<title>{self.book_name}</title></head>')
            for i in book:
                with open(f'./files/{self.book_name}/{self.book_name}.html', 'a') as file:
                    file.write(str(i))
            try:
                weasyprint.HTML(
                    filename=f'./files/{self.book_name}/{self.book_name}.html').write_pdf(f'./files/{self.book_name}.pdf')
            except Exception as error:
                logger.warning(
                    f'Не удалось сделать PDF.\nКнига: {self.book_read_link}\nОшибка: {error}')
            shutil.rmtree(f'./files/{self.book_name}')
        else:
            self.book_name = None

        return self.book_name
