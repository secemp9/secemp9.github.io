import requests
from PIL import Image
from io import BytesIO

# URL of the profile picture
PROFILE_PIC_URL = 'https://pbs.twimg.com/profile_images/1904889083505053698/fIdxky7Q_400x400.jpg'

# Download the image
def download_image(url):
    response = requests.get(url)
    response.raise_for_status()
    return Image.open(BytesIO(response.content))

# Resize and save as favicon.ico and favicon.png
def make_favicon(img, size=(32, 32)):
    img = img.convert('RGBA')
    img = img.resize(size, Image.LANCZOS)
    img.save('favicon.png', format='PNG')
    img.save('favicon.ico', format='ICO')
    print('Saved favicon.png and favicon.ico')

if __name__ == '__main__':
    img = download_image(PROFILE_PIC_URL)
    make_favicon(img) 