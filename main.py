import boto3
import ffmpeg
import os

def encode_video(input_file, output_file, video_codec, audio_codec, crf, audio_bitrate):
    try:
        stream = ffmpeg.input(input_file)
        stream = ffmpeg.output(
            stream,
            output_file,
            vcodec=video_codec,
            acodec="copy",
            crf=crf,
            **{'b:a': audio_bitrate} # controls the audio bitrate.
            # **{"q:v": 1} # controls video quality. smaller num = higher quality
        )
        ffmpeg.run(stream)
        print(f"Video converted successfully to {output_file}")
        return True
    except ffmpeg.Error as e:
        print("Error converting video.")
        print(e.stderr.decode() if e.stderr else str(e))
        return False

def scan_for_and_upload_videos(input_directory, output_directory, output_format, video_codec, audio_codec, crf, audio_bitrate, s3):
    # scan videos in directory
    for root, dirs, files in os.walk(input_directory):
        for f in files:
            input_file_path = os.path.join(root, f)

            if os.path.isfile(input_file_path):

                new_output = f[:f.index(".")] + "." + output_format
                aws_output = output_directory + new_output
                
                temp_output = f[:f.index(".")] + "_temp." + output_format
                temp_file_path = os.path.join(input_directory, temp_output)

                if encode_video(input_file_path, temp_file_path, video_codec, audio_codec, crf, audio_bitrate):
                    s3.upload_file(temp_file_path, 'hackingerror404-bucket', aws_output)
                    os.remove(temp_file_path)

input_directory = "vidsInput"
output_directory = "vidsOutput/" # NEEDS TO END IN A '/' TO WORK.
output_format = "mp4"
video_codec = "libx264"
crf = 23
audio_bitrate = '128k'

s3 = boto3.client('s3')

scan_for_and_upload_videos(input_directory, output_directory, output_format, video_codec, "dummy", crf, audio_bitrate, s3)