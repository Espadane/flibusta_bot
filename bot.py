from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher.filters import Text
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from catalog import Catalog
from pdf_converter import PdfConverter
from epub_converter import EpubConverter
from notifer import Notifer
from flibusta_logger import logger
import json
import asyncio
import os
import aioschedule

catalog = Catalog()
pdf_converter = PdfConverter()
epub_converter = EpubConverter()
notifer = Notifer()


bot_token = os.getenv("FLIBUSTA_BOT_TOKEN")
if not bot_token:
    exit("Error: no token provided")

bot = Bot(token=bot_token)
dp = Dispatcher(bot)


@dp.message_handler(commands=['start'])
async def start_command(msg: types.Message):
    '''Обработчик команды /start
    '''
    await msg.answer('Неофициальный бот флибусты для поиска и скачивания книжек.')


@dp.message_handler(commands=['help'])
async def help_command(msg: types.Message):
    '''Обработчик команды /help
    '''
    await msg.answer('Просто отправь мне запрос и я покажу какие книжки есть в каталоге.\nМогу искать по автору, серии, названию книги. Так же могу искать по всему сразу например "Гарри Поттер Роулинг"\n\n<b>! Важный момент ! Если что-то сломалось не надо винить автора. Вините Роскомнадзор. Автор не виноват, что они против книжек.</b>', parse_mode='HTML')


@dp.message_handler(commands=['news'])
async def news_feed(msg: types.Message):
    """Обработка команды /news, для подписки пользователя на получение обновлений

    Args:
        msg (types.Message): команда /news
    """
    await bot.delete_message(chat_id=msg.from_user.id, message_id=msg.message_id)
    btn_9 = InlineKeyboardButton('09:00', callback_data=f'feed\n09:00')
    btn_14 = InlineKeyboardButton('14:00', callback_data=f'feed\n14:00')
    btn_18 = InlineKeyboardButton('18:00', callback_data=f'feed\n18:00')
    btn_21 = InlineKeyboardButton('21:00', callback_data=f'feed\n21:00')
    btn_cancel = InlineKeyboardButton(
        'Отписаться от рассылки', callback_data=f'feed\nNone')
    feed_menu = InlineKeyboardMarkup().add(btn_9, btn_14)
    feed_menu.add(btn_18, btn_21)
    feed_menu.add(btn_cancel)
    await msg.answer('Выберите в какое время вы хотите получать новые книги (по МСК):', reply_markup=feed_menu)


@dp.message_handler(commands=['random'])
async def random_book(msg: types.Message):
    """Обработка команды получения случайной книги из каталога

    Args:
        msg (types.Message): команда /random
    """
    await bot.delete_message(chat_id=msg.from_user.id, message_id=msg.message_id)
    user_id = msg.from_user.id
    random_book = await catalog.random_book()
    await msg.answer('Вот вам что почитать случайного: ')
    await show_book(user_id=user_id, books=random_book, index=0, book_source='query')


@dp.message_handler(Text)
async def get_search_query(msg: types.Message):
    """Обрабатываем текстовое сообщение пользователя и передаем его в поиск книг по каталогу

    Args:
        msg (types.Message): сообщение пользователя, подрузумевается что это запрос к поиску книг
    """
    user_id = msg.from_user.id
    query = msg.text
    if os.path.exists(f'./files/{user_id}_query.json'):
        os.remove(f'./files/{user_id}_query.json')
        try:
            # если пользователь что-то уже спрашивал удалеем прошлый запрос
            for i in range(0, 5):
                await bot.delete_message(chat_id=msg.from_user.id, message_id=msg.message_id - i)
        except:
            pass
        logger.debug(f'Файл: {user_id}_query.json удален')
    books = await catalog.get_book_response(query=query, random_book=None)
    await search_result_forming(user_id, books)


@dp.message_handler(Text)
async def search_result_forming(user_id, books):
    """В зависимости от количества книг в ответе выдаем результат пользователю.
    Ограничение в 30 книг сделано для того чтобы не листать ответ пол часа.

    Args:
        user_id (int): айди пользователя необходим для пересылки ответа
        books (_type_): список книг из каталога
    """
    if len(books) > 30:
        await bot.send_message(user_id, f'Слишком большое количество книг ({len(books)} шт.). Пожалуйста уточните запрос, а то вам будет сложно искать, а нам сложно печатать.')
    elif len(books) == 0:
        await bot.send_message(user_id, 'Книг по данному запросу не найдено. Уточните вопрос, или если уверены в нем подпишитесь на обновления.Возможно книга появится позже.')
    else:
        await save_books_to_json(user_id, books)
        await show_book(user_id, books, index=0, book_source='query')


async def save_books_to_json(user_id, books):
    """Сохраняем список книг запрошенные пользователем в json. У телеграм есть ограничение на размер данных для передачи в колбек кнопок.

    Args:
        user_id (int): необходим для сохранения файла с ответом 
        books (list): список словарей с книгами
    """
    with open(f'./files/{user_id}_query.json', 'w') as file:
        json.dump(books, file, ensure_ascii=False, indent=4)
        logger.debug(
            f'Файл с книжками которые запросил пользователь сохранен.Под именем - {user_id}_query.json')


