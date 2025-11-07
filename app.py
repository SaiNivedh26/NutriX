from flask import Flask, render_template, request, jsonify, send_from_directory, Response, stream_with_context, send_file
import google.generativeai as gemini
from PIL import Image
import base64
import re
import os
import json
import uuid
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfgen import canvas
from io import BytesIO
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['PDF_FOLDER'] = 'pdf_reports'

# Create directories if they don't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['PDF_FOLDER'], exist_ok=True)


# Configure Gemini API
gemini.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# Custom loading phrases
LOADING_PHRASES = [
    "🔍 Analyzing your delicious meal...",
    "🥗 Calculating nutritional insights...", 
    "📊 Generating personalized nutrition report...",
    "🍽️ Consulting our expert nutrition database...",
    "💡 Uncovering hidden nutritional secrets..."
]

def get_gem_response_stream(input_prompt, image):
    """Stream response from Gemini API"""
    model = gemini.GenerativeModel('gemini-2.0-flash')
    response = model.generate_content([input_prompt, image[0]], stream=True)
    
    for chunk in response:
        if chunk.text:
            yield chunk.text

def clean_response_text(text):
    """Remove markdown characters and format text properly"""
    # Remove markdown headers (#, ##, ###) but preserve the text
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    # Remove markdown bold/italic (*, **, _) but keep the content
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*\n]+)\*', r'\1', text)  # Don't match across newlines
    text = re.sub(r'__([^_]+)__', r'\1', text)
    text = re.sub(r'_([^_\n]+)_', r'\1', text)  # Don't match across newlines
    # Remove standalone asterisks and hashes (but not in context)
    text = re.sub(r'^\s*[*#]+\s*$', '', text, flags=re.MULTILINE)
    # Remove markdown list markers at line start but keep content
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
    # Remove numbered list markers but keep content
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    # Remove markdown links but keep text
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # Remove horizontal rules (lines with only dashes/equals)
    text = re.sub(r'^[-=]{3,}$', '', text, flags=re.MULTILINE)
    # Clean up multiple spaces (but preserve single spaces)
    text = re.sub(r' {2,}', ' ', text)
    # Clean up multiple newlines (keep max 2)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def highlight_numbers(text):
    """Wrap numbers in span tags for highlighting"""
    # Match numbers (integers and decimals) including percentages
    pattern = r'(\d+\.?\d*%?)'
    return re.sub(pattern, r'<span class="number-highlight">\1</span>', text)

def input_image_setup(uploaded_file):
    if uploaded_file is not None:
        bytes_data = uploaded_file.read()
        image_parts = [
            {
                "mime_type": uploaded_file.content_type,
                "data": bytes_data
            }
        ]
        return image_parts
    else:
        raise FileNotFoundError("No file uploaded")

