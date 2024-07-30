from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import pandas as pd
import io

app = Flask(__name__)

# Permitir CORS para qualquer origem durante o desenvolvimento
CORS(app, resources={r"/api/*": {"origins": "*"}})

def get_page(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.text

def check_url_status(url):
    try:
        response = requests.head(url, allow_redirects=True, timeout=10)
        response.raise_for_status()
        return response.status_code
    except requests.RequestException:
        return None

def process_links(html, base_url):
    soup = BeautifulSoup(html, 'html.parser')
    records = []
    divs = soup.find_all('div', class_='paginas-internas')
    
    for div in divs:
        links = div.find_all('a')
        for link in links:
            href = link.get('href', '')
            if href.lower().endswith(('.pdf', '.png', '.jpeg', '.jpg')):
                file_url = href if href.startswith('http') else base_url + href
                status_code = check_url_status(file_url)
                
                if status_code == 404:
                    records.append({'URL': file_url, 'Status': 'Erro 404'})
                elif status_code == 200:
                    records.append({'URL': file_url, 'Status': 'OK'})
                else:
                    records.append({'URL': file_url, 'Status': f'Status inesperado: {status_code}'})
    return records

@app.route('/')
def index():
    return "API para verificação de URLs está funcionando."

@app.route('/check-urls', methods=['POST'])
def check_urls():
    data = request.json
    base_url = data.get('base_url', '')
    
    if not base_url:
        return jsonify({'error': 'Base URL não fornecida'}), 400
    
    try:
        html_content = get_page(base_url)
        records = process_links(html_content, base_url)
        return jsonify(records)
    except requests.RequestException as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download-excel', methods=['POST'])
def download_excel():
    data = request.json
    records = data.get('records', [])
    
    if not records:
        return jsonify({'error': 'Nenhum dado disponível para exportar'}), 400

    df = pd.DataFrame(records)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='URLs')
    output.seek(0)
    
    return send_file(output, attachment_filename='url_status.xlsx', as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

if __name__ == '__main__':
    app.run(port=5000)
