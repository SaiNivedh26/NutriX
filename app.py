import streamlit as st
import google.generativeai as gemini
import os
from PIL import Image

gemini.configure(api_key="AIzaSyDAA7gq4wlgmKaivg_NsD3uF3CkIn8B8mc")

def get_gem_response(input_prompt,image):
    model=gemini.GenerativeModel('gemini-1.5-flash')
    response=model.generate_content([input_prompt,image[0]])
    return response.text

def input_image_setup(uploaded_file):
    if uploaded_file is not None:
        # Read the file into bytes
        bytes_data = uploaded_file.getvalue()

        image_parts = [
            {
                "mime_type": uploaded_file.type,  # Get the mime type of the uploaded file
                "data": bytes_data
            }
        ]
        return image_parts
    else:
        raise FileNotFoundError("OOPS ! ..... File not found")
    

st.set_page_config(page_title="Calories Advsior",page_icon="./my_img.jpeg")
st.header("Nutrition checker app by Sai Nikedh")
uploaded_file = st.file_uploader("Choose an image..: ",type=["jpj","jpeg","png"])
image=""
if uploaded_file is not None:
    image=Image.open(uploaded_file)
    st.image(image,caption="Uploaded image",use_container_width=True)

submit=st.button("Tell me about Total calories in this food item")

input_prompt = """
You are an expert in nutritionist and providing Dietary information, you need to see the foodn item from the image
and calculate the total calories, also provided details of every food items with calory intake
in the below format

1. Item 1 - number of calories
2. Item 2 - number of calories
---
---

Finally you can mention whether the food is healthy or not healthy and mention that too.
mention the percentage split of ratio of carbohydrate,fats,fibres,sugars and other things required in diet

Analyze this food image and provide details about its calorie content and dietary recommendations.

Response only if the Image is some food item, for any other Images, just respond Provide proper food Image. 

"""

if submit:
     with st.spinner('Calculating calories...'):
        image_data = input_image_setup(uploaded_file)
        response = get_gem_response(input_prompt,image_data)
     st.header("Response is ")
     st.write(response)
