import sqlite3
import telebot
from telebot import types
import io

bot = telebot.TeleBot('6749040210:AAGD-DBueu5Q-KxUGpV-SE_73ugjrVNf_t8')
user_dict = {}

def create_tables():
    conn = sqlite3.connect('user.sql')
    cur = conn.cursor()

    # Create users table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            pass TEXT
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS user_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            file_name TEXT,
            file_content BLOB,
            file_extension TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    conn.commit()
    conn.close()
create_tables()

def is_admin(user_id):
    return user_id == 778871044

def start_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton('Регистрация'))
    markup.row(types.KeyboardButton('Авторизация'))
    return markup

@bot.message_handler(commands=['myfiles'])
def view_user_files(message):
    user_id = message.from_user.id

    conn = sqlite3.connect('user.sql')
    cur = conn.cursor()

    cur.execute("SELECT file_name FROM user_files WHERE user_id=?", (user_id,))
    file_names = cur.fetchall()

    conn.close()

    if file_names:
        bot.send_message(message.chat.id, 'Ваши сохраненные файлы:')
        for file_name in file_names:
            bot.send_message(message.chat.id, f'- {file_name[0]}')
    else:
        bot.send_message(message.chat.id, 'У вас нет сохраненных файлов.')

def exit_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton('Мои файлы'))
    markup.row(types.KeyboardButton('Сохранить файл'), types.KeyboardButton('Получить файлы'))
    markup.row(types.KeyboardButton('Выход'))

    return markup


@bot.message_handler(commands=['start'])
def main(message):
    user_id = message.from_user.id
    bot.send_message(message.chat.id, f'Привет, {message.from_user.username}', reply_markup=start_markup())

    if user_id not in user_dict:
        user_dict[user_id] = {'name': None, 'password': None, 'is_admin': False}

    if user_dict[user_id]['name'] is not None:
        bot.send_message(message.chat.id, f'Привет, {user_dict[user_id]["name"]}! Вы уже зарегистрированы.')
        bot.send_message(message.chat.id, 'Выберите действие:', reply_markup=exit_markup())
    else:
        bot.send_message(message.chat.id, 'Выберите действие:', reply_markup=start_markup())

@bot.message_handler(func=lambda message: message.text.lower() == 'регистрация')
def register(message):
    user_id = message.from_user.id
    bot.send_message(message.chat.id, 'Введите имя для регистрации:')
    bot.register_next_step_handler(message, register_name)

def register_name(message):
    user_id = message.from_user.id
    user_dict[user_id]['name'] = message.text.strip()
    bot.send_message(message.chat.id, f'{user_dict[user_id]["name"]}, введите пароль для регистрации:')
    bot.register_next_step_handler(message, register_password)

def register_password(message):
    user_id = message.from_user.id
    user_dict[user_id]['password'] = message.text.strip()

    conn = sqlite3.connect('user.sql')
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE name=?", (user_dict[user_id]['name'],))
    existing_user = cur.fetchone()

    if existing_user:
        bot.send_message(message.chat.id, 'Пользователь с таким именем уже существует. Пожалуйста, выберите другое имя.')
        cur.close()
        conn.close()
        return

    cur.execute("INSERT INTO users (name, pass) VALUES (?, ?)", (user_dict[user_id]['name'], user_dict[user_id]['password']))
    conn.commit()
    cur.close()
    conn.close()

    bot.send_message(message.chat.id, f'Регистрация прошла успешно!', reply_markup=exit_markup())

@bot.message_handler(func=lambda message: message.text.lower() == 'авторизация')
def login(message):
    user_id = message.from_user.id
    bot.send_message(message.chat.id, 'Введите имя для входа:')
    bot.register_next_step_handler(message, login_name)

def login_name(message):
    user_id = message.from_user.id
    user_dict[user_id]['name'] = message.text.strip()
    bot.send_message(message.chat.id, f'{user_dict[user_id]["name"]}, введите пароль для входа:')
    bot.register_next_step_handler(message, login_check)

def login_check(message):
    user_id = message.from_user.id
    password = message.text.strip()

    conn = sqlite3.connect('user.sql')
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE name=? AND pass=?", (user_dict[user_id]['name'], password))
    existing_user = cur.fetchone()

    if existing_user:
        bot.send_message(message.chat.id, 'Вход выполнен успешно!', reply_markup=exit_markup())
    else:
        bot.send_message(message.chat.id, 'Неверное имя пользователя или пароль.')

    cur.close()
    conn.close()

