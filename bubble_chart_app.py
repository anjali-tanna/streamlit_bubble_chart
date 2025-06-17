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
    .chart-container {
        border: 2px solid #e6e6e6;
        border-radius: 10px;
        padding: 20px;
        margin: 20px 0;
        background-color: #fafafa;
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

# NEW: Static horizontal line option
st.sidebar.subheader("📍 Static Reference Lines")
use_static_horizontal = st.sidebar.checkbox("Use Static Horizontal Line")
static_horizontal_value = st.sidebar.number_input("Static Horizontal Value", value=0.0, disabled=not use_static_horizontal)

use_static_vertical = st.sidebar.checkbox("Use Static Vertical Line")
static_vertical_value = st.sidebar.number_input("Static Vertical Value", value=0.0, disabled=not use_static_vertical)

# Helper functions
@st.cache_data
def load_data(file):
    """Load CSV data"""
    if file is not None:
        return pd.read_csv(file)
    return None

def convert_to_numeric(series, column_name):
    """Convert series to numeric, handling strings by encoding them"""
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors='coerce')
    else:
        # For non-numeric data, create a categorical encoding
        unique_values = series.dropna().unique()
        value_map = {val: i for i, val in enumerate(sorted(unique_values))}
        numeric_series = series.map(value_map)
        st.info(f"📝 Column '{column_name}' contains non-numeric data. Converted to numeric using categorical encoding.")
        with st.expander(f"View encoding for '{column_name}'"):
            for original, encoded in value_map.items():
                st.write(f"'{original}' → {encoded}")
        return numeric_series

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