def parse_macronutrients(response_text):
    """Extract macronutrient percentages from AI response"""
    # Default values if parsing fails
    carbs = None
    proteins = None
    fats = None
    
    # Try to find percentages in the response
    # Look for patterns like "carbohydrates: 45%", "carbs: 45%", "45% carbs", etc.
    patterns = {
        'carbs': [
            r'carbohydrates?[:\s-]+(\d+(?:\.\d+)?)\s*%',
            r'(\d+(?:\.\d+)?)\s*%[:\s-]+(?:of\s+)?carbohydrates?',
            r'carbs?[:\s-]+(\d+(?:\.\d+)?)\s*%',
            r'(\d+(?:\.\d+)?)\s*%[:\s-]+(?:of\s+)?carbs?',
            r'carbohydrate[:\s-]+(\d+(?:\.\d+)?)\s*percent',
            r'(\d+(?:\.\d+)?)\s*percent[:\s-]+carbohydrate',
            # More flexible patterns
            r'carbohydrates?\s*[:\-]\s*(\d+(?:\.\d+)?)\s*%',
            r'(\d+(?:\.\d+)?)\s*%\s*carbohydrates?',
            r'carbohydrates?\s*(\d+(?:\.\d+)?)\s*%'
        ],
        'proteins': [
            r'proteins?[:\s-]+(\d+(?:\.\d+)?)\s*%',
            r'(\d+(?:\.\d+)?)\s*%[:\s-]+(?:of\s+)?proteins?',
            r'protein[:\s-]+(\d+(?:\.\d+)?)\s*%',
            r'(\d+(?:\.\d+)?)\s*%[:\s-]+(?:of\s+)?protein',
            r'protein[:\s-]+(\d+(?:\.\d+)?)\s*percent',
            r'(\d+(?:\.\d+)?)\s*percent[:\s-]+protein',
            # More flexible patterns
            r'proteins?\s*[:\-]\s*(\d+(?:\.\d+)?)\s*%',
            r'(\d+(?:\.\d+)?)\s*%\s*proteins?',
            r'proteins?\s*(\d+(?:\.\d+)?)\s*%'
        ],
        'fats': [
            r'fats?[:\s-]+(\d+(?:\.\d+)?)\s*%',
            r'(\d+(?:\.\d+)?)\s*%[:\s-]+(?:of\s+)?fats?',
            r'fat[:\s-]+(\d+(?:\.\d+)?)\s*%',
            r'(\d+(?:\.\d+)?)\s*%[:\s-]+(?:of\s+)?fat',
            r'fat[:\s-]+(\d+(?:\.\d+)?)\s*percent',
            r'(\d+(?:\.\d+)?)\s*percent[:\s-]+fat',
            # More flexible patterns
            r'fats?\s*[:\-]\s*(\d+(?:\.\d+)?)\s*%',
            r'(\d+(?:\.\d+)?)\s*%\s*fats?',
            r'fats?\s*(\d+(?:\.\d+)?)\s*%'
        ]
    }
    
    response_lower = response_text.lower()
    
    # Try to find all three macronutrients
    for nutrient, pattern_list in patterns.items():
        for pattern in pattern_list:
            match = re.search(pattern, response_lower)
            if match:
                try:
                    value = float(match.group(1))
                    # Only accept reasonable values (0-100)
                    if 0 <= value <= 100:
                        if nutrient == 'carbs' and carbs is None:
                            carbs = value
                        elif nutrient == 'proteins' and proteins is None:
                            proteins = value
                        elif nutrient == 'fats' and fats is None:
                            fats = value
                        if carbs is not None and proteins is not None and fats is not None:
                            break
                except (ValueError, IndexError):
                    continue
        if carbs is not None and proteins is not None and fats is not None:
            break
    
    # If we found all three, use them
    if carbs is not None and proteins is not None and fats is not None:
        # Normalize to ensure they sum to 100
        total = carbs + proteins + fats
        if total > 0:
            carbs = (carbs / total) * 100
            proteins = (proteins / total) * 100
            fats = (fats / total) * 100
    else:
        # Use defaults if parsing failed
        # Try to use partial data if available
        if carbs is None:
            carbs = 40
        if proteins is None:
            proteins = 30
        if fats is None:
            fats = 30
        # Normalize defaults
        total = carbs + proteins + fats
        if total > 0:
            carbs = (carbs / total) * 100
            proteins = (proteins / total) * 100
            fats = (fats / total) * 100
    
    result = {
        'carbs': round(carbs, 1),
        'proteins': round(proteins, 1),
        'fats': round(fats, 1)
    }
    
    # Debug logging (can be removed in production)
    print(f"Parsed macros: {result}")
    
    return result

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/image/<filename>')
def serve_image(filename):
    """Serve images from the root directory"""
    return send_from_directory('.', filename)

def generate_pdf_report(chart_image_path, nutrition_text, report_uuid):
    """Generate PDF report with chart and nutrition text"""
    pdf_path = os.path.join(app.config['PDF_FOLDER'], f'{report_uuid}.pdf')
    
    # Create PDF document
    doc = SimpleDocTemplate(pdf_path, pagesize=A4,
                          rightMargin=72, leftMargin=72,
                          topMargin=72, bottomMargin=18)
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor='#27AE60',
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=18,
        textColor='#2C3E50',
        spaceAfter=12,
        spaceBefore=12
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        textColor='#34495E',
        spaceAfter=12,
        alignment=TA_LEFT,
        leading=16
    )
    
    # Title
    elements.append(Paragraph("🍎 NutriX - Nutrition Report", title_style))
    elements.append(Spacer(1, 0.2*inch))
    elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", styles['Normal']))
    elements.append(Spacer(1, 0.3*inch))
    
    # Chart Image
    if os.path.exists(chart_image_path):
        chart_img = RLImage(chart_image_path, width=5*inch, height=3*inch)
        elements.append(Paragraph("Macronutrient Breakdown", heading_style))
        elements.append(chart_img)
        elements.append(Spacer(1, 0.3*inch))
    
    # Nutrition Text
    elements.append(Paragraph("Nutrition Insights", heading_style))
    
    # Split text into paragraphs and add them
    paragraphs = nutrition_text.split('\n\n')
    for para in paragraphs:
        if para.strip():
            # Clean HTML tags if any
            para_clean = re.sub(r'<[^>]+>', '', para)
            elements.append(Paragraph(para_clean, normal_style))
            elements.append(Spacer(1, 0.1*inch))
    
    # Footer
    elements.append(Spacer(1, 0.3*inch))
    elements.append(Paragraph("Designed and Developed by Sai Nikedh from 10-B", 
                             ParagraphStyle('Footer', parent=styles['Normal'], 
                                          fontSize=9, textColor='#7F8C8D', 
                                          alignment=TA_CENTER)))
    
    # Build PDF
    doc.build(elements)
    return pdf_path

