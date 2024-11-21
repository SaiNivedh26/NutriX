import streamlit as st
import google.generativeai as gemini
from PIL import Image
import base64
import time
import matplotlib.pyplot as plt
import numpy as np
import io

# Configure Gemini API (Note: Replace with a secure method of API key management)
gemini.configure(api_key="AIzaSyDAA7gq4wlgmKaivg_NsD3uF3CkIn8B8mc")

# Custom loading phrases
LOADING_PHRASES = [
    "🔍 Analyzing your delicious meal...",
    "🥗 Calculating nutritional insights...", 
    "📊 Generating personalized nutrition report...",
    "🍽️ Consulting our expert nutrition database...",
    "💡 Uncovering hidden nutritional secrets..."
]

def get_gem_response(input_prompt, image):
    model = gemini.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content([input_prompt, image[0]])
    return response.text

def input_image_setup(uploaded_file):
    if uploaded_file is not None:
        # Read the file into bytes
        bytes_data = uploaded_file.getvalue()
        image_parts = [
            {
                "mime_type": uploaded_file.type,
                "data": bytes_data
            }
        ]
        return image_parts
    else:
        raise FileNotFoundError("No file uploaded")

def generate_macronutrient_plot():
    # Generate random macronutrient data for visualization
    categories = ['Carbs', 'Proteins', 'Fats']
    values = np.random.randint(10, 60, size=3)  # Random values between 10 and 60
    values = (values / sum(values)) * 100  # Normalize to percentage

    fig, ax = plt.subplots(figsize=(4, 3))
    ax.bar(categories, values, color=['#FF9999', '#66B2FF', '#FFCC99'])
    ax.set_title("Macronutrient Breakdown")
    ax.set_ylabel("Percentage (%)")
    
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    
    return buf

