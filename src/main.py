import boto3
import ffmpeg
import flet as ft
import os
import subprocess
import threading
import time

def run_ffmpeg_encode(input_path, output_path, video_codec, crf):
    try:
        stream = ffmpeg.input(input_path)
        stream = ffmpeg.output(
            stream,
            output_path,
            vcodec=video_codec,
            acodec="copy",
            crf=crf,
            threads=4
            # **{'b:a': audio_bitrate} # controls the audio bitrate.
            # **{"q:v": 1} # controls video quality. smaller num = higher quality
        )
        ffmpeg.run(stream)
        print(f"Video converted successfully to {output_path}")
        return True
    except ffmpeg.Error as e:
        print("Error converting video.")
        print(e.stderr.decode() if e.stderr else str(e))
        return False

def scan_videos(input_directory, allowed_exts=None):
    if allowed_exts is None:
        allowed_exts = {".mp4", ".mov", ".mkv", ".avi", ".gif"}
    videos = []
    for root, _, files in os.walk(input_directory):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in allowed_exts:
                videos.append(os.path.join(root, f))
    return sorted(videos)

def main(page: ft.Page):
    page.title = "Encode & Upload"
    page.window_width = 500
    page.window_height = 500
    page.resizable = True
    page.padding = 16
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER

    input_directory = ft.TextField(label="Local Video Path")
    output_directory = ft.TextField(label="Cloud Output Path")
    output_format = ft.Dropdown(
        label="Output Video Format",
        editable=True,
        options=[
            ft.DropdownOption(key="avi", text=".avi"),
            ft.DropdownOption(key="gif", text=".gif"),
            ft.DropdownOption(key="mkv", text=".mkv"),
            ft.DropdownOption(key="mov", text=".mov"),
            ft.DropdownOption(key="mp4", text=".mp4")
        ]
    )
    crf_slider = ft.Slider(min=17, max=47, divisions=30, label="crf = {value}")
    crf_slider.value = 23
    crf_slider_text = ft.Text("Compression Rate; higher value = more compressed.")

    # log_field = ft.TextField(label="Console Output", multiline=True, read_only=True, expand=True)
    start_btn = ft.Button(content="Start", width=160)
    status_label = ft.Text("", size=14)
    progress_bar = ft.ProgressBar(width=600, height=12, bgcolor=ft.Colors.GREY_200)
    progress_text = ft.Text("Task Tracker: 0 / 0", size=12)
    progress_ring = ft.ProgressRing()

    header = ft.Row(
        controls=[
            ft.Icon(ft.Icons.CLOUD_SYNC, size=32, color=ft.Colors.BLUE_400),
            ft.Text("Media Encoder & Uploader", size=24, weight=ft.FontWeight.BOLD),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
    )
    subtitle = ft.Text("Batch convert and push video files to S3", color=ft.Colors.GREY_400, size=14)

    # 2. Inputs
    input_directory = ft.TextField(
        label="Local Video Path", 
        icon=ft.Icons.FOLDER_OPEN,
        border_color=ft.Colors.BLUE_GREY_700
    )
    output_directory = ft.TextField(
        label="Cloud Output Prefix", 
        icon=ft.Icons.CLOUD_UPLOAD,
        border_color=ft.Colors.BLUE_GREY_700
    )
    output_format = ft.Dropdown(
        label="Output Video Format",
        leading_icon=ft.Icons.MOVIE,
        border_color=ft.Colors.BLUE_GREY_700,
        options=[
            ft.DropdownOption(key="avi", text=".avi"),
            ft.DropdownOption(key="gif", text=".gif"),
            ft.DropdownOption(key="mkv", text=".mkv"),
            ft.DropdownOption(key="mov", text=".mov"),
            ft.DropdownOption(key="mp4", text=".mp4")
        ]
    )

    # 3. Sliders & Settings
    crf_slider = ft.Slider(min=17, max=47, divisions=30, label="CRF: {value}", expand=True)
    crf_slider.value = 23
    slider_row = ft.Column([
        ft.Row([ft.Text("Compression Rate (CRF)", weight=ft.FontWeight.W_500), ft.Text("Higher = smaller file, lower quality", size=12, color=ft.Colors.GREY_500)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        crf_slider
    ], spacing=0)

    # 4. Status & Progress
    status_label = ft.Text("Ready", size=14, color=ft.Colors.BLUE_400, weight=ft.FontWeight.W_500)
    progress_bar = ft.ProgressBar(height=8, bgcolor=ft.Colors.BLUE_GREY_900, color=ft.Colors.BLUE_400, visible=False)
    progress_text = ft.Text("0 / 0 Tasks", size=12, color=ft.Colors.GREY_400)
    progress_ring = ft.ProgressRing(width=20, height=20, stroke_width=2, visible=False)
    
    start_btn = ft.ElevatedButton(
        content=ft.Row([ft.Icon(ft.Icons.PLAY_ARROW), ft.Text("Start Processing")], alignment=ft.MainAxisAlignment.CENTER),
        width=200,
        height=45,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8), bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE)
    )

    video_codec = "libx264"
    s3 = boto3.client('s3')

    def update_ui(status_text=None, task_counter=None, total_tasks=None):
        async def _update():
            if status_text is not None:
                status_label.value = status_text
            if task_counter is not None and total_tasks is not None:
                progress_bar.value = (task_counter / total_tasks) if total_tasks > 0 else 0.0
                progress_text.value = f"Task Tracker: {task_counter} / {total_tasks}"
            page.update()
        
        page.run_task(_update)

    def encode_and_upload(input_path: str, output_path: str, output_format: str, video_codec: str, crf: str):
        video_list = scan_videos(input_path)
        num = len(video_list)
        if num == 0:
            update_ui(status_text="No videos found.")
            start_btn.disabled = False
            page.update() # TODO: consider swapping above ^ order so update() isn't called twice in a row?
            return

        total_tasks = num * 2
        task_counter = 0
        update_ui(status_text="Starting...", task_counter=task_counter, total_tasks=total_tasks)

        for vid_counter, vid_path in enumerate(video_list, start=1):
            filename_base = os.path.splitext(os.path.basename(vid_path))[0]
            temp_output = os.path.join(input_path, f"{filename_base}_temp." + output_format)
            aws_output = (output_path.rstrip("/") + "/" + filename_base + "." + output_format).lstrip("/")

            # ENCODE STEP!
            update_ui(status_text=f"Encoding {filename_base} ({vid_counter}/{num})")
            time.sleep(0.1)
            encode_success = run_ffmpeg_encode(vid_path, temp_output, video_codec, crf)
            task_counter += 1
            update_ui(task_counter=task_counter, total_tasks=total_tasks)

            if not encode_success:
                update_ui(status_text=f"Encoding failed: {filename_base} — skipping file")
                continue

            update_ui(task_counter=task_counter, total_tasks=total_tasks)
            time.sleep(0.1)

            # UPLOAD STEP!
            update_ui(status_text=f"Uploading {filename_base} ({vid_counter}/{num})")
            time.sleep(0.1) # Give the UI a microsecond to draw the "Uploading" text

            try:
                s3.upload_file(temp_output, "hackingerror404-bucket", aws_output)
                update_ui(status_text=f"Uploaded {filename_base}")
                time.sleep(0.1) # Ensure the "Uploaded" message actually renders
            except Exception as e:
                    update_ui(status_text=f"Upload failed: {filename_base} - skipping upload")            
            finally:
                try:
                    os.remove(temp_output)
                except Exception:
                    pass

            task_counter += 1
            update_ui(task_counter=task_counter, total_tasks=total_tasks)

        update_ui(status_text="All videos complete.")
        print("ALL VIDEOS COMPLETE!")
        start_btn.disabled = False
        progress_ring.visible = False
        page.update()

    def on_start(e):
        if not input_directory.value:
            update_ui(status_text="Please provide a local video path.")
            return
        if not output_directory.value:
            update_ui(status_text="Please provide a cloud output prefix.")
            return
        if not output_format.value:
            update_ui(status_text="Please provide an output video format.")
            return

        start_btn.disabled = True
        progress_bar.visible = True
        progress_ring.visible = True
        update_ui(status_text="Preparing...", task_counter=0, total_tasks=1)

        threading.Thread(target=encode_and_upload, args=(input_directory.value, output_directory.value, output_format.value, video_codec, crf_slider.value), daemon=True).start()

    start_btn.on_click = on_start
    progress_bar.value = 0.0    
    progress_bar.visible = False
    progress_ring.visible = False

    main_card = ft.Card(
        elevation=10,
        content=ft.Container(
            width=550,
            padding=40,
            content=ft.Column(
                controls=[
                    header,
                    ft.Container(content=subtitle, alignment=ft.Alignment.CENTER, padding=ft.Padding.only(bottom=20)),
                    
                    # Form Section
                    input_directory,
                    output_directory,
                    output_format,
                    ft.Container(height=10),
                    slider_row,
                    
                    ft.Divider(height=40, color=ft.Colors.BLUE_GREY_800),
                    
                    # Progress Section
                    ft.Row([status_label, progress_ring], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    progress_bar,
                    ft.Container(content=progress_text, alignment=ft.Alignment.CENTER_RIGHT),
                    
                    ft.Container(height=10),
                    
                    # Action Section
                    ft.Row([start_btn], alignment=ft.MainAxisAlignment.CENTER)
                ],
                spacing=10
            )
        )
    )

    page.add(main_card)

ft.run(main)