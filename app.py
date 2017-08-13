import json
from flask import Flask
from flask import request
import requests
import structlog
from os import path
import os
import tarfile
from slugify import slugify
from urllib.parse import urlparse, parse_qs
import youtube_dl

from settings import (
    BOT_KEY,
    ADMIN_ID,
    STATIC_URL,
    DOWNLOAD_DIR,
    STATIC_DIR
)


app = Flask(__name__)
logger = structlog.get_logger(__name__)


@app.before_first_request
def setup_logging():
    pass


def send_message(chat_id, text):
    url_send_message = 'https://api.telegram.org/bot{bot_key}/sendMessage'.format(bot_key=BOT_KEY)
    payload = dict(chat_id=int(chat_id), text=text)
    return requests.post(url_send_message, data=payload)


def get_video_id(video_url):
    parsed_url = urlparse(url=video_url)
    video_id = parse_qs(qs=parsed_url.query).get('v', [None])[0]
    log = logger.bind(parsed_url=parsed_url, video_id=video_id)
    log.debug('Done parsing video', video_url=video_url)
    return video_id


def download_video(video_url, user_id):
    log = logger.bind(func='download_video', video_url=video_url, user_id=user_id)
    parsed_url = urlparse(url=video_url)
    video_id = get_video_id(video_url=video_url)
    log.debug('Downloading video')
    if parsed_url.path == '/watch' and 'youtube' in parsed_url.netloc and video_id:
        send_message(chat_id=user_id, text='downloading youtube video:{}'.format(video_url))
        ydl_opts = dict(
            writeautomaticsub=True,
            writesubtitles=True,
            subtitleslangs=['en', 'ru'],
            format='mp4[height=720]',
            outtmpl='{DOWNLOAD_DIR}/%(id)s/%(title)s.%(ext)s'.format(DOWNLOAD_DIR=DOWNLOAD_DIR)
        )
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            res = ydl.download([video_url])
            logger.debug('Video was downloaded', res=res)
        return process_video(video_id=video_id, user_id=user_id)
    log.debug('Invalid video url')
    return False


def subtitles_to_text(files, out_dir):
    def skip_header_and_timestamps(lines):
        header = True
        for line in lines:
            if '00:0' in line:
                header = False
            if not header and '-->' not in line:
                yield line

    def filter_crap(word):
        crap = [':', 'c.color']
        return all(c not in word for c in crap)

    def gen_lines_with_newlines(words):
        LINE_LEN = 80
        currlen = 0
        for word in words:
            if currlen > LINE_LEN:
                currlen = 0
                yield '\n'
            currlen += len(word)
            yield word

    subtitle_files = filter(lambda filename: filename.endswith('vtt'), files)
    for filename in subtitle_files:
        with open(path.join(out_dir, filename), 'r') as f:
            lines = f.readlines()
        lines = filter(None, '\n'.join(lines).splitlines())
        lines = list(skip_header_and_timestamps(lines=lines))
        clean_words = list()
        for line in lines:
            def filter_crap(word):
                crap = [':', 'c.color']
                return all(c not in word for c in crap)

            words = line.replace('>', ' ').replace('<', ' ').replace('/', ' ').replace(' c ', '').split(' ')
            clean_words.extend(filter(filter_crap, filter(None, words)))
        out_text = ' '.join(gen_lines_with_newlines(clean_words)).replace('\n ', '\n')
        out_filename = filename.replace('vtt', 'txt')
        with open(path.join(out_dir, out_filename), 'w') as outifle:
            outifle.write(out_text)
    return True


def process_video(video_id, user_id):
    log = logger.bind(func=process_video, video_id=video_id, user_id=user_id)
    log.debug('Starting processing video')
    out_dir = path.join(DOWNLOAD_DIR, video_id)
    files = os.listdir(out_dir)
    video_title = list(filter(lambda x: '.mp4' in x, files))[0].replace('.mp4', '')
    log.debug('Done extracting video infos', video_title=video_title, files=files)
    log.debug('Processing subtitle files')
    subtitles_to_text(files=files, out_dir=out_dir)
    log.debug('Gzipping')
    arch_name = path.join(STATIC_DIR, slugify(video_title) + '.tar.gz')
    with tarfile.open(arch_name, "w:gz") as tar:
        for file in files:
            tar.add(path.join(out_dir, file))
    log.debug('Done processing video')
    return True


@app.route("/", methods=['GET', 'POST'])
def main():
    log = logger
    logger.info('Got request', data=request.data)
    try:
        data_str = request.data.decode('utf8')
        ddict = json.loads(data_str)
    except (ValueError, TypeError) as e:
        log.exception('Cant deserialize json', e=e, data=request.data, exc_info=True, stack_info=True)
        return "Not a json"
    message = ddict.get('message', dict())
    log.debug('Got message', message=message)
    user_id = message.get('from', dict()).get('id')
    log = log.bind(user_id=user_id)
    log.debug('Got user_id')
    text = message.get('text', '')
    video_url = text.split(' ')[0]
    try:
        res = download_video(video_url=video_url, user_id=user_id)
        log.debug('download video result', res=res)
        if res:
            video_id = get_video_id(video_url=video_url)
            result_url = '{STATIC_URL}/{video_id}.tar.gz'.format(STATIC_URL=STATIC_URL, video_id=video_id)
            send_message(chat_id=user_id,
                         text='Processing ok, you can download results here {result_url}'.format(result_url=result_url))
            return 'Ok'
        else:
            send_message(chat_id=user_id, text='Invalid video url {url}'.format(url=video_url))
            return 'Invalid video'
    except Exception as e:  # Everything can happen
        log.exception('Download error', e=e, data=request.data, exc_info=True, stack_info=True)
        send_message(chat_id=user_id, text='Something bad happened, this incident is reported.\n'
                                           'Information above can help \n {}'.format(request.data))
        return str(e)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8181)
