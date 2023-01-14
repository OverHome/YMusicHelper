import tools
from yandex_music import Client
from selenium_brouser import get_token

print('Приветствую, это помощник для сервиса YandexMusic')
print('Хотите войти в свой аккаунт по логину и паролю? Y/n')
if (input()[0].upper()=="Y"):
    client = Client(get_token())
else:
    client = Client(input("Тогда введите токен: "))

print("Проверка подключения")
try:
    client.init()
except Exception:
    pass
if client.token is None or client.me is None:
    print("Ошибка подключения")
    exit(-1)

print("Поиск треков")
tracks = tools.find_missing_tracks(client)
if tracks is not None:
    print('\n'.join([tracks[i] for i in range(len(tracks))]), '\n')
    print(f'Найдено {len(tracks)} треков. Хотите их скачать? Y/n')

    if (input()[0].upper() == "Y"):
        print("Скачивание")
        tools.download_all_treck(tracks)
else:
    print("Все на своих местах")