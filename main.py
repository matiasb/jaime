import os

import jobs
import settings

import flask

from flask import (
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)


app = flask.Flask(__name__)
app.config.from_object(settings)


@app.context_processor
def available_jobs():
    """Make jobs available to templates through a context processor."""
    available_jobs = [jobs.Job(slug) for slug in settings.JOBS]
    return dict(jobs=available_jobs)


@app.errorhandler(404)
@app.route('/not-found')
def not_found(error=None):
    """Page not found."""
    return render_template('not_found.html'), 404


@app.route('/')
def index():
    """Jaime home."""
    return render_template('index.html')


@app.route('/job/<slug>/<instance_id>/logs/<filename>')
def output_file(slug, instance_id, filename):
    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        os.path.join(slug, instance_id, filename))


@app.route('/job/<slug>', methods=['GET', 'POST'])
def setup_new_instance(slug):
    """Set up a new job instance."""
    error = None

    try:
        job = jobs.Job(slug)
    except jobs.DoesNotExist:
        return redirect(url_for('not_found'))

    if request.method == 'POST':
        instance = jobs.Instance(job)
        compressed = request.files.get('compressed_file', None)
        if compressed:
            try:
                instance.setup_from_compressed_file(compressed)
            except Exception as e:
                error = str(e)
                instance.remove()
        elif job.individual_upload:
            uploaded_files = [f for f in request.files.values() if bool(f)]
            try:
                instance.setup_from_files(*uploaded_files)
            except Exception as e:
                error = str(e)
                instance.remove()
        else:
            error = 'Invalid job submission'

        if error is None:
            return redirect(
                url_for('run_output', instance_id=instance.id, slug=slug))

        flash(error, category='error')

    return render_template('detail.html', job=job)


@app.route('/job/<slug>/<instance_id>')
def run_output(slug, instance_id):
    """Run job instance and display output."""
    try:
        job = jobs.Job(slug)
        instance = job.get_instance(instance_id)
    except jobs.DoesNotExist:
        return redirect(url_for('not_found'))

    refresh = request.args.get('refresh', None)

    if not instance.completed or refresh:
        timeout = getattr(settings, 'JOBS_TIMEOUT', None)
        output = instance.run(timeout=timeout)
    else:
        output = instance.output

    return render_template(
        'output.html', instance_id=instance_id, job=job, output=output)


if __name__ == '__main__':
    app.run(port=5000, host='0.0.0.0')
