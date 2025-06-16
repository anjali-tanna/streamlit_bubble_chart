import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
import io
import base64
import random
import colorsys
import time
import os
from matplotlib import font_manager as fm
import matplotlib as mpl

# Set page config
st.set_page_config(
    page_title="Dynamic Bubble Chart Generator",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        color: #1f77b4;
        margin-bottom: 2rem;
    }
    .step-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #2e8b57;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .status-box {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .info-box {
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
if 'config_loaded' not in st.session_state:
    st.session_state.config_loaded = False
if 'current_start_data' not in st.session_state:
    st.session_state.current_start_data = None
if 'current_end_data' not in st.session_state:
    st.session_state.current_end_data = None
if 'discovered_categories' not in st.session_state:
    st.session_state.discovered_categories = []
if 'colors' not in st.session_state:
    st.session_state.colors = {}

# Header
st.markdown('<div class="main-header">🎯 Dynamic Bubble Chart Generator</div>', unsafe_allow_html=True)
st.markdown("### 📂 Categories → 📊 Points → 🎬 Animate")

# Sidebar for configuration
st.sidebar.title("⚙️ Configuration")

# File uploads
st.sidebar.subheader("📁 Data Files")
start_file = st.sidebar.file_uploader("Upload Start Data (CSV)", type=['csv'], key="start")
end_file = st.sidebar.file_uploader("Upload End Data (CSV)", type=['csv'], key="end")

# Chart parameters
st.sidebar.subheader("📊 Chart Parameters")
custom_title = st.sidebar.text_input("Chart Title", value="Chart Title", help="Will become 'Your Title Landscape Over Time'")
label_column = st.sidebar.text_input("Label Column", value="Topic")
category_column = st.sidebar.text_input("Category Column", value="Category")
x_column = st.sidebar.text_input("X-axis Column", value="X-axis")
y_column = st.sidebar.text_input("Y-axis Column", value="Y-axis")
size_column = st.sidebar.text_input("Size Column", value="Size")

# Animation settings
st.sidebar.subheader("🎬 Animation Settings")
num_frames = st.sidebar.slider("Number of Frames", 30, 200, 100)
interval = st.sidebar.slider("Speed (ms)", 50, 500, 150)
scale = st.sidebar.number_input("Size Scale", value=0.000005, format="%.6f")

# Helper functions
@st.cache_data
def load_data(file):
    """Load CSV data"""
    if file is not None:
        return pd.read_csv(file)
    return None

def discover_categories_from_data(start_data, end_data, category_column):
    """Discover unique categories"""
    all_categories = pd.concat([
        start_data[category_column], 
        end_data[category_column]
    ]).unique()
    
    categories = [str(cat) for cat in all_categories if pd.notna(cat)]
    return sorted(categories)

def generate_distinct_colors(num_colors):
    """Generate visually distinct colors"""
    colors = []
    golden_ratio = 0.618033988749895
    
    for i in range(num_colors):
        hue = (i * golden_ratio) % 1.0
        saturation = 0.7 + (i % 3) * 0.1
        value = 0.8 + (i % 2) * 0.15
        
        r, g, b = colorsys.hsv_to_rgb(hue, saturation, value)
        hex_color = f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
        colors.append(hex_color)
    
    return colors