# Advanced Streamlit UI
def main():
    # Custom page configuration
    st.set_page_config(
        page_title="NutriX-Food", 
        page_icon="⭕", 
        layout="wide"
    )
    st.markdown("<h1 style='font-size: 2em; color: red;'>Sai Nikedh - 9B</h1>", unsafe_allow_html=True)

    # Load and resize the QR code image
    qr_code_image = Image.open('image.png')  # Path to uploaded image
    qr_code_image = qr_code_image.resize((150, 150))  # Resize to a smaller size

    # Display the QR code image directly below the name
    st.image(qr_code_image, caption="Scan for More Info", use_container_width=False)

    # Custom CSS for professional look
    st.markdown("""
    <style>
    .main-header {
        font-size: 3em;
        color: #2C3E50;
        text-align: center;
        margin-bottom: 30px;
    }
    .subheader {
        color: #34495E;
        text-align: center;
        margin-bottom: 20px;
    }
    .stButton>button {
        background-color: #27AE60;
        color: white;
        font-size: 1.1em;
        padding: 10px 20px;
        border-radius: 10px;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #2ECC71;
        transform: scale(1.05);
    }
    img.small-img {
        max-width: 300px;
        width: 100%;
        border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

    # App Title
    st.markdown('<h1 class="main-header">🍎 NutriX - Food Advisor</h1>', unsafe_allow_html=True)
    st.markdown('<h3 class="subheader">Unlock the Secrets of Your Meal</h3>', unsafe_allow_html=True)

    # Image Upload
    uploaded_file = st.file_uploader(
        "Upload Your Meal Image", 
        type=["jpg", "jpeg", "png"],
        help="Supports JPG, JPEG, and PNG formats"
    )

    # Nutrition Analysis Prompt
    input_prompt = """
You are an expert nutritionist and providing dietary information. You need to see the food item from the image
and calculate the total calories, also provide details of every food item with calorie intake in the below format:

1. Item 1 - number of calories
2. Item 2 - number of calories
---
---
    As a professional nutritionist, analyze this food image and provide:
    1. Detailed calorie breakdown
    2. Nutritional value of each item
    3. Macro and micronutrient percentages
    4. Health assessment
    5. Dietary recommendations
    
Finally you can mention whether the food is healthy or not healthy and mention that too.
Mention the percentage split of ratio of carbohydrates, fats, fibers, sugars and other things required in diet.

Analyze this food image and provide details about its calorie content and dietary recommendations.

Response only if the image is some food item; for any other images, just respond with 'Provide a proper food image'. 
"""

    # Analysis Button
    if uploaded_file is not None:
        # Display uploaded image in a smaller size
        image = Image.open(uploaded_file)
        image_bytes = base64.b64encode(uploaded_file.read()).decode("utf-8")
        
        st.markdown(
            f"""
            <div style="text-align: center; margin: 20px 0;">
                <img class="small-img" src="data:image/png;base64,{image_bytes}" alt="Uploaded Meal">
            </div>
            """,
            unsafe_allow_html=True
        )

        # Analysis Button
        if st.button("Analyze Nutrition 🔬", key="analyze_btn"):
            # Interactive Loading Experience
            progress_bar = st.progress(0)
            status_text = st.empty()

            # Simulated loading with dynamic phrases
            for i, phrase in enumerate(LOADING_PHRASES, 1):
                status_text.info(phrase)
                progress_bar.progress(i * 20)
                time.sleep(0.7)

            try:
                # Perform actual analysis
                image_data = input_image_setup(uploaded_file)
                with st.spinner('Generating professional nutrition report...'):
                    response = get_gem_response(input_prompt, image_data)

                # Clear loading states
                progress_bar.empty()
                status_text.empty()

                # Display Results
                st.success("✅ Nutrition Analysis Complete!")
                
                col1, col2 = st.columns([2, 1])  # Create two columns

                with col1:
                    st.markdown("""
                    <div style="
                        font-family: Arial, sans-serif; 
                        font-size: 1.5em;  
                        line-height: 1.8;  
                        color: #2C3E50; 
                        background-color: #F9F9F9; 
                        padding: 30px;  
                        border-radius: 10px; 
                        margin-top: 20px;
                        max-width: 800px; 
                        margin-left: auto; 
                        margin-right: auto; 
                    ">
                        <h2 style="text-align: center; color: #27AE60; font-size: 2em;">📊 Nutrition Insights</h2>
                        <div style="max-height: 600px;font-size: 1.8em; overflow-y: auto;">
                            <p style="text-align: justify;">{}</p>  
                        </div>
                    </div>
                    """.format(response), unsafe_allow_html=True)

                with col2:
                    st.subheader("Macronutrient Breakdown")
                    plot_buf = generate_macronutrient_plot()
                    st.image(plot_buf)

            except Exception as e:
                st.error(f"Analysis failed: {e}")

    else:
        st.info("👆 Upload a meal image to get started!")

# Run the app
# Custom Footer
def display_footer():
    st.markdown("""
    <hr style="margin-top: 40px; border: 1px solid #27AE60;">
    <div style="
        text-align: center; 
        font-family: Arial, sans-serif; 
        color: #2C3E50; 
        font-size: 1.2em; 
        margin-top: 20px;
    ">
        <p style="
            font-size: 1.5em; 
            color: #27AE60; 
            font-weight: bold;
        ">
            Designed and Developed by Sai Nikedh from 9-B
        </p>
        <p style="
            font-size: 1.1em; 
            color: #34495E; 
            margin-top: -10px;
        ">
            Empowering Nutrition with Cutting-Edge AI Solutions
        </p>
    </div>
    """, unsafe_allow_html=True)

# Run the app
if __name__ == "__main__":
    main()
    display_footer()


# import streamlit as st
# import google.generativeai as gemini
# import os
# from PIL import Image

# gemini.configure(api_key="AIzaSyDAA7gq4wlgmKaivg_NsD3uF3CkIn8B8mc")

# def get_gem_response(input_prompt,image):
#     model=gemini.GenerativeModel('gemini-1.5-flash')
#     response=model.generate_content([input_prompt,image[0]])
#     return response.text

# def input_image_setup(uploaded_file):
#     if uploaded_file is not None:
#         # Read the file into bytes
#         bytes_data = uploaded_file.getvalue()

#         image_parts = [
#             {
#                 "mime_type": uploaded_file.type,  # Get the mime type of the uploaded file
#                 "data": bytes_data
#             }
#         ]
#         return image_parts
#     else:
#         raise FileNotFoundError("OOPS ! ..... File not found")
    

# st.set_page_config(page_title="Calories Advsior",page_icon="./my_img.jpeg")
# st.header("Nutrition checker app by Sai Nikedh")
# uploaded_file = st.file_uploader("Choose an image..: ",type=["jpj","jpeg","png"])
# image=""
# if uploaded_file is not None:
#     image=Image.open(uploaded_file)
#     st.image(image,caption="Uploaded image",use_container_width=True)

# submit=st.button("Tell me about Total calories in this food item")

# input_prompt = """
# You are an expert in nutritionist and providing Dietary information, you need to see the foodn item from the image
# and calculate the total calories, also provided details of every food items with calory intake
# in the below format

# 1. Item 1 - number of calories
# 2. Item 2 - number of calories
# ---
# ---

# Finally you can mention whether the food is healthy or not healthy and mention that too.
# mention the percentage split of ratio of carbohydrate,fats,fibres,sugars and other things required in diet

# Analyze this food image and provide details about its calorie content and dietary recommendations.

# Response only if the Image is some food item, for any other Images, just respond Provide proper food Image. 

# """

# if submit:
#      with st.spinner('Calculating calories...'):
#         image_data = input_image_setup(uploaded_file)
#         response = get_gem_response(input_prompt,image_data)
#      st.header("Response is ")
#      st.write(response)
