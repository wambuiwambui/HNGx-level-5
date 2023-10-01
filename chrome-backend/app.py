from flask import Flask, request, jsonify
import boto3
import botocore
from decouple import config
import threading  # Import threading module
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Configure AWS S3
AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
S3_BUCKET = config('S3_BUCKET')
S3_REGION = config('S3_REGION')

# Initialize S3 client
s3 = boto3.client('s3', region_name=S3_REGION, aws_access_key_id=AWS_ACCESS_KEY_ID,
                  aws_secret_access_key=AWS_SECRET_ACCESS_KEY)

# Initialize Amazon Transcribe client
transcribe = boto3.client('transcribe', region_name=S3_REGION,
                        aws_access_key_id=AWS_ACCESS_KEY_ID,
                        aws_secret_access_key=AWS_SECRET_ACCESS_KEY)

def start_transcription_job(video_filename, s3_url):
    try:
        # Create a transcription job
        job_name = f"transcription-{video_filename}"
        transcribe.start_transcription_job(
            TranscriptionJobName=job_name,
            LanguageCode='en-US',
            MediaFormat='mp4',
            Media={
                'MediaFileUri': s3_url
            },
            OutputBucketName=S3_BUCKET
        )
    except Exception as e:
        print(f"Error starting transcription job: {str(e)}")

@app.route('/upload', methods=['POST'])
def upload():
    if 'video' not in request.files:
        return jsonify({"message": "Please upload a video file"}), 401

    video = request.files['video']

    if video.filename == '':
        return jsonify({"message": "Please add a video file name"}), 401

    # Upload the video to S3
    try:
        s3.upload_fileobj(video, S3_BUCKET, video.filename)
    except botocore.exceptions.NoCredentialsError:
        return jsonify({"message": "AWS S3 credentials not configured"}), 401

    s3_url = generate_s3_url(S3_BUCKET, video.filename)
    transcribe_s3_url = generate_transcribed_s3_url(S3_BUCKET, f"transcription-{video.filename}")

    # Start transcription job in a separate thread
    transcription_thread = threading.Thread(target=start_transcription_job, args=(video.filename, s3_url))
    transcription_thread.start()

    return jsonify({"video_name": video.filename, "url": s3_url, "transcription_job_started": True, "transcribe_url": transcribe_s3_url}), 202

@app.route('/play/<video_filename>')
def play(video_filename):
    s3_url = generate_s3_url(S3_BUCKET, video_filename)
    return jsonify({"video_name": video_filename, "url": s3_url}), 200

def generate_s3_url(bucket, key):
    s3_url = f"https://{bucket}.s3.amazonaws.com/{key}"
    return s3_url

def generate_transcribed_s3_url(bucket, key):
    transcribe_s3_url = f"https://{bucket}.s3.amazonaws.com/{key}"
    return transcribe_s3_url
if __name__ == '__main__':
    app.run(debug=True, port=5001)