@app.route('/download', methods=['POST'])
def download_report():
    """Generate PDF and return it for download"""
    try:
        data = request.json
        chart_image_base64 = data.get('chart_image')
        nutrition_text = data.get('nutrition_text')
        
        if not chart_image_base64 or not nutrition_text:
            return jsonify({'error': 'Missing required data'}), 400
        
        # Generate unique UUID
        report_uuid = str(uuid.uuid4())
        
        # Save chart image temporarily
        chart_image_path = os.path.join(app.config['PDF_FOLDER'], f'chart_{report_uuid}.png')
        # Handle base64 data (remove data:image/png;base64, prefix if present)
        chart_image_data_str = chart_image_base64
        if ',' in chart_image_data_str:
            chart_image_data_str = chart_image_data_str.split(',')[1]
        chart_image_data = base64.b64decode(chart_image_data_str)
        with open(chart_image_path, 'wb') as f:
            f.write(chart_image_data)
        
        # Clean nutrition text (remove HTML tags)
        clean_text = re.sub(r'<[^>]+>', '', nutrition_text)
        clean_text = clean_text.replace('&nbsp;', ' ')
        clean_text = clean_text.replace('&amp;', '&')
        
        # Generate PDF
        pdf_path = generate_pdf_report(chart_image_path, clean_text, report_uuid)
        
        # Clean up temporary chart image after PDF is generated
        try:
            if os.path.exists(chart_image_path):
                os.remove(chart_image_path)
        except Exception as e:
            print(f"Warning: Could not remove temporary chart image: {e}")
        
        # Return PDF file for download
        return send_file(pdf_path, as_attachment=True, download_name=f'NutriX_Report_{report_uuid}.pdf')
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Check file type
        if not file.filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            return jsonify({'error': 'Invalid file type. Please upload JPG, JPEG, or PNG'}), 400
        
        # Read file
        file.seek(0)
        image_data = input_image_setup(file)

        # Nutrition Analysis Prompt
        input_prompt = """
You are an expert nutritionist and providing dietary information. You need to see the food item from the image
and calculate the total calories, also provide details of every food item with calorie intake.

IMPORTANT: Write your response in plain text format. Do NOT use markdown formatting like asterisks (*), hash symbols (#), or any special markdown characters. Use simple text only.

    As a professional nutritionist, analyze this food image and provide:
- Detailed calorie breakdown for each item
- Nutritional value of each item
- Macro and micronutrient percentages

CRITICAL: You MUST include the macronutrient breakdown in this EXACT format somewhere in your response:
Carbohydrates: XX%, Proteins: YY%, Fats: ZZ%
(where XX, YY, ZZ are the actual percentages that should sum to approximately 100%)

For example: "Carbohydrates: 45%, Proteins: 30%, Fats: 25%" or "Carbs: 50%, Proteins: 25%, Fats: 25%"

- Health assessment
- Dietary recommendations

Finally mention whether the food is healthy or not healthy.
Mention the percentage split of ratio of carbohydrates, fats, fibers, sugars and other things required in diet.

Analyze this food image and provide details about its calorie content and dietary recommendations.

        """
        
        # Convert image to base64 for display
        file.seek(0)
        image_bytes = base64.b64encode(file.read()).decode("utf-8")
        image_base64 = f"data:{file.content_type};base64,{image_bytes}"
        
        # Return streaming response
        def generate():
            full_response = ""
            try:
                for chunk in get_gem_response_stream(input_prompt, image_data):
                    full_response += chunk
                    # Clean and format the chunk
                    cleaned_chunk = clean_response_text(chunk)
                    if cleaned_chunk:
                        # Send chunk as JSON with proper escaping
                        try:
                            chunk_json = json.dumps({'chunk': cleaned_chunk, 'type': 'chunk'}, ensure_ascii=False)
                            yield f"data: {chunk_json}\n\n"
                        except (UnicodeEncodeError, ValueError) as e:
                            # Fallback: escape the chunk manually if JSON encoding fails
                            cleaned_chunk_escaped = cleaned_chunk.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
                            yield f'data: {{"chunk": "{cleaned_chunk_escaped}", "type": "chunk"}}\n\n'
                
                # After streaming is complete, parse macros and send final data
                macros = parse_macronutrients(full_response)
                try:
                    complete_json = json.dumps({'type': 'complete', 'macros': macros, 'image': image_base64}, ensure_ascii=False)
                    yield f"data: {complete_json}\n\n"
                except (UnicodeEncodeError, ValueError) as e:
                    # If image is too large, send without image
                    complete_json = json.dumps({'type': 'complete', 'macros': macros}, ensure_ascii=False)
                    yield f"data: {complete_json}\n\n"
            except Exception as e:
                error_json = json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)
                yield f"data: {error_json}\n\n"
        
        return Response(stream_with_context(generate()), mimetype='text/event-stream')
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
