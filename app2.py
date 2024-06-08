import os
from flask import Flask, render_template, request, send_from_directory
from wizard_ai.components.video_to_subtitle import SubtitleGenerator, Video2SubConfig
from wizard_ai.components.summarize import Summarizer
from wizard_ai.pipeline import run_training_pipeline
import threading

from gtts import gTTS
from werkzeug.utils import secure_filename

from wizard_ai.components.video_downloader import VideoDownloader

app = Flask(__name__)
app.config['upload_dir'] = os.path.join('uploads/')
os.makedirs(app.config['upload_dir'], exist_ok=True)

print("Loading Summarizer model")
summarizer = Summarizer()
summarizer.load_model()


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/transcribe', methods=['POST'])
def upload_file():
    if request.method == 'POST':
        subtitle_generator = SubtitleGenerator(config=Video2SubConfig())
        task = 'transcribe'

        # Handling file upload
        if 'video_file' in request.files:
            video_file = request.files['video_file']
            if video_file.filename == '':
                return "No selected file", 400

            filename = secure_filename(video_file.filename)
            video_path = os.path.join(app.config['upload_dir'], filename)
            video_file.save(video_path)

            if len(request.form.getlist('translate-btn')) > 0:
                task = 'translate'
                print("Translate task is selected:", task)

            subtitle = subtitle_generator.get_subtitles(
                video_paths=[video_path], 
                model_path='tiny', 
                task=task, 
                verbose=False
            )

        # Handling video link
        elif 'link-input' in request.form:
            video_link = request.form['link-input']
            downloader = VideoDownloader(url=video_link, save_path=app.config['upload_dir'])
            video_path = downloader.download()

            option = request.form.get('options')
            if option == 'translate':
                task = 'translate'
                print("Translate task is selected:", task)

            subtitle = subtitle_generator.get_subtitles(
                video_paths=[video_path], 
                model_path='tiny', 
                task=task, 
                verbose=False
            )

        else:
            return "No video file or link provided", 400

        transcript_text = subtitle[1]['text']
        summary_text = summarizer.summarize_text(transcript_text)
        tts = gTTS(summary_text, tld="co.uk")
        audio_path = os.path.join(app.config['upload_dir'], 'summary.mp3')
        tts.save(audio_path)

        return render_template('index.html', transcript=transcript_text, summary=summary_text, audio_path=audio_path)
    
    
@app.route('/audio/<path:filename>')
def serve_audio(filename):
    return send_from_directory(app.config['upload_dir'], filename, mimetype='audio/mpeg')


@app.route('/train', methods=['GET', 'POST'])
def start_train():
    def run_training():
        run_training_pipeline()
    train_thread = threading.Thread(target=run_training)
    train_thread.start()
    return "Training has started"


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)