def create_animated_chart(start_data, end_data, params):
    """Create the animated bubble chart"""
    # Apply scaling
    start_scaled = start_data.copy()
    end_scaled = end_data.copy()
    start_scaled[params['size_column']] *= params['scale']
    end_scaled[params['size_column']] *= params['scale']
    
    # Calculate medians
    q1median_x = start_scaled[params['x_column']].median()
    q2median_x = end_scaled[params['x_column']].median()
    q1median_y = start_scaled[params['y_column']].median()
    q2median_y = end_scaled[params['y_column']].median()
    
    # Set up axis limits
    all_x = pd.concat([start_scaled[params['x_column']], end_scaled[params['x_column']]])
    all_y = pd.concat([start_scaled[params['y_column']], end_scaled[params['y_column']]])
    
    min_x, max_x = all_x.min(), all_x.max()
    min_y, max_y = all_y.min(), all_y.max()
    
    x_range, y_range = max_x - min_x, max_y - min_y
    x_padding = x_range * 0.15 if x_range > 0 else 1
    y_padding = y_range * 0.15 if y_range > 0 else 1
    
    xlim = (min_x - x_padding, max_x + x_padding)
    ylim = (min_y - y_padding, max_y + y_padding)
    
    # Create animation
    fig, ax = plt.subplots(figsize=(12, 8))
    
    def animate(frame):
        ax.clear()
        
        progress = frame / (params['num_frames'] - 1) if params['num_frames'] > 1 else 0
        
        # Interpolate data
        x = start_scaled[params['x_column']] + (end_scaled[params['x_column']] - start_scaled[params['x_column']]) * progress
        y = start_scaled[params['y_column']] + (end_scaled[params['y_column']] - start_scaled[params['y_column']]) * progress
        sizes = start_scaled[params['size_column']] + (end_scaled[params['size_column']] - start_scaled[params['size_column']]) * progress
        
        # Create scatter plot
        ax.scatter(x, y, s=sizes, alpha=0.75, 
                  c=start_scaled[params['category_column']].map(params['colors']), 
                  edgecolors='white', linewidth=0.8)
        
        # Add median lines
        current_x_pos = q1median_x + (q2median_x - q1median_x) * progress
        current_y_pos = q1median_y + (q2median_y - q1median_y) * progress
        
        ax.axvline(current_x_pos, color='#666666', linestyle='-', linewidth=1.0, alpha=0.8)
        ax.axhline(current_y_pos, color='#666666', linestyle='-', linewidth=1.0, alpha=0.8)
        
        # Add labels
        for i, (x_val, y_val, title) in enumerate(zip(x, y, start_scaled[params['label_column']])):
            if pd.notna(title):
                ax.annotate(str(title), (x_val, y_val), color='black',
                           textcoords="offset points", xytext=(0, 12), 
                           ha='center', fontsize=9, fontweight='normal')
        
        # Styling
        ax.set_xlim(xlim)
        ax.set_ylim(ylim)
        ax.set_xticklabels([])
        ax.set_yticklabels([])
        ax.tick_params(left=False, bottom=False)
        ax.set_facecolor('#FAFAFA')
        
        for spine in ax.spines.values():
            spine.set_visible(False)
        
        ax.set_title(f'{params["title"]} Landscape Over Time - Frame {frame+1}', 
                    fontsize=14, fontweight='bold')
    
    anim = FuncAnimation(fig, animate, frames=params['num_frames'], 
                       interval=params['interval'], repeat=True, blit=False)
    
    plt.tight_layout()
    return fig, anim

