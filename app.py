from flask import Flask, request, render_template, jsonify
import PyPDF2
import io
import os
import tabula  # For tables
import pdfplumber  # Better text + table extraction
import fitz  # PyMuPDF for images/graphs
from PIL import Image
import base64
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = 'uploads'

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def extract_content(file_stream):
    text = []
    tables = []
    images = []
    
    # Extract tables using tabula
    pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], 'temp.pdf')
    file_stream.save(pdf_path)
    try:
        tables = tabula.read_pdf(pdf_path, pages='all')
        tables = [table.to_html() for table in tables if not table.empty]
    except Exception as e:
        print(f"Table extraction error: {e}")
    
    # Extract text and detect tables using pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text.append(page.extract_text() or '')
            
    # Extract images using PyMuPDF
    doc = fitz.open(pdf_path)
    for page_num in range(len(doc)):
        page = doc[page_num]
        image_list = page.get_images()
        
        for img_index, img in enumerate(image_list):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            
            # Convert to base64 for display
            image_b64 = base64.b64encode(image_bytes).decode()
            images.append(f"data:image/jpeg;base64,{image_b64}")
    
    doc.close()
    os.remove(pdf_path)  # Clean up temp file
    
    return {
        'text': '\n'.join(text),
        'tables': tables,
        'images': images
    }

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/extract', methods=['POST'])
def extract():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.endswith('.pdf'):
        return jsonify({'error': 'Please upload a PDF file'}), 400

    try:
        content = extract_content(file)
        return jsonify(content)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)