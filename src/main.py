import boto3
import ffmpeg
import flet as ft
import os
import queue
import subprocess
import threading

def run_ffmpeg_encode(input_path, output_path, video_codec, crf):
    cmd = [
        "ffmpeg",
        "-y",
        "-i", input_path,
        "-c:v", video_codec,
        "-crf", str(crf),
        "-c:a", "copy",
        output_path
    ]
    # WHYYYYYY do i have to use a subprocess whyyyyy
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc.returncode == 0, proc.stdout, proc.stderr

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
    ui_thread_queue = queue.Queue()

    page.title = "Encode & Upload"
    page.window_width = 500
    page.window_height = 500
    page.resizable = True
    page.padding = 16
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

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
    progress_text = ft.Text("Tasks Remaining: 0 / 0", size=12)
    progress_ring = ft.ProgressRing()

    video_codec = "libx264"
    s3 = boto3.client('s3')

    def update_ui(status_text=None, task_counter=None, total_tasks=None):
        if status_text is not None:
            status_label.value = status_text
        if task_counter is not None and total_tasks is not None:
            progress_bar.value = (task_counter / total_tasks) if total_tasks > 0 else 0.0
            progress_text.value = f"Tasks Remaining: {task_counter} / {total_tasks}"
        page.update()

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
            encode_success, _, _ = run_ffmpeg_encode(vid_path, temp_output, video_codec, crf)
            task_counter += 1
            update_ui(task_counter=task_counter, total_tasks=total_tasks)

            if not encode_success:
                update_ui(status_text=f"Encoding failed: {filename_base} — skipping file")
                continue

            update_ui(task_counter=task_counter, total_tasks=total_tasks)

            # UPLOAD STEP!
            update_ui(status_text=f"Uploading {filename_base} ({vid_counter}/{num})")
            try:
                s3.upload_file(temp_output, "hackingerror404-bucket", aws_output)
                update_ui(status_text=f"Uploaded {filename_base}")
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

    page.add(
        ft.Column([
            input_directory,
            output_directory,
            output_format,
            ft.Row([crf_slider, ft.Container(width=4), crf_slider_text]),
            ft.Row([start_btn, ft.Container(width=12), progress_text]),
            ft.Container(height=8),
            ft.Row([progress_bar, ft.Container(width=4), progress_ring]),
            ft.Container(height=12),
            status_label
        ])
    )

ft.run(main)