# Main app logic
def main():
    # Step 1: Data Upload and Preview
    st.markdown('<div class="step-header">📁 Step 1: Data Upload & Preview</div>', unsafe_allow_html=True)
    
    if start_file and end_file:
        try:
            start_data = load_data(start_file)
            end_data = load_data(end_file)
            
            st.session_state.current_start_data = start_data
            st.session_state.current_end_data = end_data
            st.session_state.data_loaded = True
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📈 Start Data")
                st.write(f"Shape: {start_data.shape}")
                st.dataframe(start_data.head())
            
            with col2:
                st.subheader("📉 End Data")
                st.write(f"Shape: {end_data.shape}")
                st.dataframe(end_data.head())
            
            # Discover categories
            if category_column in start_data.columns:
                categories = discover_categories_from_data(start_data, end_data, category_column)
                st.session_state.discovered_categories = categories
                
                st.markdown('<div class="status-box success-box">✅ Data loaded successfully!</div>', unsafe_allow_html=True)
                st.write(f"**Categories found:** {len(categories)}")
                
                # Show category breakdown
                with st.expander("📊 Category Breakdown"):
                    for cat in categories:
                        count = len(start_data[start_data[category_column] == cat])
                        st.write(f"• **{cat}**: {count} data points")
            
        except Exception as e:
            st.markdown(f'<div class="status-box error-box">❌ Error loading data: {str(e)}</div>', unsafe_allow_html=True)
    
    else:
        st.markdown('<div class="status-box info-box">📤 Please upload both start and end data files</div>', unsafe_allow_html=True)
    
    # Step 2: Color Configuration
    if st.session_state.data_loaded and st.session_state.discovered_categories:
        st.markdown('<div class="step-header">🎨 Step 2: Color Configuration</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # Generate default colors
            if not st.session_state.colors:
                default_colors = generate_distinct_colors(len(st.session_state.discovered_categories))
                for i, cat in enumerate(st.session_state.discovered_categories):
                    st.session_state.colors[cat] = default_colors[i]
            
            # Color pickers
            color_cols = st.columns(min(3, len(st.session_state.discovered_categories)))
            for i, category in enumerate(st.session_state.discovered_categories):
                with color_cols[i % 3]:
                    st.session_state.colors[category] = st.color_picker(
                        f"{category}", 
                        value=st.session_state.colors.get(category, "#1f77b4"),
                        key=f"color_{category}"
                    )
        
        with col2:
            if st.button("🎨 Auto-Assign Colors"):
                new_colors = generate_distinct_colors(len(st.session_state.discovered_categories))
                for i, cat in enumerate(st.session_state.discovered_categories):
                    st.session_state.colors[cat] = new_colors[i]
                st.rerun()
            
            if st.button("🎲 Randomize Colors"):
                for cat in st.session_state.discovered_categories:
                    hue = random.random()
                    saturation = 0.6 + random.random() * 0.4
                    value = 0.7 + random.random() * 0.3
                    r, g, b = colorsys.hsv_to_rgb(hue, saturation, value)
                    st.session_state.colors[cat] = f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
                st.rerun()
    
    # Step 3: Data Selection
    if st.session_state.data_loaded and st.session_state.discovered_categories:
        st.markdown('<div class="step-header">📂 Step 3: Category Selection</div>', unsafe_allow_html=True)
        
        selected_categories = st.multiselect(
            "Select categories to include:",
            options=st.session_state.discovered_categories,
            default=st.session_state.discovered_categories,
            help="Choose which categories to include in your animation"
        )
        
        if selected_categories:
            st.markdown('<div class="step-header">📊 Step 4: Point Selection</div>', unsafe_allow_html=True)
            
            # Filter data by selected categories
            start_data = st.session_state.current_start_data
            end_data = st.session_state.current_end_data
            
            category_mask = start_data[category_column].isin(selected_categories)
            filtered_start = start_data[category_mask]
            
            # Point selection by category
            selected_points = []
            
            for category in selected_categories:
                cat_data = filtered_start[filtered_start[category_column] == category]
                
                with st.expander(f"📁 {category} ({len(cat_data)} points)", expanded=True):
                    options = []
                    for idx, row in cat_data.iterrows():
                        label_text = str(row[label_column]) if pd.notna(row[label_column]) else f"Point {idx}"
                        options.append((label_text, idx))
                    
                    selected_in_category = st.multiselect(
                        f"Select points from {category}:",
                        options=[opt[0] for opt in options],
                        default=[opt[0] for opt in options],
                        key=f"points_{category}"
                    )
                    
                    # Get indices of selected points
                    selected_indices = [opt[1] for opt in options if opt[0] in selected_in_category]
                    selected_points.extend(selected_indices)
            
            # Step 5: Generate Animation
            if selected_points:
                st.markdown('<div class="step-header">🎬 Step 5: Generate Animation</div>', unsafe_allow_html=True)
                
                if st.button("🎬 Generate Animated Chart", type="primary"):
                    with st.spinner("Creating animation..."):
                        # Filter data to selected points
                        final_start = start_data.iloc[selected_points].copy().reset_index(drop=True)
                        final_end = end_data.iloc[selected_points].copy().reset_index(drop=True)
                        
                        # Prepare parameters
                        params = {
                            'x_column': x_column,
                            'y_column': y_column,
                            'size_column': size_column,
                            'category_column': category_column,
                            'label_column': label_column,
                            'num_frames': num_frames,
                            'interval': interval,
                            'scale': scale,
                            'colors': st.session_state.colors,
                            'title': custom_title
                        }
                        
                        # Create and display animation
                        fig, anim = create_animated_chart(final_start, final_end, params)
                        
                        # Convert to HTML
                        html_str = anim.to_jshtml()
                        
                        st.markdown('<div class="status-box success-box">✅ Animation created successfully!</div>', unsafe_allow_html=True)
                        
                        # Display animation
                        st.components.v1.html(html_str, height=600, scrolling=True)
                        
                        # Download options
                        st.markdown("### 📥 Download Options")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            # HTML download
                            filename = f"{custom_title.lower().replace(' ', '_')}_animation.html"
                            st.download_button(
                                label="📄 Download HTML",
                                data=html_str,
                                file_name=filename,
                                mime="text/html"
                            )
                        
                        with col2:
                            # GIF download
                            if st.button("🎥 Create GIF"):
                                with st.spinner("Creating GIF..."):
                                    gif_filename = f"{custom_title.lower().replace(' ', '_')}_animation.gif"
                                    writer = PillowWriter(fps=10)
                                    anim.save(gif_filename, writer=writer)
                                    
                                    with open(gif_filename, "rb") as f:
                                        gif_data = f.read()
                                    
                                    st.download_button(
                                        label="📥 Download GIF",
                                        data=gif_data,
                                        file_name=gif_filename,
                                        mime="image/gif"
                                    )
                                    
                                    # Clean up
                                    os.remove(gif_filename)

if __name__ == "__main__":
    main()
