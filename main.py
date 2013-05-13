import os
import shutil
import subprocess
import uuid

import settings
from utils import working_directory

import flask
from flask import flash, redirect, render_template, request, url_for


app = flask.Flask(__name__)
app.config.from_object(settings)


@app.context_processor
def available_jobs():
    """Make jobs available to templates through a context processor."""
    jobs = settings.JOBS
    return dict(jobs=jobs)


@app.errorhandler(404)
def not_found(error):
    """Page not found."""
    return render_template('not_found.html'), 404


@app.route('/')
def index():
    """Jaime home."""
    return render_template('index.html')


@app.route('/job/<slug>', methods=['GET', 'POST'])
def setup_new_instance(slug):
    """Set up a new job instance."""
    error = None
    job = settings.JOBS.get(slug, None)

    if job is None:
        redirect(url_for('not_found'))

    if request.method == 'POST':
        instance_id = uuid.uuid4()
        base_dir = os.path.join(settings.JOBS_DIR, slug, job['base'])
        test_dir = os.path.join(settings.JOBS_DIR, slug, str(instance_id))

        shutil.copytree(base_dir, test_dir)
        for field, uploaded_file in request.files.iteritems():
            if uploaded_file.filename not in job['expected_files']:
                error = 'Incorrect filename: %s' % uploaded_file.filename
                break
            uploaded_file.save(os.path.join(test_dir, uploaded_file.filename))

        if error is None:
            return redirect(
                url_for('run_output', instance_id=instance_id, slug=slug))

        flash(error, category='error')

    return render_template('detail.html', job=job)


@app.route('/job/<slug>/<instance_id>')
def run_output(slug, instance_id):
    """Run job instance and display output."""
    job = settings.JOBS.get(slug, None)

    if job is None:
        redirect(url_for('not_found'))

    test_dir = os.path.join(settings.JOBS_DIR, slug, instance_id)
    try:
        with working_directory(test_dir):
            try:
                output = subprocess.check_output(
                    job['command'], stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError as e:
                output = e.output
    except OSError:
        output = "Error trying to run command."

    output = output.decode('utf-8')
    return render_template(
        'output.html', instance_id=instance_id, job=job, output=output)


if __name__ == '__main__':
    app.run(port=5000, host='0.0.0.0')
