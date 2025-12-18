import subprocess

def get_video_thumbnail_base64(filepath):
    try:
        # Create a temporary image file
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            temp_image = tmp.name
        
        # Use ffmpeg to extract first frame
        subprocess.run([
            'ffmpeg', '-i', filepath,
            '-ss', '00:00:00.000',
            '-vframes', '1',
            temp_image,
            '-y'
        ], check=True, capture_output=True)
        
        # Convert to base64
        with Image.open(temp_image) as img:
            img.thumbnail((200, 200))
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=85)
            result = base64.b64encode(buffer.getvalue()).decode()
        
        # Clean up
        os.unlink(temp_image)
        return result
    except:
        return None
