import boto3
import ffmpeg
import os
import flet as ft

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
    print(f"Video Uploads Complete!")

def main(page: ft.Page):
    def button_clicked(e: ft.Event[ft.Button]):
        # button.data += 1
        message.value = f"Script Activated"
        scan_for_and_upload_videos(input_directory, output_directory, output_format, video_codec, "dummy", crf, audio_bitrate, s3)
        
    page.title = "Encode an' Cloud"
    page.window_width = 500
    page.window_height = 500
    page.resizable = True
    page.padding = 20
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    input_directory = "vidsInput"
    output_directory = "vidsOutput/" # NEEDS TO END IN A '/' TO WORK.
    output_format = "mp4"
    video_codec = "libx264"
    crf = 23
    audio_bitrate = '128k'

    s3 = boto3.client('s3')

    page.add(
        ft.SafeArea(
            content=ft.Column(
                controls=[
                    button := ft.Button(
                        content="click me to run the script :D",
                        data=0,
                        on_click=button_clicked
                    ),
                    message := ft.Text("Script Began."),
                ]
            )
        ),
    )

ft.run(main)