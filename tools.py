import os
import eyed3
import shutil
import requests
import colorama
from PIL import Image
from io import BytesIO
from yt_dlp import YoutubeDL
from string import punctuation
from ytmusicapi import YTMusic
from difflib import SequenceMatcher
from moviepy.editor import AudioFileClip

MissingTracksFolder = 'MissingTracks/'
TempFolder = 'temp/'

STATUS_CODE = {'Good': 0, 'IsExist': 1, 'NotFound': 2, 'ERROR': -1}


def find_unavailable_tracks(client):
    tracks = []
    tracks = client.users_playlists(3).tracks
    for track in tracks:
        track = track.fetch_track()
        if not track.available:
            tracks.append(get_track_fullname(track))
    return tracks


def find_track_yt(track):
    yt = YTMusic()
    search_results = yt.search(track, filter='songs', limit=10)
    track_title, track_artists = track.split(' - ')
    track_artists = track_artists.split(', ')[0]
    for song in search_results:
        search_title = song['title']
        search_artists = song['artists'][0]['name']
        title_sequence = SequenceMatcher(lambda x: x in punctuation, track_title, search_title).ratio()
        artists_sequence = SequenceMatcher(lambda x: x in punctuation, track_artists, search_artists).ratio()
        if (title_sequence + artists_sequence) / 2 >= 70:
            return "https://www.youtube.com/watch?v=" + song[0]['videoId']

    search_results = yt.search(track, filter='videos', limit=5)
    for video in search_results:
        if video['duration_seconds'] < 500:
            return "https://www.youtube.com/watch?v=" + video['videoId']

    return None


def find_missing_tracks(client):
    tracks = []
    all_track = [str(x.id) for x in client.users_playlists(3).tracks]
    like_track = [x.id for x in client.users_likes_tracks().tracks]
    c = set(all_track).difference(like_track)
    if len(c) == 0:
        return None
    for track in client.tracks(c):
        tracks.append(get_track_fullname(track))
    return tracks


def get_track_fullname(track):
    return track.title.replace('-', ' ') + ' - ' + ', '.join(map(lambda x: x.name, track.artists)).replace('-', ' ')


def convert_to_mp3(mp4file, mp3file):
    audio = AudioFileClip(mp4file)
    audio.write_audiofile(mp3file, logger=None)
    audio.close()


def download_dlp(name, url):
    filename = TempFolder + f"{name}.mp4"
    ydl_opts = {
        'quiet': True,
        'format': 'bestaudio/best',
        'keepvideo': False,
        'outtmpl': filename,
        'warnings': 'no-warnings',
        'noprogress': True
    }
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download(url)
    id = url.split('=')[1]
    return filename, id


def crop_img(img_data, is_small):
    pil_img = Image.open(BytesIO(img_data))
    img_width, img_height = pil_img.size
    if is_small:
        crop = 360
    else:
        crop = img_height
    img_new = pil_img.crop(((img_width - crop) // 2,
                            (img_height - crop) // 2,
                            (img_width + crop) // 2,
                            (img_height + crop) // 2))
    img_byte_arr = BytesIO()
    img_new.save(img_byte_arr, format='PNG')
    return img_byte_arr.getvalue()


def download_img(id):
    req = requests.get(f'https://i.ytimg.com/vi/{id}/maxresdefault.jpg')
    is_small = False

    if req.status_code == 404:
        req = requests.get(f'https://i.ytimg.com/vi/{id}//sddefault.jpg')
        is_small = True

    if req.status_code == 404:
        url = YTMusic().get_song(id)['videoDetails']['thumbnail']['thumbnails'][-1]['url']
        req = requests.get(url)
        is_small = False

    return crop_img(req.content, is_small)


def change_metadate(path, name, img):
    tag_name = name.split(' - ')
    audio_file = eyed3.load(path)
    audio_file.initTag()
    audio_file.tag.artist = tag_name[1]
    audio_file.tag.title = tag_name[0]
    audio_file.tag.images.set(3, img, 'image/jpeg')
    audio_file.tag.save()


def download_treck(name, url):
    filename, id = download_dlp(name, url)
    img_byte = download_img(id)
    path = MissingTracksFolder + name + '.mp3'
    convert_to_mp3(filename, path)
    change_metadate(path, name, img_byte)


def download_try(track):
    if os.path.exists(MissingTracksFolder + track + '.mp3'):
        return STATUS_CODE['IsExist']

    url = find_track_yt(track)
    if url is None:
        return STATUS_CODE['NotFound']

    download_treck(track, url)
    return STATUS_CODE['Good']


def output_status(status, track):
    if status is STATUS_CODE['Good']:
        print(f'\r{colorama.Fore.GREEN}Трек "{track}" установлен')
    elif status is STATUS_CODE['IsExist']:
        print(f'\r{colorama.Fore.YELLOW}Пропуск трек "{track}". Трек уже установлен')
    elif status is STATUS_CODE['NotFound']:
        print(f'\r{colorama.Fore.RED}Пропуск трек "{track}". Трек не найден')
    elif status is STATUS_CODE['ERROR']:
        print(f'\r{colorama.Fore.RED}Пропуск трек "{track}" Ошибка установки трека')


def download_all_treck(tracks):
    os.makedirs(MissingTracksFolder, exist_ok=True)
    shutil.rmtree(TempFolder, ignore_errors=True)
    for track in tracks:
        track = ''.join(list(filter(lambda c: c not in '\/:*?"<>|', track)))
        for i in range(3):
            try:
                print(f'{colorama.Fore.BLUE}Установка "{track}"... ')
                status = download_try(track)
                break
            except Exception:
                print(f'\n{colorama.Fore.RED}ОШИБКА. Попытка {i+1}/3')
                status = STATUS_CODE['ERROR']

        output_status(status, track)
