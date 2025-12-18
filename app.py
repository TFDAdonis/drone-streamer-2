import streamlit as st
import folium
from streamlit_folium import st_folium
from datetime import datetime
from PIL import Image
import io
import base64
import os
import json
import uuid
import tempfile
import mimetypes

st.set_page_config(
    page_title="Drone Media Mapping",
    page_icon="🛸",
    layout="wide",
    initial_sidebar_state="collapsed"
)

UPLOAD_DIR = "uploads"
DATA_FILE = "media_data.json"

os.makedirs(UPLOAD_DIR, exist_ok=True)

def load_media_data():
    """Load media data from JSON file"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        except:
            return get_sample_data()
    return get_sample_data()

def save_media_data(data):
    """Save media data to JSON file"""
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def save_uploaded_file(uploaded_file):
    """Save uploaded file and return path"""
    ext = uploaded_file.name.split('.')[-1].lower()
    filename = f"{uuid.uuid4().hex[:8]}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    
    with open(filepath, 'wb') as f:
        f.write(uploaded_file.getbuffer())
    
    return filepath

def get_image_base64(filepath):
    """Convert image to base64 for embedding in HTML"""
    try:
        if filepath and os.path.exists(filepath):
            with Image.open(filepath) as img:
                img.thumbnail((200, 200))
                buffer = io.BytesIO()
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                img.save(buffer, format='JPEG', quality=85)
                return base64.b64encode(buffer.getvalue()).decode()
    except Exception as e:
        st.error(f"Error converting image: {e}")
    return None

def get_video_thumbnail_base64(filepath):
    """Alternative to OpenCV for video thumbnails"""
    try:
        if filepath and os.path.exists(filepath):
            # For now, return a default video thumbnail
            # In production, you could use:
            # 1. moviepy (if installed)
            # 2. ffmpeg-python (if ffmpeg is available)
            # 3. Extract first frame using a subprocess call to ffmpeg
            
            # Create a default video thumbnail
            img = Image.new('RGB', (200, 200), color=(40, 44, 52))
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=85)
            return base64.b64encode(buffer.getvalue()).decode()
    except Exception as e:
        st.error(f"Error creating video thumbnail: {e}")
    return None

def get_media_thumbnail_base64(filepath, media_type):
    """Get thumbnail for media based on type"""
    if media_type == 'image':
        return get_image_base64(filepath)
    elif media_type == 'video':
        return get_video_thumbnail_base64(filepath)
    return None

def get_sample_data():
    """Return sample drone media data"""
    return [
        {
            'id': 1, 'type': 'image', 'title': 'Coastal Cliff Aerial',
            'lat': 34.0195, 'lon': -118.4912, 'timestamp': '2024-12-01 14:32:00',
            'altitude': 120, 'description': 'Stunning aerial view of coastal cliffs at sunset',
            'filepath': None
        },
        {
            'id': 2, 'type': 'video', 'title': 'Downtown Flyover',
            'lat': 34.0522, 'lon': -118.2437, 'timestamp': '2024-12-03 10:15:00',
            'altitude': 200, 'description': 'Cinematic drone flyover of downtown Los Angeles',
            'filepath': None
        }
    ]

# Initialize session state
if 'media_data' not in st.session_state:
    st.session_state.media_data = load_media_data()
    
if 'selected_lat' not in st.session_state:
    st.session_state.selected_lat = None
    
if 'selected_lon' not in st.session_state:
    st.session_state.selected_lon = None

if 'viewing_story' not in st.session_state:
    st.session_state.viewing_story = None
    
if 'current_story_index' not in st.session_state:
    st.session_state.current_story_index = 0

if 'clicked_marker_id' not in st.session_state:
    st.session_state.clicked_marker_id = None

if 'admin_authenticated' not in st.session_state:
    st.session_state.admin_authenticated = False

if 'show_admin_login' not in st.session_state:
    st.session_state.show_admin_login = False

st.markdown("""
<style>
    /* Story Viewer Overlay */
    .story-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.95);
        z-index: 9999;
        display: flex;
        align-items: center;
        justify-content: center;
        animation: fadeIn 0.3s ease;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
    
    .story-viewer {
        width: 90%;
        max-width: 800px;
        background: #000;
        border-radius: 20px;
        overflow: hidden;
        box-shadow: 0 20px 60px rgba(0,0,0,0.5);
        animation: slideUp 0.3s ease;
    }
    
    @keyframes slideUp {
        from { transform: translateY(20px); opacity: 0; }
        to { transform: translateY(0); opacity: 1; }
    }
    
    .story-header {
        padding: 20px;
        background: rgba(0,0,0,0.9);
        display: flex;
        align-items: center;
        gap: 15px;
        border-bottom: 1px solid rgba(255,255,255,0.1);
    }
    
    .story-media-container {
        width: 100%;
        height: 500px;
        background: #000;
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
    }
    
    .story-footer {
        padding: 20px;
        background: rgba(0,0,0,0.9);
        border-top: 1px solid rgba(255,255,255,0.1);
    }
    
    /* Story Cards */
    .story-card {
        background: white;
        border-radius: 15px;
        padding: 15px;
        margin-bottom: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        border: 2px solid transparent;
        transition: all 0.3s ease;
        cursor: pointer;
    }
    
    .story-card:hover {
        border-color: #FFFC00;
        transform: translateY(-2px);
    }
    
    .type-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
        margin-right: 8px;
    }
    
    .photo-badge {
        background: #00C853;
        color: white;
    }
    
    .video-badge {
        background: #FF6D00;
        color: white;
    }
    
    .location-badge {
        background: #2962FF;
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 12px;
    }
    
    /* Remove Streamlit default styling */
    .stButton > button {
        border-radius: 20px !important;
        font-weight: 600 !important;
    }
    
    /* Admin section styling */
    .admin-section {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 15px;
        margin-bottom: 20px;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

def create_story_marker(item):
    """Create Snapchat-style story marker"""
    filepath = item.get('filepath')
    media_type = item['type']
    
    # Try to get thumbnail
    thumb_base64 = get_media_thumbnail_base64(filepath, media_type)
    
    if thumb_base64:
        # With thumbnail
        if media_type == 'image':
            html = f'''
            <div style="
                width: 60px;
                height: 60px;
                border-radius: 50%;
                background: linear-gradient(135deg, #FFFC00 0%, #FF6B6B 50%, #4ECDC4 100%);
                padding: 3px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.3);
                cursor: pointer;
            ">
                <div style="
                    width: 100%;
                    height: 100%;
                    border-radius: 50%;
                    background-image: url('data:image/jpeg;base64,{thumb_base64}');
                    background-size: cover;
                    background-position: center;
                    border: 2px solid white;
                "></div>
            </div>
            '''
        else:  # video
            html = f'''
            <div style="
                width: 60px;
                height: 60px;
                border-radius: 50%;
                background: linear-gradient(135deg, #FF6D00 0%, #FFAB40 100%);
                padding: 3px;
                box-shadow: 0 4px 15px rgba(255, 109, 0, 0.5);
                cursor: pointer;
                position: relative;
            ">
                <div style="
                    width: 100%;
                    height: 100%;
                    border-radius: 50%;
                    background-image: url('data:image/jpeg;base64,{thumb_base64}');
                    background-size: cover;
                    background-position: center;
                    border: 2px solid white;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                ">
                    <div style="
                        width: 0;
                        height: 0;
                        border-left: 10px solid white;
                        border-top: 6px solid transparent;
                        border-bottom: 6px solid transparent;
                        margin-left: 2px;
                        filter: drop-shadow(0 0 2px rgba(0,0,0,0.5));
                    "></div>
                </div>
            </div>
            '''
    else:
        # Default markers without thumbnails
        if media_type == 'video':
            html = f'''
            <div style="
                width: 56px;
                height: 56px;
                border-radius: 50%;
                background: linear-gradient(135deg, #FF6D00 0%, #FFAB40 100%);
                padding: 3px;
                box-shadow: 0 4px 15px rgba(255, 109, 0, 0.5);
                cursor: pointer;
            ">
                <div style="
                    width: 100%;
                    height: 100%;
                    border-radius: 50%;
                    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    border: 2px solid white;
                ">
                    <div style="
                        width: 0;
                        height: 0;
                        border-left: 14px solid white;
                        border-top: 9px solid transparent;
                        border-bottom: 9px solid transparent;
                        margin-left: 4px;
                    "></div>
                </div>
            </div>
            '''
        else:
            html = f'''
            <div style="
                width: 52px;
                height: 52px;
                border-radius: 50%;
                background: linear-gradient(135deg, #00C853 0%, #69F0AE 100%);
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: 0 4px 12px rgba(0, 200, 83, 0.4);
                border: 3px solid white;
                cursor: pointer;
            ">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="white">
                    <circle cx="12" cy="12" r="3"/>
                    <path d="M9 2L7.17 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2h-3.17L15 2H9zm3 15c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5z"/>
                </svg>
            </div>
            '''
    
    return folium.DivIcon(html=html, icon_size=(60, 60), icon_anchor=(30, 30))

def create_map():
    """Create the map"""
    if st.session_state.media_data:
        center_lat = sum(item['lat'] for item in st.session_state.media_data) / len(st.session_state.media_data)
        center_lon = sum(item['lon'] for item in st.session_state.media_data) / len(st.session_state.media_data)
    else:
        center_lat, center_lon = 34.0522, -118.2437
    
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=11,
        tiles=None,
        control_scale=False
    )
    
    folium.TileLayer(
        tiles='https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
        attr='OpenStreetMap & CARTO',
        name='Map',
        max_zoom=19
    ).add_to(m)
    
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Satellite',
        max_zoom=19
    ).add_to(m)
    
    for idx, item in enumerate(st.session_state.media_data):
        icon = create_story_marker(item)
        
        popup_html = folium.Popup(f'<a href="?story_id={item["id"]}" style="text-decoration:none;"><b>{item["title"]}</b></a>', max_width=200)
        
        folium.Marker(
            location=[item['lat'], item['lon']],
            icon=icon,
            popup=popup_html,
            tooltip=f"Click marker to view: {item['title']}"
        ).add_to(m)
    
    folium.LayerControl(position='topright').add_to(m)
    return m

