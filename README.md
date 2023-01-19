# flibusta_bot
Неофициальный бот для поиска и скачивания книг на сервисе flibusta.site.  
В данном проекте использовались бибилиотки aiogram, aiohttp, requests, BeutifullSoup, html2epub, weasyprint.  
## Что может:
1. Поиск книг на сайте
2. Скачивание в EPUB и PDF 
3. Подписка на обновления сайта по времени.
4. Получение случайной книги из каталога сайта.  
## [Работающая версия](https://t.me/book_brotherhood_bot)  
## Для запуска:
- ```git clone https://github.com/Espadane/flibusta_bot```
- ```pip install -r requirements.txt```
- Добавить в виртуальное окружение переменную FLIBUSTA_BOT_TOKEN с вашим токеном
- В файле epub_converter прописать абсолютный путь до бота папка 'files' в переменную path_to_epub (библиотека для конвертирования не понимает относительные пути)
- По желанию в файле библиотеки /html2epub/epub_templates/toc.html заменить ```<title>目录</title>``` и  ```<h2>目录</h2>``` на "Содержание". Отвечает за надпись "Содержание" в оглавлении сконвертированных книг
- Запустить бот командой python3 bot.py

## Структура проекта:
- bot.py - все что связанно с работой самого бота
- catalog.py - работа с каталогом флибусты
- epub_converter.py - конвертер книг в EPUB
- pdf_converter.py - конвертер книг в PDF
- notifer.py - все что связанно со сбором RSS на сайте 
- flibusta_logger.py - настройки логгирования
