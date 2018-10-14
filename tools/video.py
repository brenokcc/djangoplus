# -*- coding: utf-8 -*-
import re
import platform
import os
import signal
from time import sleep
from subprocess import Popen, PIPE, DEVNULL
from django.conf import settings

from djangoplus.utils import to_ascii


class Subtitle(object):

    @staticmethod
    def display(message, duration=4):
        import tkinter as tk
        root = tk.Tk()
        root.overrideredirect(True)
        root.wm_attributes("-topmost", True)
        root.attributes('-alpha', 0.8)
        root.configure(background='black')
        lines = list()
        break_line = False
        for i, letter in enumerate(message):
            if break_line or i and i % 50 == 0:
                if letter == ' ':
                    lines.append('\n')
                    break_line = False
                else:
                    break_line = True
            lines.append(letter)
        message = ''.join(lines)
        line_breaks = message.count('\n')
        if 'darwin' in platform.system().lower():
            font_size, width, top, right = 30, 82, int(root.winfo_screenwidth() / 2 - 20 * 35), int(
                root.winfo_screenheight() - [90, 120, 156][line_breaks])
        else:
            font_size, width, top, right = 20, 70, int(root.winfo_screenwidth() / 2 - 70 * 7.5), int(
                root.winfo_screenheight() - [77, 110, 140][line_breaks])
        label = tk.Label(root, text=message, font=("Helvetica", font_size), width=width, height=2 + line_breaks)
        label.configure(foreground="white", background='black')
        label.pack(expand=tk.YES, fill=tk.BOTH)
        root.geometry("+{}+{}".format(top, right))
        root.after(1000 * duration, lambda: root.destroy())
        root.mainloop()


class VideoRecorder(object):
    def __init__(self):
        self.proccess = None

    def start(self):
        if 'darwin' in platform.system().lower():
            list_divices_procces = Popen('ffmpeg -f avfoundation -list_devices true -i ""'.split(), stdout=PIPE, stderr=PIPE)
            output, err = list_divices_procces.communicate()
            i = 0
            for line in err.decode('utf-8').split('\n'):
                if 'capture screen' in line.lower():
                    for i in range(0, 3):
                        if '[{}]'.format(i) in line:
                            break
            self.proccess = Popen(['ffmpeg', '-y', '-f', 'avfoundation', '-i', str(i), '/tmp/video.mkv'], stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL)
        else:
            xrandr = Popen("xrandr".split(), stdout=PIPE)
            sizes = xrandr.stdout.readlines()
            size = re.findall(r'\d+x\d+', [line.decode('utf-8').strip().split()[0] for line in sizes if '*' in line.decode('utf-8')][0])[0]
            cmd = 'ffmpeg -video_size {} -framerate 25 -f x11grab -i :0.0+0,0 -f pulse -ac 2 -i default /tmp/video.mkv'
            self.proccess = Popen(cmd.format(size).split(), stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL)
        sleep(5)

    def stop(self, title=None, output_dir=None, audio_file_path=None):

        if self.proccess:
            os.kill(self.proccess.pid, signal.SIGTERM)
            if title:
                tmp_file_path = '/tmp/video.mkv'
                if not output_dir:
                    output_dir = os.path.join(os.path.join(os.path.expanduser('~')), 'Desktop')
                    if not os.path.exists(output_dir):
                        output_dir = os.path.join(os.path.expanduser('~'))
                if not os.path.exists(output_dir):
                    os.mkdir(output_dir)

                output_file_path = '{}/{}.mkv'.format(output_dir, to_ascii(title).replace(' ', '_'))
                if os.path.exists(output_file_path):
                    os.unlink(output_file_path)

                if self.proccess:
                    os.kill(self.proccess.pid, signal.SIGTERM)
                    sleep(2)
                    os.rename(tmp_file_path, output_file_path)

                    print('Video Ouput: {}'.format(output_file_path))
                    if audio_file_path and os.path.exists(audio_file_path) and 'darwin' in platform.system().lower():
                        output_audio_path = '/tmp/video-audio.mkv'
                        combine_audio_cmd = 'ffmpeg -y -i {} -i {} -c copy -map 0:0 -map 1:0 -shortest {}  > /dev/null 2>&1'
                        os.system(combine_audio_cmd.format(output_file_path, audio_file_path, output_audio_path))
                        sleep(5)
                        os.rename(output_audio_path, output_file_path)

                    cmd = 'ffmpeg -y -i {} -metadata title="{}" {}'.format(output_file_path, title, tmp_file_path)
                    Popen(cmd, stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL, shell=True).wait()
                    os.rename(tmp_file_path, output_file_path)

                return output_file_path
        return None

    @staticmethod
    def metadata(file_path):
        cmd = 'ffmpeg -y -i {} -f ffmetadata /tmp/metadata.txt'.format(file_path)
        Popen(cmd, stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL, shell=True).wait()
        metadata = {}
        for line in open('/tmp/metadata.txt').readlines():
            if '=' in line:
                tokens = line.strip().split('=')
                metadata[tokens[0]] = tokens[1]
        return metadata


