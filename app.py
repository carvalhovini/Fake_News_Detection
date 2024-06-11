from flask import Flask, render_template, request
from PIL import Image, ExifTags
import cv2
import os
import requests

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads/'

def detect_fake_news_image(image_path):
    image = Image.open(image_path)
    width, height = image.size
    score = 100

    # Verificar metadados EXIF
    exif_data = image._getexif()
    if not exif_data:
        score -= 50  # Deduzir pontos por falta de metadados EXIF
    else:
        for tag, value in exif_data.items():
            if tag in ExifTags.TAGS:
                if ExifTags.TAGS[tag] == 'Software' and 'Photoshop' in value:
                    score -= 50  # Deduzir pontos por edição com Photoshop

    # Verificar resolução da imagem
    if width < 500 or height < 500:
        score -= 25  # Deduzir pontos por baixa resolução

    # Adicione a detecção de manipulações
    image_cv = cv2.imread(image_path)
    gray = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    if laplacian_var < 100:
        score -= 25  # Deduzir pontos por falta de detalhes

    return f"Imagem analisada. Veracidade: {max(score, 0)}%."

def detect_fake_news_video(video_path):
    video = cv2.VideoCapture(video_path)
    frame_count = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_rate = int(video.get(cv2.CAP_PROP_FPS))
    duration = frame_count / frame_rate
    score = 100

    if frame_count < 100:
        score -= 50  # Deduzir pontos por duração curta

    if frame_rate < 24:
        score -= 25  # Deduzir pontos por baixa taxa de quadros

    # Adicione a análise de frames
    success, frame = video.read()
    while success:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        if laplacian_var < 100:
            score -= 1  # Deduzir pontos por cada frame com falta de detalhes
        success, frame = video.read()

    return f"Vídeo analisado. Veracidade: {max(score, 0)}%."

def verify_text_online(text):
    api_url = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer YOUR_API_KEY'
    }
    params = {
        'query': text
    }
    response = requests.get(api_url, headers=headers, params=params)
    result = response.json()
    
    if result.get('claims'):
        claim = result['claims'][0]
        return f"Texto analisado: {claim['text']} - Veracidade: {claim['claimReview'][0]['textualRating']}"
    else:
        return "Nenhuma verificação encontrada para o texto fornecido."

@app.route('/', methods=['GET', 'POST'])
def index():
    result = ""
    if request.method == 'POST':
        if 'file' in request.files and request.files['file'].filename != '':
            file = request.files['file']
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)
            if file.content_type.startswith('image'):
                result = detect_fake_news_image(file_path)
            elif file.content_type.startswith('video'):
                result = detect_fake_news_video(file_path)
            else:
                result = "Formato de arquivo não suportado."
        elif 'text' in request.form and request.form['text'] != '':
            text = request.form['text']
            result = verify_text_online(text)
        else:
            result = "Nenhum conteúdo fornecido."

    return render_template('index.html', result=result)

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)
