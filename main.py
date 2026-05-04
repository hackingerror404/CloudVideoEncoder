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
    except ffmpeg.Error as e:
        print("Error converting video.")
        print(e.stderr.decode() if e.stderr else str(e))

def encoder_func(input_directory, output_directory, output_format, video_codec, audio_codec, crf, audio_bitrate):
    # scan videos in directory
    for root, dirs, files in os.walk(input_directory):
        for f in files:
            input_file_path = os.path.join(root, f)

            new_output = f[:f.index(".")] + "." + output_format
            output_file_path = os.path.join(output_directory, new_output)

            if os.path.isfile(input_file_path):
                encode_video(input_file_path, output_file_path, video_codec, audio_codec, crf, audio_bitrate)

input_directory = "vidsInput"
output_directory = "vidsOutput"
output_format = "mp4"
video_codec = "libx264"
crf = 23
audio_bitrate = '128k'

encoder_func(input_directory, output_directory, output_format, video_codec, "dummy", crf, audio_bitrate)