# -*- coding: utf-8 -*-

import six
import time
import hashlib
import os.path
import itertools
import datetime
from io import StringIO
from django.conf import settings
from dropbox import Dropbox, files
from django.core.files import File
from django.core.cache import cache
from dropbox.exceptions import ApiError
from django.core.files.storage import Storage
from django.utils.encoding import filepath_to_uri
from django.utils.deconstruct import deconstructible
from dropbox.files import FolderMetadata, FileMetadata

"""
Usage:
    document = models.FileField(
        verbose_name='Document',
        upload_to='dropbox:documents'
    )
"""


@deconstructible
class DropboxStorage(Storage):

    CHUNK_SIZE = 1 * 1024 * (settings.DEBUG and 1 or 1024)  # 1 Kb or 1Mb

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, '_instance'):
            cls._instance = super(DropboxStorage, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self, location='/'):
        self.client = None
        self.location = location
        self.base_url = 'https://dl.dropboxusercontent.com/'
        self.base_dir = settings.MEDIA_ROOT
        self.tmp_dir = os.path.join(settings.BASE_DIR, '.dropbox')
        self.log_file = os.path.join(settings.BASE_DIR, '.dropbox.log')
        if not os.path.exists(self.tmp_dir):
            os.mkdir(self.tmp_dir)
        if not os.path.exists(self.log_file):
            file = open(self.log_file, 'w')
            file.close()

    def _get_client(self):
        if not self.client:
            self.client = Dropbox(settings.DROPBOX_TOKEN)
        return self.client

    def _get_abs_path(self, name):
        return os.path.realpath(os.path.join(self.location, name))

    def _open(self, name, mode='rb'):
        local_file_path = os.path.join(self.tmp_dir, name)
        if os.path.exists(local_file_path):
            return File(open(local_file_path, mode))
        else:
            return DropboxFile(self._get_abs_path(name), self, mode=mode)

    def _save(self, name, content):
        name = self._get_abs_path(name)
        relative_path = self._get_abs_path(name)[1:]
        file_path = os.path.join(self.base_dir, relative_path)
        dir_path = os.path.dirname(file_path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        link_path = os.path.join(self.tmp_dir, relative_path)
        dir_path = os.path.dirname(link_path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        with open(file_path, 'wb') as f:
            f.write(content.read())
            f.close()
        os.symlink(file_path, link_path)
        return name

    def _print_progress(self, iteration, total, prefix='', suffix='', decimals=1, length=100, fill='█'):
        percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
        filled = int(length * iteration // total)
        bar = fill * filled + '-' * (length - filled)
        if settings.DEBUG and 0:
            print('\r%s |%s| %s%% %s' % (prefix, bar, percent, suffix), end='\r')
        else:
            self._log('{}%'.format(percent))
        if iteration == total:
            if settings.DEBUG:
                print('')
            else:
                self._log('100%')

    def _log(self, info, sep='\n'):
        formated_time = datetime.datetime.now().strftime("[%d/%b/%Y %H:%M:%S]")
        if settings.DEBUG and 0:
            print('{} {}'.format(formated_time, info))
        else:
            file = open(self.log_file, 'a')
            file.write('{} {}'.format(formated_time, info))
            file.write(sep)
            file.close()

    def path(self, name):
        return os.path.join(self.base_dir, name)

    def delete(self, name):
        name = self._get_abs_path(name)
        self._get_client().files_delete_v2(name)

    def exists(self, name):
        try:
            self._get_client().files_get_metadata(name)
        except ApiError as e:
            if e.error.is_path() and e.error.get_path().is_not_found():
                return False
            raise e
        return True

    def exists_locally(self, name):
        return os.path.exists(os.path.join(self.base_dir, name))

    def listdir(self, path):
        path = self._get_abs_path(path)
        response = self._get_client().files_list_folder(path)
        directories = []
        files = []
        for entry in response.entries:
            if type(entry) == FolderMetadata:
                directories.append(os.path.basename(entry.path_display))
            elif type(entry) == FileMetadata:
                files.append(os.path.basename(entry.path_display))
        return directories, files

    def size(self, name):
        cache_key = 'django-dropbox-size:{}'.format(filepath_to_uri(name))
        size = cache.get(cache_key)
        if not size:
            size = self._get_client().files_get_metadata(name).size
            cache.set(cache_key, size, 3600 * 24 * 365)
        return size

    def url(self, name):
        return '/cloud/{}'.format(self._get_abs_path(name)[1:])

    def remote_url(self, name):
        cache_key = 'django-dropbox-size:{}'.format(filepath_to_uri(name))
        url = cache.get(cache_key)
        if not url:
            url = self._get_client().files_get_temporary_link(name).link
            cache.set(cache_key, url, 3600 * 3)
        return url

    def get_available_name(self, name, max_length=None):
        name = self._get_abs_path(name)
        dir_name, file_name = os.path.split(name)
        file_root, file_ext = os.path.splitext(file_name)
        count = itertools.count(1)
        while self.exists(name):
            name = os.path.join(dir_name, "%s_%s%s" % (file_root, next(count), file_ext))
        return name

    def sync(self):
        self._log('Starting sync on dir {}...'.format(self.tmp_dir))
        while True:
            for file_path in [os.path.join(dp, f) for dp, dn, names in os.walk(self.tmp_dir) for f in names]:
                local_hash = DropboxContentHasher.calculate(file_path)
                remote_path = file_path[len(self.tmp_dir):]
                if not self.exists(remote_path):
                    directory = os.path.dirname(remote_path)
                    if directory and not self.exists(directory):
                        self._get_client().files_create_folder_v2(directory)
                    with open(file_path, 'rb') as f:
                        file_size = os.path.getsize(file_path)
                        self._log('Uploading {} [{} bytes] ({}) to {}...'.format(
                            file_size, file_path, local_hash, remote_path)
                        )
                        if file_size <= self.CHUNK_SIZE:
                            self._get_client().files_upload(f.read(), remote_path)
                        else:
                            self._log('Starting session...')
                            upload_session_start_result = self._get_client().files_upload_session_start(
                                f.read(self.CHUNK_SIZE)
                            )
                            cursor = files.UploadSessionCursor(
                                session_id=upload_session_start_result.session_id,
                                offset=f.tell()
                            )
                            commit = files.CommitInfo(path=remote_path)
                            while f.tell() < file_size:
                                self._print_progress(f.tell(), file_size)
                                if file_size - f.tell() <= self.CHUNK_SIZE:
                                    self._get_client().files_upload_session_finish(
                                        f.read(self.CHUNK_SIZE), cursor, commit
                                    )
                                    self._print_progress(file_size, file_size)
                                    self._log('Session closed!')
                                else:
                                    self._get_client().files_upload_session_append_v2(
                                        f.read(self.CHUNK_SIZE), cursor
                                    )
                                    cursor.offset = f.tell()
                        self._log('Upload completed!')
                        local_hash = DropboxContentHasher.calculate(file_path)
                remote_hash = self._get_client().files_get_metadata(remote_path).content_hash
                self._log('Remote file found with hash {}!'.format(remote_hash))
                if local_hash == remote_hash:
                    self._log('Removing {}...'.format(file_path))
                    os.unlink(file_path)
                    self._log('File successfully uploaded: {} '.format(file_path))
            sleep_time = settings.DEBUG and 10 or 60*60
            self._log('Sleeping for {} seconds...'.format(sleep_time))
            time.sleep(sleep_time)


class DropboxFile(File):

    def __init__(self, name, storage, mode):
        self._storage = storage
        self._mode = mode
        self._is_dirty = False
        self.file = StringIO()
        self.start_range = 0
        self._name = name

    @property
    def size(self):
        if not hasattr(self, '_size'):
            self._size = self._storage.size(self._name)
        return self._size

    def read(self, num_bytes=None):
        metadata, response = self._storage.client.files_download(self._name)
        return response.content

    def write(self, content):
        if 'w' not in self._mode:
            raise AttributeError("File was opened for read-only access.")
        self.file = StringIO(content)
        self._is_dirty = True

    def close(self):
        if self._is_dirty:
            self._storage.client.files_upload(self.file.getvalue(), self._name)
        self.file.close()


class DropboxContentHasher(object):

    BLOCK_SIZE = 4 * 1024 * 1024

    def __init__(self):
        self._overall_hasher = hashlib.sha256()
        self._block_hasher = hashlib.sha256()
        self._block_pos = 0

        self.digest_size = self._overall_hasher.digest_size

    def update(self, new_data):
        if self._overall_hasher is None:
            raise AssertionError(
                "can't use this object anymore; you already called digest()")

        assert isinstance(new_data, six.binary_type), (
            "Expecting a byte string, got {!r}".format(new_data))

        new_data_pos = 0
        while new_data_pos < len(new_data):
            if self._block_pos == self.BLOCK_SIZE:
                self._overall_hasher.update(self._block_hasher.digest())
                self._block_hasher = hashlib.sha256()
                self._block_pos = 0

            space_in_block = self.BLOCK_SIZE - self._block_pos
            part = new_data[new_data_pos:(new_data_pos+space_in_block)]
            self._block_hasher.update(part)

            self._block_pos += len(part)
            new_data_pos += len(part)

    def _finish(self):
        if self._overall_hasher is None:
            raise AssertionError(
                "can't use this object anymore; you already called digest() or hexdigest()")

        if self._block_pos > 0:
            self._overall_hasher.update(self._block_hasher.digest())
            self._block_hasher = None
        h = self._overall_hasher
        self._overall_hasher = None
        return h

    def digest(self):
        return self._finish().digest()

    def hexdigest(self):
        return self._finish().hexdigest()

    def copy(self):
        c = DropboxContentHasher.__new__(DropboxContentHasher)
        c._overall_hasher = self._overall_hasher.copy()
        c._block_hasher = self._block_hasher.copy()
        c._block_pos = self._block_pos
        return c

    @staticmethod
    def calculate(file_path):
        hasher = DropboxContentHasher()
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(1024)
                if len(chunk) == 0:
                    break
                hasher.update(chunk)
        return hasher.hexdigest()


class StreamHasher(object):

    def __init__(self, f, hasher):
        self._f = f
        self._hasher = hasher

    def close(self):
        return self._f.close()

    def flush(self):
        return self._f.flush()

    def fileno(self):
        return self._f.fileno()

    def tell(self):
        return self._f.tell()

    def read(self, *args):
        b = self._f.read(*args)
        self._hasher.update(b)
        return b

    def write(self, b):
        self._hasher.update(b)
        return self._f.write(b)

    def next(self):
        b = self._f.next()
        self._hasher.update(b)
        return b

    def readline(self, *args):
        b = self._f.readline(*args)
        self._hasher.update(b)
        return b

    def readlines(self, *args):
        b = None
        bs = self._f.readlines(*args)
        for b in bs:
            self._hasher.update(b)
        return b
