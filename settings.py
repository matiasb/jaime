import os


PROJECT_DIR = os.path.dirname(__file__)
JOBS_DIR = os.path.join(PROJECT_DIR, 'jobs')
DEBUG = True
SECRET_KEY = "Your secret key here."
MAX_CONTENT_LENGTH = 0.1 * 1024 * 1024

JOBS = {}

# Timeout out in seconds for each run, None for unlimited
# (uses timeout command)
JOBS_TIMEOUT = 15
