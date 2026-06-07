# Cloud Video Encoder

This is a Linux application built within Python and the [Flet Framework](https://flet.dev/) that's designed to scan a directory you provide for video files, encode them to a format and compression rate you specify, and upload them to an Amazon S3 bucket. The app uses Flet's toolkit to create a simple, easy-to-read GUI that automates the manual encoding and uploading process behind ffmpeg and boto3's scripting tools. 

AWS Secret Keys will be necessary to use the app and provided in the settings. (These will only be saved locally on your machine, and can be edited/deleted at will). 

<p align="center">
  <img width="1091" height="826" alt="Screenshot_20260603_154741" src="https://github.com/user-attachments/assets/141f66b0-1516-445f-85a9-e7d138c61e9a" style="width:75%; height:75%;"/>
</p>

<br></br>

### TO INSTALL:
The app is packed in a .tar.gz file, please use the release linked [here](https://github.com/hackingerror404/CloudVideoEncoder/releases/tag/v1.0.1).

### Dependencies/Technologies Used:
- Python 3.14
- [Flet App Framework](https://flet.dev/)
- ffmpeg, [ffmpeg-python](https://github.com/kkroening/ffmpeg-python)
- [Amazon Boto3](https://docs.aws.amazon.com/boto3/latest/)

### Demonstration Of the App in Use!
Link [here](https://youtu.be/u0LHTt5oqNo).