def create_static_chart(data, params, title_suffix=""):
    """Create a static bubble chart"""
    # Convert columns to numeric
    data_processed = data.copy()
    data_processed[params['x_column']] = convert_to_numeric(data[params['x_column']], params['x_column'])
    data_processed[params['y_column']] = convert_to_numeric(data[params['y_column']], params['y_column'])
    data_processed[params['size_column']] = convert_to_numeric(data[params['size_column']], params['size_column'])
    
    # Apply scaling
    data_processed[params['size_column']] *= params['scale']
    
    # Calculate medians or use static values
    if params.get('use_static_horizontal', False):
        median_y = params['static_horizontal_value']
    else:
        median_y = data_processed[params['y_column']].median()
    
    if params.get('use_static_vertical', False):
        median_x = params['static_vertical_value']
    else:
        median_x = data_processed[params['x_column']].median()
    
    # Set up axis limits
    min_x, max_x = data_processed[params['x_column']].min(), data_processed[params['x_column']].max()
    min_y, max_y = data_processed[params['y_column']].min(), data_processed[params['y_column']].max()
    
    x_range, y_range = max_x - min_x, max_y - min_y
    x_padding = x_range * 0.15 if x_range > 0 else 1
    y_padding = y_range * 0.15 if y_range > 0 else 1
    
    xlim = (min_x - x_padding, max_x + x_padding)
    ylim = (min_y - y_padding, max_y + y_padding)
    
    # Create plot
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Create scatter plot
    ax.scatter(data_processed[params['x_column']], 
              data_processed[params['y_column']], 
              s=data_processed[params['size_column']], 
              alpha=0.75,
              c=data_processed[params['category_column']].map(params['colors']), 
              edgecolors='white', linewidth=0.8)
    
    # Add median lines
    ax.axvline(median_x, color='#666666', linestyle='-', linewidth=1.0, alpha=0.8)
    ax.axhline(median_y, color='#666666', linestyle='-', linewidth=1.0, alpha=0.8)
    
    # Add labels
    for i, (x_val, y_val, title) in enumerate(zip(data_processed[params['x_column']], 
                                                   data_processed[params['y_column']], 
                                                   data_processed[params['label_column']])):
        if pd.notna(title):
            ax.annotate(str(title), (x_val, y_val), color='black',
                       textcoords="offset points", xytext=(0, 12), 
                       ha='center', fontsize=9, fontweight='normal')
    
    # Styling
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    ax.tick_params(labelsize=10)
    ax.set_facecolor('#FAFAFA')
    
    # Add axis labels
    ax.set_xlabel(params['x_column'], fontsize=12, fontweight='bold')
    ax.set_ylabel(params['y_column'], fontsize=12, fontweight='bold')
    
    for spine in ax.spines.values():
        spine.set_visible(False)
    
    ax.set_title(f'{params["title"]} {title_suffix}', 
                fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    return fig

def create_animated_chart(start_data, end_data, params):
    """Create the animated bubble chart"""
    # Convert columns to numeric for both datasets
    start_processed = start_data.copy()
    end_processed = end_data.copy()
    
    start_processed[params['x_column']] = convert_to_numeric(start_data[params['x_column']], params['x_column'])
    start_processed[params['y_column']] = convert_to_numeric(start_data[params['y_column']], params['y_column'])
    start_processed[params['size_column']] = convert_to_numeric(start_data[params['size_column']], params['size_column'])
    
    end_processed[params['x_column']] = convert_to_numeric(end_data[params['x_column']], params['x_column'])
    end_processed[params['y_column']] = convert_to_numeric(end_data[params['y_column']], params['y_column'])
    end_processed[params['size_column']] = convert_to_numeric(end_data[params['size_column']], params['size_column'])
    
    # Apply scaling
    start_processed[params['size_column']] *= params['scale']
    end_processed[params['size_column']] *= params['scale']
    
    # Calculate medians or use static values
    if params.get('use_static_horizontal', False):
        q1median_y = q2median_y = params['static_horizontal_value']
    else:
        q1median_y = start_processed[params['y_column']].median()
        q2median_y = end_processed[params['y_column']].median()
    
    if params.get('use_static_vertical', False):
        q1median_x = q2median_x = params['static_vertical_value']
    else:
        q1median_x = start_processed[params['x_column']].median()
        q2median_x = end_processed[params['x_column']].median()
    
    # Set up axis limits
    all_x = pd.concat([start_processed[params['x_column']], end_processed[params['x_column']]])
    all_y = pd.concat([start_processed[params['y_column']], end_processed[params['y_column']]])
    
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
        x = start_processed[params['x_column']] + (end_processed[params['x_column']] - start_processed[params['x_column']]) * progress
        y = start_processed[params['y_column']] + (end_processed[params['y_column']] - start_processed[params['y_column']]) * progress
        sizes = start_processed[params['size_column']] + (end_processed[params['size_column']] - start_processed[params['size_column']]) * progress
        
        # Create scatter plot
        ax.scatter(x, y, s=sizes, alpha=0.75, 
                  c=start_processed[params['category_column']].map(params['colors']), 
                  edgecolors='white', linewidth=0.8)
        
        # Add median lines
        current_x_pos = q1median_x + (q2median_x - q1median_x) * progress
        current_y_pos = q1median_y + (q2median_y - q1median_y) * progress
        
        ax.axvline(current_x_pos, color='#666666', linestyle='-', linewidth=1.0, alpha=0.8)
        ax.axhline(current_y_pos, color='#666666', linestyle='-', linewidth=1.0, alpha=0.8)
        
        # Add labels
        for i, (x_val, y_val, title) in enumerate(zip(x, y, start_processed[params['label_column']])):
            if pd.notna(title):
                ax.annotate(str(title), (x_val, y_val), color='black',
                           textcoords="offset points", xytext=(0, 12), 
                           ha='center', fontsize=9, fontweight='normal')
        
        # Styling
        ax.set_xlim(xlim)
        ax.set_ylim(ylim)
        ax.tick_params(labelsize=10)
        ax.set_facecolor('#FAFAFA')
        
        # Add axis labels
        ax.set_xlabel(params['x_column'], fontsize=12, fontweight='bold')
        ax.set_ylabel(params['y_column'], fontsize=12, fontweight='bold')
        
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
                st.dataframe(start_data.head(), height=200)
            
            with col2:
                st.subheader("📉 End Data")
                st.write(f"Shape: {end_data.shape}")
                st.dataframe(end_data.head(), height=200)
            
            # Show column types
            st.subheader("📊 Column Information")
            col_info_col1, col_info_col2 = st.columns(2)
            
            with col_info_col1:
                st.write("**Start Data Column Types:**")
                st.write(start_data.dtypes.to_dict())
            
            with col_info_col2:
                st.write("**End Data Column Types:**")  
                st.write(end_data.dtypes.to_dict())
            
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
            
            # Step 5: Generate Charts
            if selected_points:
                st.markdown('<div class="step-header">🎬 Step 5: Generate Charts</div>', unsafe_allow_html=True)
                
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
                    'title': custom_title,
                    'use_static_horizontal': use_static_horizontal,
                    'static_horizontal_value': static_horizontal_value,
                    'use_static_vertical': use_static_vertical,
                    'static_vertical_value': static_vertical_value
                }
                
                chart_col1, chart_col2 = st.columns(2)
                
                with chart_col1:
                    if st.button("📊 Generate Static Chart (End Data)", type="primary"):
                        with st.spinner("Creating static chart..."):
                            fig_static = create_static_chart(final_end, params, "- End State")
                            
                            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                            st.markdown("### 📊 Static Bubble Chart (End Data)")
                            st.pyplot(fig_static, use_container_width=True)
                            st.markdown('</div>', unsafe_allow_html=True)
                            
                            # Download static chart
                            buf = io.BytesIO()
                            fig_static.savefig(buf, format='png', dpi=300, bbox_inches='tight')
                            buf.seek(0)
                            
                            st.download_button(
                                label="📥 Download Static Chart (PNG)",
                                data=buf.getvalue(),
                                file_name=f"{custom_title.lower().replace(' ', '_')}_static.png",
                                mime="image/png"
                            )
                
                with chart_col2:
                    if st.button("🎬 Generate Animated Chart", type="primary"):
                        with st.spinner("Creating animation..."):
                            # Create and display animation
                            fig, anim = create_animated_chart(final_start, final_end, params)
                            
                            # Convert to HTML
                            html_str = anim.to_jshtml()
                            
                            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                            st.markdown("### 🎬 Animated Bubble Chart")
                            st.components.v1.html(html_str, height=800, scrolling=False)
                            st.markdown('</div>', unsafe_allow_html=True)
                            
                            # Download options
                            st.markdown("### 📥 Download Animation")
                            
                            download_col1, download_col2 = st.columns(2)
                            
                            with download_col1:
                                # HTML download
                                filename = f"{custom_title.lower().replace(' ', '_')}_animation.html"
                                st.download_button(
                                    label="📄 Download HTML",
                                    data=html_str,
                                    file_name=filename,
                                    mime="text/html"
                                )
                            
                            with download_col2:
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