@bot.message_handler(func=lambda message: message.text.lower() == 'выход')
def logout(message):
    user_id = message.from_user.id
    user_dict[user_id]['name'] = None
    user_dict[user_id]['password'] = None
    bot.send_message(message.chat.id, 'Вы успешно вышли из аккаунта.', reply_markup=start_markup())

#view_user_files()
@bot.message_handler(func=lambda message: message.text.lower() == 'мои файлы')
def view_user_files_command(message):
    view_user_files(message)

@bot.message_handler(commands=['savefile'])
def save_file(message):
    user_id = message.from_user.id
    bot.send_message(message.chat.id, 'Отправьте мне файл(ы) для сохранения.')

@bot.message_handler(content_types=['document'])
def handle_document(message):
    user_id = message.from_user.id
    file_info = bot.get_file(message.document.file_id)
    file_content = bot.download_file(file_info.file_path)

    file_extension = file_info.file_path.split('.')[-1].lower()

    user_dict[user_id]['files'] = {
        'name': None,
        'content': file_content,
        'file_extension': file_extension
    }

    bot.send_message(message.chat.id, 'Введите имя для сохранения файла:')
    bot.register_next_step_handler(message, save_file_name)

def save_file_name(message):
    user_id = message.from_user.id
    new_file_name = message.text.strip()

    conn = sqlite3.connect('user.sql')
    cur = conn.cursor()

    cur.execute("SELECT * FROM user_files WHERE user_id=? AND file_name=?", (user_id, new_file_name))
    existing_file = cur.fetchone()

    if existing_file:
        conn.close()
        bot.send_message(message.chat.id, f'Файл с именем "{new_file_name}" уже существует. Введите другое имя для сохранения файла:')
        bot.register_next_step_handler(message, save_file_name)  # Ask for a new file name
        return

    cur.execute("INSERT INTO user_files (user_id, file_name, file_content, file_extension) VALUES (?, ?, ?, ?)",
                (user_id, new_file_name, user_dict[user_id]['files']['content'], user_dict[user_id]['files']['file_extension']))
    conn.commit()
    conn.close()

    bot.send_message(message.chat.id, f'Файл успешно сохранён под именем: {new_file_name}')
    del user_dict[user_id]['files']


@bot.message_handler(commands=['getfile'])
def get_file(message):
    user_id = message.from_user.id
    bot.send_message(message.chat.id, 'Введите имя файла, который вы хотите получить:')


@bot.message_handler(func=lambda message: message.text.lower() == 'id')
def info(message):
    bot.reply_to(message, f'id: {message.from_user.id}')

@bot.message_handler(func=lambda message: message.text.lower() == 'сохранить файл')
def save_file_command(message):
    user_id = message.from_user.id
    bot.send_message(message.chat.id, 'Отправьте мне файл(ы) для сохранения.')

@bot.message_handler(func=lambda message: message.text.lower() == 'получить файлы')
def get_files_command(message):
    user_id = message.from_user.id
    bot.send_message(message.chat.id, 'Введите имя файла, который вы хотите получить:')

@bot.message_handler(func=lambda message: 'get_file' not in user_dict[message.from_user.id])
def get_file_name(message):
    user_id = message.from_user.id
    user_dict[user_id]['get_file'] = {'name': message.text.strip()}
    send_user_files(message, user_id)

def send_user_files(message, user_id):
    file_name = user_dict[user_id]['get_file']['name']

    conn = sqlite3.connect('user.sql')
    cur = conn.cursor()

    cur.execute("SELECT file_content, file_extension FROM user_files WHERE user_id=? AND file_name=?", (user_id, file_name))
    file_info = cur.fetchone()

    conn.close()

    if file_info:
        requested_file_extension = file_info[1].lower()

        file_data = io.BytesIO(file_info[0])
        file_path = f"{file_name}.{requested_file_extension}"
        with open(file_path, 'wb') as f:
            f.write(file_data.getvalue())

        with open(file_path, 'rb') as f:
            bot.send_document(message.chat.id, f)

        del user_dict[user_id]['get_file']
    else:
        bot.send_message(message.chat.id, 'Файл не найден.')

bot.polling(none_stop=True)
