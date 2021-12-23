import io
import base64
from PIL import Image, ImageEnhance, ImageOps


def process_image_for_output(image: Image) -> str:
    print("Processing image for output...", end='')
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(4.0)
    enhancer = ImageEnhance.Sharpness(image)
    image = enhancer.enhance(4.0)
    #image = ImageOps.grayscale(image)
    
    #image = image.convert('L')
    #image = image.point(lambda x: 0 if x<128 else 255, '1')
    image = image.convert('1')
    #image = image.convert('L')
    
    buf = io.BytesIO()
    image.save(buf, format='PNG')
    r = base64.b64encode(buf.getvalue()).decode('ascii')
    print(' [Done]')
    return r