class VideoUploader(object):

    SCOPES = [
        'https://www.googleapis.com/auth/youtube',
        'https://www.googleapis.com/auth/youtube.force-ssl',
        'https://www.googleapis.com/auth/youtube.readonly',
        'https://www.googleapis.com/auth/youtube.upload'
    ]
    API_SERVICE_NAME = 'youtube'
    API_VERSION = 'v3'

    AUTH_URI = 'https://accounts.google.com/o/oauth2/auth'
    TOKEN_URI = 'https://www.googleapis.com/oauth2/v3/token'
    AUTH_CERT_URL = 'https://www.googleapis.com/oauth2/v1/certs'

    PROJECT_ID = 'youtube-215812'
    CLIENT_ID = '289626547199-v2476ui09vqqjgbl607n2lcsq7arq0u0.apps.googleusercontent.com'
    CLIENT_SECRET = 'QjWNSUt_ILAytbnROoSAdv7m'

    def __init__(self):

        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from google_auth_oauthlib.flow import InstalledAppFlow

        client_config = {"installed": {
            'client_id': VideoUploader.CLIENT_ID,
            'project_id': VideoUploader.PROJECT_ID, 'auth_uri': VideoUploader.AUTH_URI,
            'token_uri': VideoUploader.TOKEN_URI,
            'auth_provider_x509_cert_url': VideoUploader.AUTH_CERT_URL,
            'client_secret': VideoUploader.CLIENT_SECRET}
        }

        credentials = Credentials(None, refresh_token="1/8nCdTJu1q8xGwPMRiorcWP8XgoOBkwyinSX3MYQRsmo", token_uri="https://accounts.google.com/o/oauth2/token", client_id=VideoUploader.CLIENT_ID, client_secret=VideoUploader.CLIENT_SECRET)

        if not credentials:
            flow = InstalledAppFlow.from_client_config(client_config, VideoUploader.SCOPES)
            credentials = flow.run_console()
            import pdb; pdb.set_trace()

        self.service = build(VideoUploader.API_SERVICE_NAME, VideoUploader.API_VERSION, credentials=credentials)

    def list_videos(self):
        videos_ids = [item['id']['videoId'] for item in self.service.search().list(forMine=True, type="video", part="id,snippet", fields='items(id)').execute()['items']]
        videos = [video for video in self.service.videos().list(part="id,snippet", id=','.join(videos_ids), fields='items(id,snippet/tags,snippet/title,snippet/description)').execute()['items'] if settings.PROJECT_NAME in video.get('snippet', {}).get('tags', [])]
        return videos

    def delete_video(self, video_id):
        self.service.videos().delete(id=video_id).execute()
        print('Video "{}" deleted from Youtube.'.format(video_id))

    def upload_video(self, file_path, title, force=False):
        self.upload_videos([(file_path, title)], force=force)

    def upload_videos(self, tuples, force=False):
        from googleapiclient.http import MediaFileUpload
        uploaded_titles = {}
        for video in self.list_videos():
            uploaded_titles[video['snippet']['title']] = video['id']
        tags = [settings.PROJECT_NAME]
        for file_path, title in tuples:
            if title not in uploaded_titles or force:
                response = None

                if force and title in uploaded_titles:
                    video_id = uploaded_titles[title]
                    self.delete_video(video_id)

                body = dict(
                    snippet=dict(title=title, description='', tags=tags, categoryId='22'),
                    status=dict(privacyStatus='public')
                )

                media_body = MediaFileUpload(file_path, chunksize=-1, resumable=True)
                request = self.service.videos().insert(
                    part=','.join(body.keys()), body=body, media_body=media_body
                )

                while response is None:
                    print('Uploading file "{}"...'.format(file_path))
                    status, response = request.next_chunk()
                    if response is not None:
                        if 'id' in response:
                            url = 'http://www.youtube.com/embed/{}?rel=0&autoplay=1'.format(response['id'])
                            print('The video was successfully uploaded. {}'.format(url))
                        else:
                            exit('The upload failed with an unexpected response: %s' % response)
            else:
                print('The video "{}" has already been uploaded. Force upload if it should be replaced.'.format(title))