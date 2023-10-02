from flask import Flask, request, jsonify
import boto3
import botocore
from decouple import config
import threading  # Import threading module
from flask_cors import CORS
import io
import time
import random
import string

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Configure AWS S3 cofiguration variables
AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
S3_BUCKET = config('S3_BUCKET')
S3_REGION = config('S3_REGION')

# Initialize S3 client
s3 = boto3.client('s3', region_name=S3_REGION, aws_access_key_id=AWS_ACCESS_KEY_ID,
                  aws_secret_access_key=AWS_SECRET_ACCESS_KEY)

# Initialize Amazon s3 Transcribe client
transcribe = boto3.client('transcribe', region_name=S3_REGION,
                          aws_access_key_id=AWS_ACCESS_KEY_ID,
                          aws_secret_access_key=AWS_SECRET_ACCESS_KEY)


def start_transcription_job(video_filename):
    try:
        # Create a transcription job
        job_name = f"transcription-{video_filename}"
        output_key = video_filename + ".vtt"
        transcribe.start_transcription_job(
            TranscriptionJobName=job_name,
            IdentifyLanguage=True,
            MediaFormat='webm',
            Media={
                'MediaFileUri': f"s3://{S3_BUCKET}/{video_filename}"
            },
            OutputBucketName=S3_BUCKET,
            OutputKey=output_key
        )
    except Exception as e:
        print(f"Error starting transcription job: {str(e)}")


@app.route('/upload', methods=['POST'])
def upload():
    
    # Get the incoming stream from the request
    blob_data = request.files["blob"]

    # Create a BytesIO object to store the stream data
    stream_data = io.BytesIO(blob_data)

    video_filename = generate_unique_filename(".mp4")


    # Upload the video to S3
    try:
        # Reset the stream data position to the beginning
        stream_data.seek(0)
        # Calculate content length
        s3.upload_fileobj(stream_data, S3_BUCKET, video_filename, ExtraArgs={
            'ContentType': "video/mp4", 'ACL': "public-read"})
    except botocore.exceptions.NoCredentialsError:
        return jsonify({"message": "AWS S3 credentials not configured"}), 401

    s3_url = generate_s3_url(S3_BUCKET, video_filename)
    transcribe_s3_url = generate_s3_url(
        S3_BUCKET, video_filename + ".vtt")

    # Start transcription job in a separate thread
    transcription_thread = threading.Thread(
        target=start_transcription_job, args=(video_filename,))
    transcription_thread.start()

    return jsonify({"video_name": video_filename, "url": s3_url, "transcribe_url": transcribe_s3_url}), 201


@app.route('/play/<video_filename>')
def play(video_filename):
    s3_url = generate_s3_url(S3_BUCKET, video_filename)
    return jsonify({"video_name": video_filename, "url": s3_url}), 200


def generate_s3_url(bucket, key):
    s3_url = f"https://{bucket}.s3.amazonaws.com/{key}"
    return s3_url


def generate_unique_filename(file_extension=".mp4"):
    # Get the current timestamp (in milliseconds)
    timestamp_ms = int(time.time() * 1000)

    # Generate a random string of characters (e.g., letters and digits)
    random_string = ''.join(random.choices(
        string.ascii_letters + string.digits, k=6))

    # Combine timestamp and random string to create a unique filename
    unique_filename = f"{timestamp_ms}_{random_string}{file_extension}"

    return unique_filename


if __name__ == '__main__':
    app.run(debug=True, port=5001)
