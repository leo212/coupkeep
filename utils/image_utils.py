"""
Utility functions for image processing.
"""

from PIL import Image
import io

def resize_image(image_bytes, max_width=800, max_height=800):
    """
    Resize an image while preserving aspect ratio.
    
    Args:
        image_bytes: The image data as bytes
        max_width: Maximum width of the resized image
        max_height: Maximum height of the resized image
        
    Returns:
        Bytes of the resized image, or the original bytes if no resizing was needed
    """
    with Image.open(io.BytesIO(image_bytes)) as img:
        # Only resize if the image is larger than the target size
        if img.width > max_width or img.height > max_height:
            img.thumbnail((max_width, max_height), Image.LANCZOS)  # Preserves aspect ratio
            output = io.BytesIO()
            img.save(output, format=img.format)
            return output.getvalue()
        else:
            return image_bytes