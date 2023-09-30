from flask import Flask, request, render_template, redirect, url_for
import os
import boto3
import botocore
from decouple import config
from io import BytesIO

app = Flask(__name__)

# Configure AWS S3
AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
S3_BUCKET = config('S3_BUCKET')
S3_REGION = config('S3_REGION')

s3 = boto3.client('s3', region_name=S3_REGION, aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'video' not in request.files:
        return redirect(request.url)

    video = request.files['video']

    if video.filename == '':
        return redirect(request.url)

    # Upload the video to S3
    try:
        s3.upload_fileobj(video, S3_BUCKET, video.filename)
    except botocore.exceptions.NoCredentialsError:
        return "AWS S3 credentials not configured.", 500

    return redirect(url_for('play', video_filename=video.filename))

@app.route('/play/<video_filename>')
def play(video_filename):
    s3_url = generate_s3_url(S3_BUCKET, video_filename)
    return render_template('play.html', s3_url=s3_url)

def generate_s3_url(bucket, key):
    s3_url = f"https://{bucket}.s3.amazonaws.com/{key}"
    return s3_url

if __name__ == '__main__':
    app.run(debug=True)
