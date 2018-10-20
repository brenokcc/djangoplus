# -*- coding: utf-8 -*-
import os
from django.conf import settings
from subprocess import Popen, DEVNULL
from django.core.management.base import BaseCommand

from djangoplus.tools.video import VideoUploader, VideoRecorder


class Command(BaseCommand):

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument('video', default=None, nargs='?')
        parser.add_argument('--delete', action='store_true', dest='delete', default=False, help='Deletes the video')
        parser.add_argument('--upload', action='store_true', dest='upload', default=False,
                            help='Uploads the video if it has not been uploaded yet')
        parser.add_argument('--force-upload', action='store_true', dest='force_upload', default=False,
                            help='Uploads the video even it has already been uploaded')
        parser.add_argument('--clear', action='store_true', dest='clear', default=False,
                            help='Deletes all uploaded videos')

    def handle(self, *args, **options):
        youtube = VideoUploader()
        video = options.get('video')
        delete = options.get('delete')
        upload = options.get('upload')
        force_upload = options.get('force_upload')
        clear = options.get('clear')
        if video:
            if upload or force_upload:
                video_path = '{}/{}'.format(settings.BASE_DIR, video)
                if os.path.exists(video_path):
                    title = VideoRecorder.metadata(video_path).get('title', video)
                    youtube.upload_video(video_path, title, force=force_upload)
                else:
                    print('Video {} does not exists.'.format(video_path))
            elif delete:
                if video.endswith('.mkv'):
                    video_path = '{}/{}'.format(settings.BASE_DIR, video)
                    if os.path.exists(video_path):
                        os.unlink(video_path)
                        print('The video {} deleted from file system.'.format(video_path))
                    else:
                        print('The video {} does not exists.'.format(video_path))
                else:
                    youtube.delete_video(video)
            else:
                vlc = None
                if os.path.exists('/Applications/VLC.app/Contents/MacOS/VLC'):
                    vlc = '/Applications/VLC.app/Contents/MacOS/VLC'
                elif os.path.exists('/usr/bin/vlc'):
                    vlc = '/usr/bin/vlc'
                if vlc:
                    cmd = '{} --play-and-exit --fullscreen {}'.format(vlc, video)
                    Popen(cmd.split(), stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL)
                else:
                    print('VLC is not installed!')
        else:
            directory = '{}/videos'.format(settings.BASE_DIR)

            local_videos = []
            if os.path.exists(directory):
                for file_name in os.listdir(directory):
                    if '.mkv' in file_name:
                        url = 'videos/{}'.format(file_name)
                        video_path = os.path.join(directory, file_name)
                        title = VideoRecorder.metadata(video_path).get('title', file_name)
                        local_video = dict(file_name=file_name, url=url, title=title, video_path=video_path)
                        local_videos.append(local_video)

            if upload or force_upload:
                for local_video in local_videos:
                    youtube.upload_video(local_video['video_path'], local_video['title'], force=force_upload)
            elif clear:
                for uploaded_video in youtube.list_videos():
                    youtube.delete_video(uploaded_video['id'])
            else:
                print('LOCAL VIDEOS')
                if local_videos:
                    for local_video in local_videos:
                        print('{}\t{}\t{}'.format(local_video['file_name'], local_video['url'], local_video['title']))
                else:
                    print('No local video was found!')

                print('\nUPLOADED VIDEOS')
                uploaded_videos = youtube.list_videos()
                if uploaded_videos:
                    for uploaded_video in uploaded_videos:
                        url = 'https://www.youtube.com/watch?v={}'.format(uploaded_video['id'])
                        print('{}\t{}\t{}'.format(uploaded_video['id'], url, uploaded_video['snippet']['title']))
                else:
                    print('No uploaded video was found!')
