import codecs
import os
import re
import shutil
import subprocess
import tarfile
import uuid
import zipfile

import settings

from utils import working_directory


class DoesNotExist(Exception):
    pass


class InvalidCompressedFileError(Exception):

    def __init__(self, missing=None, extra=None):
        self.missing = missing
        self.extra = extra

    def __str__(self):
        msg = 'Invalid content'
        if self.missing:
            msg += ': You are missing %s' % ', '.join(self.missing)
        if self.extra:
            msg += ' (unneeded files: %s)' % ', '.join(self.extra)
        return msg


class Job(object):

    def __init__(self, slug):
        job = settings.JOBS.get(slug, None)
        if job is None:
            raise DoesNotExist('Job does not exist')

        self.slug = slug
        self.title = job.get('title', '')
        self.description = job.get('description', '')
        self.base_dirname = job.get('base')
        self.individual_upload = job.get('allow_individual_upload', True)

        compressed_file = job.get('compressed_file', None)
        if compressed_file is not None and isinstance(compressed_file, tuple):
            self.compressed_label = compressed_file[0]
            self.compressed_name = compressed_file[1]
        else:
            self.compressed_label = compressed_file
            self.compressed_name = None

        self.compressed_file = job.get('expected_filename', None)
        self.expected_files = job.get('expected_files', [])
        self.output_files = [settings.OUTPUT_FILENAME]
        self.output_files.extend(job.get('output_files', []))
        self.command = job.get('command', [])

    @property
    def base_dir(self):
        return os.path.join(settings.JOBS_DIR, self.slug, self.base_dirname)

    def get_instance(self, instance_id):
        return Instance(self, instance_id=instance_id)


class Instance(object):

    def __init__(self, job, instance_id=None):
        self.job = job
        if instance_id:
            self.id = instance_id
            if not os.path.exists(self.test_dir):
                raise DoesNotExist('Job instance does not exist')
        else:
            self.id = str(uuid.uuid4())

    @property
    def output_file(self):
        return os.path.join(self.test_dir, settings.OUTPUT_FILENAME)

    @property
    def output_dir(self):
        return os.path.join(settings.UPLOAD_FOLDER, self.job.slug, self.id)

    @property
    def test_dir(self):
        return os.path.join(settings.JOBS_DIR, self.job.slug, self.id)

    @property
    def completed(self):
        return os.path.exists(self.output_file)

    @property
    def output(self):
        output = None
        if os.path.exists(self.output_file):
            with codecs.open(self.output_file, 'r', 'utf-8') as f:
                output = f.read()
        return output

    def _process_compressed_file(self, cls, list_method, filepath, mode):
        compressed_file = cls(filepath, mode=mode)
        namelist = getattr(compressed_file, list_method, lambda: [])
        expected = set(self.job.expected_files)
        provided = set(namelist())
        if set(namelist()) != set(self.job.expected_files):
            missing = expected - provided
            extra = provided - expected
            raise InvalidCompressedFileError(missing=missing, extra=extra)
        else:
            compressed_file.extractall(self.test_dir)
        compressed_file.close()

    def _validate_filename(self, regex, filename):
        if regex is not None:
            if not re.match(regex, filename):
                raise Exception('Invalid filename')

    def setup_from_compressed_file(self, compressed):
        self._validate_filename(self.job.compressed_name, compressed.filename)
        shutil.copytree(self.job.base_dir, self.test_dir)

        dest_file = os.path.join(self.test_dir, compressed.filename)
        compressed.save(dest_file)

        if tarfile.is_tarfile(dest_file):
            self._process_compressed_file(
                tarfile.open, 'getnames', dest_file, 'r:gz')
        elif zipfile.is_zipfile(dest_file):
            self._process_compressed_file(
                zipfile.ZipFile, 'namelist', dest_file, 'r')
        else:
            raise Exception('Not supported compressed file')

    def setup_from_files(self, *files):
        shutil.copytree(self.job.base_dir, self.test_dir)
        if len(files) != len(self.job.expected_files):
            raise Exception('Missing or unexpected file(s)')

        for f in files:
            if f.filename not in self.job.expected_files:
                raise Exception('Invalid filename: %s' % f.filename)
            dest_file = os.path.join(self.test_dir, f.filename)
            f.save(dest_file)

    def run(self, timeout=None):
        return_code = None
        command = self.job.command
        if timeout is not None:
            command = ['timeout', str(timeout)] + self.job.command

        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        with working_directory(self.test_dir):
            with codecs.open(settings.OUTPUT_FILENAME, 'w', 'utf-8') as f:
                try:
                    return_code = subprocess.call(
                        command, stdout=f, stderr=subprocess.STDOUT)

                    if return_code == 124:
                        # return code from timeout command when expired
                        f.write('\n***** TIMEOUT ERROR *****\n')
                except OSError:
                    f.write("Error trying to run command.")

            for filename in self.job.output_files:
                if os.path.exists(filename):
                    dest_file = os.path.join(self.output_dir, filename)
                    shutil.copyfile(filename, dest_file)

        return return_code

    def remove(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
