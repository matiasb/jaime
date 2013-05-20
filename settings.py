import os


PROJECT_DIR = os.path.dirname(__file__)

DEBUG = True
SECRET_KEY = "Your secret key here."

UPLOAD_FOLDER = os.path.join(PROJECT_DIR, 'output')
MAX_CONTENT_LENGTH = 0.1 * 1024 * 1024


JOBS_DIR = os.path.join(PROJECT_DIR, 'jobs')

# Timeout out in seconds for each run, None for unlimited
# (uses timeout command)
JOBS_TIMEOUT = 30

JOBS = {}