async def load_books_from_json(user_id):
    '''
    '''
    with open(f'./files/{user_id}_query.json') as file:
        books = json.load(file)
        logger.debug(
            'Список книг которые запросил пользователь успешно загружен из файла.')
    return books


@dp.message_handler(Text)
async def show_book(user_id, books, index, book_source):
    """Функция выводит одну книгу с информацией из списка книг по запросу пользователя.
    Так же выводит кнопки вперед и назад в зависимости от индекса книги в списке.
    Выводит кнопки скачивания EPUB и PDF.

    Args:
        user_id (int): используется чтобы знать кому посылать ответ
        books (list): список ответа с книгами
        index (int): позиция конкретной книги в списке
    """
    book = books[index]
    try:
        book_link = book['book_link']
    except:
        book_link = 'https://flibusta.site'
    try:
        book_name = book['book_name']
    except:
        book_name = 'Нет данных'
    try:
        author = f'{book["book_author_fn"]} {book["book_author_mn"]} {book["book_author_ln"]}'
    except:
        author = 'Нет данных, может ниже где написано'
    try:
        book_lang = book['book_lang']
    except:
        book_lang = 'Нет данных, видимо RU'
    try:
        book_year = book['book_year']
    except:
        book_year = 'Нет данных, свежачок!'
    try:
        book_series = book['book_series']
    except:
        book_series = 'Нет данных'
    try:
        book_summary = book['book_summary']
    except:
        book_summary = 'Придется прочитать'
    # опять таки ограничение телеграм, поэтому используется только первое слово из названия книги
    short_book_name = book_name.split(' ')[0]
    short_book_name = short_book_name.replace('.', '').replace(',', '')
    btn_next = InlineKeyboardButton(
        f'Книга ➡', callback_data=f'next\n{index}\n{book_source}')
    btn_prev = InlineKeyboardButton(
        '⬅ Книга', callback_data=f'prev\n{index}\n{book_source}')
    btn_download_epub = InlineKeyboardButton(
        'Скачать EPUB', callback_data=f'epub\n{book_link}\n{short_book_name}')
    btn_download_pdf = InlineKeyboardButton(
        'Скачать PDF', callback_data=f'pdf\n{book_link}\n{short_book_name}')
    buttons = []
    if index == 0:
        if len(books) == 1:
            pass
        else:
            buttons.append(btn_next)
    elif index == len(books) - 1:
        buttons.append(btn_prev)
    else:
        buttons.append(btn_prev)
        buttons.append(btn_next)
    menu = InlineKeyboardMarkup().add(*buttons)
    menu.add(btn_download_epub, btn_download_pdf)
    if book_source == 'query':
        await bot.send_message(user_id, f'Найденые книги {index + 1} из {len(books)}\n\nАвтор: {author}\nНазвание: {book_name}\nСерия: {book_series}\nГод: {book_year} Язык: {book_lang}\nОписание: {book_summary}\n<a href="{book_link}">Посмотреть на сайте</a>', reply_markup=menu, parse_mode='HTML')
    elif book_source == 'new':
        await bot.send_message(user_id, f'Новые книги на сайте {index + 1} из {len(books)}\n\nНазвание: {book_name}\nОписание: {book_summary}\n<a href="{book_link}">Посмотреть на сайте</a>', reply_markup=menu, parse_mode='HTML')


@dp.callback_query_handler(lambda c: 'next' in c.data)
async def forward(callback_query: types.CallbackQuery):
    """Обработка кнопки далее, для перехода по списку книг. 
    После нажатия снова вызывается функция отображения книги, но уже с новым индексом +1 

    Args:
        callback_query (types.CallbackQuery): просто передается индекс книги в списке
    """
    index = int(callback_query.data.split('\n')[1]) + 1
    book_source = callback_query.data.split('\n')[2]
    user_id = int(callback_query.from_user.id)
    if book_source == 'query':
        books = await load_books_from_json(user_id)
    elif book_source == 'new':
        books = await Notifer().get_dif_books()
    await bot.delete_message(chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id)
    await show_book(user_id, books, index, book_source=book_source)


@dp.callback_query_handler(lambda c: 'prev' in c.data)
async def backward(callback_query: types.CallbackQuery):
    """Обработка кнопки назад, для перехода по списку книг. 
    После нажатия снова вызывается функция отображения книги, но уже с новым индексом -1 

    Args:
        callback_query (types.CallbackQuery): просто передается индекс книги в списке
    """
    index = int(callback_query.data.split('\n')[1]) - 1
    book_source = callback_query.data.split('\n')[2]
    user_id = int(callback_query.from_user.id)
    if book_source == 'query':
        books = await load_books_from_json(user_id)
    elif book_source == 'new':
        books = await notifer.get_dif_books()
    await bot.delete_message(chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id)
    await show_book(user_id, books, index, book_source=book_source)


