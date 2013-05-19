import os
import shutil
import subprocess
import tarfile
import uuid
import zipfile

import settings

from utils import working_directory


class DoesNotExist(Exception):
    pass


class Job(object):

    def __init__(self, slug):
        job = settings.JOBS.get(slug, None)
        if job is None:
            raise DoesNotExist('Job does not exist')

        self.slug = slug
        self.title = job.get('title', '')
        self.description = job.get('description', '')
        self.base_dirname = job.get('base')
        self.expected_files = job.get('expected_files', [])
        self.command = job.get('command', [])

    @property
    def base_dir(self):
        return os.path.join(settings.JOBS_DIR, self.slug, self.base_dirname)

    def get_instance(self, instance_id):
        return Instance(self, instance_id=instance_id)


class Instance(object):

    def __init__(self, job, instance_id=None):
        if instance_id:
            self.id = instance_id
            if not os.path.exists(self.test_dir):
                raise DoesNotExist('Job instance does not exist')
        else:
            self.id = uuid.uuid4()
        self.job = job

    @property
    def test_dir(self):
        return os.path.join(settings.JOBS_DIR, self.job.slug, str(self.id))

    def _process_compressed_file(self, cls, list_method, filepath, mode):
        compressed_file = cls(filepath, mode=mode)
        namelist = getattr(compressed_file, list_method, lambda: [])
        if set(namelist()) != set(self.job.expected_files):
            raise Exception('Wrong compressed file contents')
        else:
            compressed_file.extractall(self.test_dir)
        compressed_file.close()

    def setup_from_compressed_file(self, compressed):
        shutil.copytree(self.job.base_dir, self.test_dir)

        dest_file = os.path.join(self.test_dir, compressed.filename)
        compressed.save(dest_file)

        if tarfile.is_tarfile(dest_file):
            self._process_compressed_file(
                tarfile.TarFile, 'getnames', dest_file, 'r:gz')
        elif zipfile.is_zipfile(dest_file):
            self._process_compressed_file(
                zipfile.ZipFile, 'namelist', dest_file, 'r')
        else:
            raise Exception('Unsupported file')

    def setup_from_files(self, *files):
        shutil.copytree(self.job.base_dir, self.test_dir)
        if len(files) != len(self.job.expected_files):
            raise Exception('Missing or unexpected file(s)')

        for f in files:
            if f.filename not in self.job.expected_files:
                raise Exception('Invalid filename: %s' % f.filename)
            dest_file = os.path.join(self.test_dir, f.filename)
            f.save(dest_file)

    def run(self):
        try:
            with working_directory(self.test_dir):
                try:
                    output = subprocess.check_output(
                        self.job.command, stderr=subprocess.STDOUT)
                except subprocess.CalledProcessError as e:
                    output = e.output
        except OSError:
            output = "Error trying to run command."

        output = output.decode('utf-8')
        return output