def find_story_by_location(lat, lon, tolerance=0.001):
    """Find a story by its approximate location"""
    for idx, story in enumerate(st.session_state.media_data):
        if abs(story['lat'] - lat) < tolerance and abs(story['lon'] - lon) < tolerance:
            return idx, story
    return None, None

# Check if viewing a story
if st.session_state.viewing_story is not None:
    current_story = st.session_state.media_data[st.session_state.current_story_index]
    
    if st.button("✕ Close", key="close_story"):
        st.session_state.viewing_story = None
        st.rerun()
    
    st.markdown("---")
    
    if current_story.get('filepath') and os.path.exists(current_story['filepath']):
        if current_story['type'] == 'image':
            try:
                st.image(current_story['filepath'], width=1200)
            except Exception as e:
                st.error(f"Error loading image: {str(e)}")
        else:
            try:
                video_file = open(current_story['filepath'], 'rb')
                video_bytes = video_file.read()
                st.video(video_bytes)
                video_file.close()
            except Exception as e:
                st.error(f"Error loading video: {str(e)}")
    else:
        icon = '🎬' if current_story['type'] == 'video' else '📷'
        st.markdown(f"""
        <div style="text-align: center; padding: 100px 20px; background: #f0f0f0; border-radius: 10px;">
            <div style="font-size: 80px; margin-bottom: 20px;">{icon}</div>
            <h2>{current_story['title']}</h2>
            <p style="font-size: 18px; color: #666;">{current_story['description']}</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.stop()

# Main app interface
st.markdown("""
<div style="text-align: center; margin-bottom: 30px;">
    <h1 style="font-size: 36px; font-weight: 800; color: #000; margin-bottom: 10px;">
        Drone Media Map
        <span style="background: #FFFC00; color: #000; padding: 6px 16px; border-radius: 20px; font-size: 16px; font-weight: 700;">
            SNAP STYLE
        </span>
    </h1>
    <p style="color: #666;">Click on any map marker to view the story</p>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns([5, 1])

with col1:
    m = create_map()
    map_output = st_folium(m, width=None, height=600, key="main_map")
    
    if map_output and map_output.get('last_object_clicked'):
        clicked = map_output['last_object_clicked']
        if clicked:
            click_lat = clicked.get('lat')
            click_lng = clicked.get('lng')
            if click_lat and click_lng:
                # Find stories at the clicked location, prioritize uploaded files
                stories_at_location = []
                
                for idx, story in enumerate(st.session_state.media_data):
                    distance = ((story['lat'] - click_lat)**2 + (story['lon'] - click_lng)**2)**0.5
                    if distance < 0.02:
                        has_file = story.get('filepath') and os.path.exists(story['filepath'])
                        stories_at_location.append((distance, has_file, idx, story))
                
                if stories_at_location:
                    # Sort by: has file (True first), then distance
                    stories_at_location.sort(key=lambda x: (not x[1], x[0]))
                    distance, has_file, nearest_idx, nearest_story = stories_at_location[0]
                    st.session_state.viewing_story = nearest_story['id']
                    st.session_state.current_story_index = nearest_idx
                    st.rerun()
    
    st.markdown("### Quick View")
    cols = st.columns(3)
    for idx, story in enumerate(st.session_state.media_data[:6]):
        with cols[idx % 3]:
            if st.button(f"View {story['title'][:15]}...", 
                       key=f"quick_view_{story['id']}",
                       use_container_width=True):
                st.session_state.viewing_story = story['id']
                st.session_state.current_story_index = idx
                st.rerun()
            
            if story.get('filepath') and os.path.exists(story['filepath']) and story['type'] == 'image':
                try:
                    with Image.open(story['filepath']) as img:
                        img.thumbnail((200, 150))
                        st.image(img, use_container_width=True)
                except:
                    pass

with col2:
    st.markdown("### Legend")
    st.markdown("""
    <div style="padding: 8px 0;">
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px;">
            <div style="width: 14px; height: 14px; border-radius: 50%; background: linear-gradient(135deg, #00C853 0%, #69F0AE 100%); border: 2px solid white;"></div>
            <span style="font-size: 13px;">Photo</span>
        </div>
        <div style="display: flex; align-items: center; gap: 10px;">
            <div style="width: 14px; height: 14px; border-radius: 50%; background: linear-gradient(135deg, #FF6D00 0%, #FFAB40 100%); border: 2px solid white;"></div>
            <span style="font-size: 13px;">Video</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### Stats")
    total = len(st.session_state.media_data)
    images = sum(1 for x in st.session_state.media_data if x['type'] == 'image')
    videos = sum(1 for x in st.session_state.media_data if x['type'] == 'video')
    st.metric("Total", total)
    st.metric("Photos", images)
    st.metric("Videos", videos)

st.markdown("---")
st.markdown("## All Stories")

if st.session_state.media_data:
    cols = st.columns(3)
    
    for idx, story in enumerate(st.session_state.media_data):
        with cols[idx % 3]:
            if st.button(f"View {story['title'][:20]}...", 
                        key=f"view_{story['id']}",
                        use_container_width=True,
                        help=f"Click to view this story"):
                st.session_state.viewing_story = story['id']
                st.session_state.current_story_index = idx
                st.rerun()
            
            st.markdown(f"""
            <div style="background: #f8f9fa; padding: 15px; border-radius: 10px; margin-top: 5px;">
                <div style="font-weight: 600; font-size: 16px; color: #333;">{story['title']}</div>
                <div style="font-size: 12px; color: #666; margin: 5px 0;">{story['timestamp'][:10]} • {story['altitude']}m</div>
                <div style="font-size: 14px; color: #555;">{story['description'][:80]}...</div>
                <div style="margin-top: 10px;">
                    <span style="
                        display: inline-block;
                        padding: 3px 10px;
                        border-radius: 10px;
                        font-size: 11px;
                        font-weight: 600;
                        background: {'#00C853' if story['type'] == 'image' else '#FF6D00'};
                        color: white;
                    ">{'PHOTO' if story['type'] == 'image' else 'VIDEO'}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("")

st.markdown("---")

# Admin Authentication Section
if not st.session_state.admin_authenticated:
    col1, col2, col3 = st.columns([1, 1, 20])
    with col3:
        if st.button("🔓", key="admin_toggle", help="Admin access"):
            st.session_state.show_admin_login = not st.session_state.show_admin_login
    
    if st.session_state.show_admin_login:
        with st.form("admin_login_form"):
            admin_username = st.text_input("Username", placeholder="Enter username")
            admin_password = st.text_input("Password", type="password", placeholder="Enter password")
            login_button = st.form_submit_button("Login", use_container_width=True)
            
            if login_button:
                correct_password = os.getenv('ADMIN_PASSWORD', '')
                if admin_username == "farouk" and admin_password == correct_password:
                    st.session_state.admin_authenticated = True
                    st.session_state.show_admin_login = False
                    st.success("✓ Admin access granted!")
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password")
else:
    st.markdown("## Upload New Media")
    
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.admin_authenticated = False
            st.rerun()

if st.session_state.admin_authenticated:
    with st.form("upload_form", clear_on_submit=True):
        st.markdown("### Add Photo or Video")
        
        uploaded_file = st.file_uploader(
            "Choose a photo or video file",
            type=['jpg', 'jpeg', 'png', 'gif', 'mp4', 'mov', 'avi', 'webm'],
            help="Supported formats: JPG, PNG, GIF for photos; MP4, MOV, AVI, WEBM for videos"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            title = st.text_input("Title", placeholder="e.g., Beach Sunset Aerial")
            latitude = st.number_input("Latitude", value=34.0522, format="%.6f", help="Enter the latitude coordinate")
        
        with col2:
            altitude = st.number_input("Altitude (meters)", value=100, min_value=0, max_value=10000)
            longitude = st.number_input("Longitude", value=-118.2437, format="%.6f", help="Enter the longitude coordinate")
        
        description = st.text_area("Description", placeholder="Describe your drone media...", height=100)
        
        submit_button = st.form_submit_button("Upload Media", type="primary", use_container_width=True)
        
        if submit_button:
            if uploaded_file is not None and title:
                ext = uploaded_file.name.split('.')[-1].lower()
                if ext in ['jpg', 'jpeg', 'png', 'gif']:
                    media_type = 'image'
                else:
                    media_type = 'video'
                
                filepath = save_uploaded_file(uploaded_file)
                
                new_id = max([item['id'] for item in st.session_state.media_data], default=0) + 1
                
                new_media = {
                    'id': new_id,
                    'type': media_type,
                    'title': title,
                    'lat': latitude,
                    'lon': longitude,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'altitude': altitude,
                    'description': description if description else f"Uploaded {media_type}",
                    'filepath': filepath
                }
                
                st.session_state.media_data.append(new_media)
                save_media_data(st.session_state.media_data)
                
                st.success(f"Successfully uploaded {media_type}: {title}")
                st.rerun()
            elif not uploaded_file:
                st.error("Please select a file to upload")
            elif not title:
                st.error("Please enter a title for your media")