@dp.callback_query_handler(lambda c: 'epub' in c.data)
async def download_epub(callback_query: types.CallbackQuery):
    """Вызов конвертера в EPUB и отправка полученого файла пользлвателю.
    Args:
        callback_query (types.CallbackQuery): получаем ссылку на книгу которую надо скачать и ее название для сохранения файла
    """
    user_id = callback_query.from_user.id
    book_link = callback_query.data.split('\n')[1]
    book_name = callback_query.data.split('\n')[2].lower()
    await bot.send_message(user_id, 'Скачиваем EPUB\nДождитесь окончания, это может занять какое-то время.')
    try:
        book_name = epub_converter.make_epub(
            short_book_name=book_name, book_link=book_link)
        await bot.send_document(chat_id=user_id, document=open(f'./files/{book_name}.epub', 'rb'))
        os.remove(f'./files/{book_name}.epub')
    except Exception as error:
        logger.warning(
            f'Что то пошло не так с конвертацией EPUB и отправки пользователю. Данные:\nСсылка на неполучившуюся книгу:{book_link}\nНазвание книги: {book_name}\nАйди пользователя: {user_id}\nОшибка: {error}')
        await bot.send_message(user_id, 'Извините что-то пошло не так. Мы работаем над проблемой. Попробуйте позже.')


@dp.callback_query_handler(lambda c: 'pdf' in c.data)
async def download_pdf(callback_query: types.CallbackQuery):
    """Вызов конвертера в PDF и отправка полученого файла пользлвателю.

    Args:
        callback_query (types.CallbackQuery): получаем ссылку на книгу которую надо скачать и ее название для сохранения файла
    """
    user_id = callback_query.from_user.id
    book_link = callback_query.data.split('\n')[1]
    book_name = callback_query.data.split('\n')[2].lower()
    await bot.send_message(user_id, 'Скачиваем PDF\nДождитесь окончания, это может занять какое-то время.')

    try:
        book_name = pdf_converter.make_pdf(
            book_name=book_name, book_link=book_link)
        await bot.send_document(chat_id=user_id, document=open(f'./files/{book_name}.pdf', 'rb'))
        os.remove(f'./files/{book_name}.pdf')
    except Exception as error:
        logger.warning(
            f'Что то пошло не так с конвертацией PDF и отправки пользователю. Данные:\nСсылка на неполучившуюся книгу:{book_link}\nНазвание книги: {book_name}\nАйди пользователя: {user_id}\nОшибка: {error}')
        await bot.send_message(user_id, 'Извините что-то пошло не так. Мы работаем над проблемой. Попробуйте позже.')


@dp.callback_query_handler(lambda c: 'feed' in c.data)
async def set_notify_time(callback_query: types.CallbackQuery):
    """Обрабатываем время в которое оповещать пользователя о новинках

    Args:
        callback_query (types.CallbackQuery): получаем время уведомления
    """
    user_id = callback_query.from_user.id
    notify_time = callback_query.data.split('\n')[1]
    notifer.set_user_schedule(user_id=str(user_id), notify_time=notify_time)
    if notify_time == 'None':
        await bot.send_message(user_id, text='Вы отписались от обновлений')
    else:
        await bot.send_message(user_id, text=f'Теперь обновления будут приходить в {notify_time} по МСК')
    await bot.delete_message(chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id)


async def send_new_books(notify_time):
    users = await notifer.get_user_id_to_send(notify_time=notify_time)
    books = await notifer.get_dif_books()
    if books != []:
        for user in users:
            await show_book(user_id=user, books=books, index=0, book_source='new')
    else:
        for user in users:
            await bot.send_message(user, 'Сегодня новых книг нет, но вы можете выбрать случайную командой "\\random"')


async def scheduler():
    # скачиваем новый каталог каждый день в 05:00
    aioschedule.every().day.at('05:00').do(catalog.download_catalog_zip)
    # распаковывываем новую версию каталога каждый день в 05:30 на всякий случай попозже
    aioschedule.every().day.at('05:30').do(catalog.unzip_catalog)
    # проверяем RSS с новыми книгами каждый день в 8:00 утра
    aioschedule.every().day.at('08:00').do(notifer.write_new_books_to_json)
    # новые книги
    aioschedule.every().day.at('09:00').do(send_new_books, notify_time='09:00')
    aioschedule.every().day.at('14:00').do(send_new_books, notify_time='14:00')
    aioschedule.every().day.at('18:00').do(send_new_books, notify_time='18:00')
    aioschedule.every().day.at('21:00').do(send_new_books, notify_time='21:00')
    # удаляем файл с обновлениями, чтобы не машался
    aioschedule.every().day.at('23:59').do(notifer.delete_diff_books)

    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)


async def on_startup(_):
    if not os.path.exists('./files/'):
        os.mkdir('./files/')
        await catalog.download_catalog_zip()
        await catalog.unzip_catalog()
    asyncio.create_task(scheduler())

if __name__ == '__main__':

    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
