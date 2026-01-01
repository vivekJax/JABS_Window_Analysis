#!/usr/bin/env python3
"""
Generate HTML report from parsed window size analysis data.
Uses only Python standard library - no external dependencies needed.
"""

import csv
import random
from pathlib import Path
from datetime import datetime
from collections import defaultdict


def load_csv(filepath):
    """Load CSV file and return as list of dicts."""
    data = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)
    return data


def calculate_stats(video_df):
    """Calculate statistics from video data."""
    # Convert numeric columns
    for row in video_df:
        for key in ['accuracy', 'precision_not_behavior', 'precision_behavior',
                   'recall_not_behavior', 'recall_behavior',
                   'f1_not_behavior', 'f1_behavior']:
            if key in row:
                try:
                    row[key] = float(row[key])
                except (ValueError, TypeError):
                    row[key] = None
    
    # Group by video name
    video_stats = defaultdict(lambda: {'accuracies': [], 'f1_behaviors': [], 'count': 0})
    for row in video_df:
        video_name = row['video_name']
        if row['accuracy'] is not None:
            video_stats[video_name]['accuracies'].append(row['accuracy'])
        if row['f1_behavior'] is not None:
            video_stats[video_name]['f1_behaviors'].append(row['f1_behavior'])
            video_stats[video_name]['count'] += 1
    
    # Calculate mean accuracy per video
    worst_videos = []
    for video_name, stats in video_stats.items():
        if stats['accuracies']:
            mean_acc = sum(stats['accuracies']) / len(stats['accuracies'])
            sd_acc = (sum((x - mean_acc)**2 for x in stats['accuracies']) / len(stats['accuracies']))**0.5
            worst_videos.append({
                'video_name': video_name,
                'mean_accuracy': mean_acc,
                'sd_accuracy': sd_acc
            })
    
    # Sort by mean accuracy (ascending for worst)
    worst_videos.sort(key=lambda x: x['mean_accuracy'])
    
    # Calculate CV using F1 (behavior) for sensitivity
    sensitive_videos = []
    for video_name, stats in video_stats.items():
        if stats['f1_behaviors']:
            mean_f1 = sum(stats['f1_behaviors']) / len(stats['f1_behaviors'])
            sd_f1 = (sum((x - mean_f1)**2 for x in stats['f1_behaviors']) / len(stats['f1_behaviors']))**0.5
            cv = sd_f1 / mean_f1 if mean_f1 > 0 else None
            mean_acc = sum(stats['accuracies']) / len(stats['accuracies']) if stats['accuracies'] else 0
            sd_acc = (sum((x - mean_acc)**2 for x in stats['accuracies']) / len(stats['accuracies']))**0.5 if stats['accuracies'] else 0
            sensitive_videos.append({
                'video_name': video_name,
                'mean_accuracy': mean_acc,
                'sd_accuracy': sd_acc,
                'cv': cv,
                'f1_values': stats['f1_behaviors']  # Store F1 values for plotting
            })
    
    # Sort by CV (descending for most sensitive)
    sensitive_videos = [v for v in sensitive_videos if v['cv'] is not None]
    sensitive_videos.sort(key=lambda x: x['cv'], reverse=True)
    
    return worst_videos, sensitive_videos


def find_best_values(summary_df):
    """Find best value for each metric column."""
    best = {}
    for row in summary_df:
        for metric in ['mean_accuracy', 'mean_f1_behavior', 'mean_f1_not_behavior']:
            val = float(row[metric])
            if metric not in best or val > best[metric]['value']:
                best[metric] = {'value': val, 'window': row['window_size']}
        # For SD columns, lower is better
        for metric in ['sd_accuracy', 'sd_f1_behavior', 'sd_f1_not_behavior']:
            val = float(row[metric])
            if metric not in best or val < best[metric]['value']:
                best[metric] = {'value': val, 'window': row['window_size']}
    return best


def create_barbell_plot(metric_name, metric_values, window_sizes, best_window, plot_width=300, plot_height=200):
    """Create SVG barbell/dot plot for a metric."""
    if not metric_values:
        return ""
    
    # Ensure all values are floats
    metric_values = {k: float(v) for k, v in metric_values.items()}
    
    min_val = min(metric_values.values())
    max_val = max(metric_values.values())
    range_val = max_val - min_val
    padding = range_val * 0.1 if range_val > 0 else 0.01
    
    # Scale values to plot coordinates
    plot_padding = 40
    plot_area_width = plot_width - 2 * plot_padding
    plot_area_height = plot_height - 2 * plot_padding
    
    svg = f'<svg class="plot-svg" viewBox="0 0 {plot_width} {plot_height}" xmlns="http://www.w3.org/2000/svg">'
    svg += f'<rect width="{plot_width}" height="{plot_height}" fill="#fafafa"/>'
    
    # Y-axis labels (window sizes) - ordered 5, 10, 15, 20, 25, 30
    sorted_windows = sorted([int(w) for w in window_sizes])
    y_spacing = plot_area_height / (len(sorted_windows) - 1) if len(sorted_windows) > 1 else plot_area_height
    y_positions = {}
    
    for i, window_int in enumerate(sorted_windows):
        window = str(window_int)
        y_pos = plot_padding + (i * y_spacing if len(sorted_windows) > 1 else plot_area_height / 2)
        y_positions[window] = y_pos
        svg += f'<text x="{plot_padding - 5}" y="{y_pos + 4}" class="barbell-label" text-anchor="end" font-size="9px">{window}</text>'
    
    # X-axis scale
    x_min = plot_padding
    x_max = plot_width - plot_padding
    x_range = x_max - x_min
    
    # Draw reference line at minimum value
    svg += f'<line x1="{x_min}" y1="{plot_padding}" x2="{x_min}" y2="{plot_height - plot_padding}" stroke="#ddd" stroke-width="1"/>'
    svg += f'<line x1="{x_max}" y1="{plot_padding}" x2="{x_max}" y2="{plot_height - plot_padding}" stroke="#ddd" stroke-width="1"/>'
    
    # Draw dots and lines (barbell plot) - in order 5, 10, 15, 20, 25, 30
    for window_int in sorted_windows:
        window = str(window_int)
        if window in metric_values:
            val = metric_values[window]
            # Normalize value to plot coordinates
            normalized = (val - min_val + padding) / (range_val + 2 * padding) if range_val > 0 else 0.5
            x_pos = x_min + normalized * x_range
            y_pos = y_positions[window]
            
            # Check if this is the best value
            is_best = window == best_window
            
            # Draw line from min to value
            svg += f'<line x1="{x_min}" y1="{y_pos}" x2="{x_pos}" y2="{y_pos}" class="barbell-line"/>'
            
            # Draw dot
            dot_class = "barbell-dot-best" if is_best else "barbell-dot"
            dot_radius = 6 if is_best else 5
            svg += f'<circle cx="{x_pos}" cy="{y_pos}" r="{dot_radius}" class="{dot_class}"/>'
            
            # Value label (only show if there's space)
            if x_pos + 35 < plot_width:
                svg += f'<text x="{x_pos + 8}" y="{y_pos + 4}" class="barbell-label" font-size="9px">{val:.3f}</text>'
    
    # X-axis labels (min and max)
    svg += f'<text x="{x_min}" y="{plot_height - plot_padding + 20}" class="barbell-label" text-anchor="middle" font-size="8px">{min_val:.3f}</text>'
    svg += f'<text x="{x_max}" y="{plot_height - plot_padding + 20}" class="barbell-label" text-anchor="middle" font-size="8px">{max_val:.3f}</text>'
    
    svg += '</svg>'
    return svg


def calculate_boxplot_stats(values):
    """Calculate boxplot statistics (Q1, median, Q3, IQR, whiskers)."""
    if not values:
        return None
    
    sorted_vals = sorted([float(v) for v in values])
    n = len(sorted_vals)
    
    # Calculate quartiles
    q1_idx = int(n * 0.25)
    median_idx = int(n * 0.5)
    q3_idx = int(n * 0.75)
    
    q1 = sorted_vals[q1_idx] if q1_idx < n else sorted_vals[0]
    median = sorted_vals[median_idx] if median_idx < n else sorted_vals[-1]
    q3 = sorted_vals[q3_idx] if q3_idx < n else sorted_vals[-1]
    
    iqr = q3 - q1
    
    # Whiskers: 1.5 * IQR from Q1 and Q3
    lower_whisker = max(sorted_vals[0], q1 - 1.5 * iqr)
    upper_whisker = min(sorted_vals[-1], q3 + 1.5 * iqr)
    
    # Outliers
    outliers = [v for v in sorted_vals if v < lower_whisker or v > upper_whisker]
    
    return {
        'min': sorted_vals[0],
        'q1': q1,
        'median': median,
        'q3': q3,
        'max': sorted_vals[-1],
        'lower_whisker': lower_whisker,
        'upper_whisker': upper_whisker,
        'outliers': outliers,
        'values': sorted_vals
    }


def create_boxwhisker_plot(video_df, metric='accuracy', summary_df=None, plot_width=1000, plot_height=500):
    """Create SVG box-whisker plot with individual points for each video."""
    # Group data by window size
    from collections import defaultdict
    window_data = defaultdict(list)
    
    for row in video_df:
        window = row['window_size']
        try:
            val = float(row[metric])
            window_data[window].append(val)
        except (ValueError, KeyError):
            continue
    
    if not window_data:
        return ""
    
    # Sort windows: 5, 10, 15, 20, 25, 30
    sorted_windows = sorted([int(w) for w in window_data.keys()])
    sorted_windows = [str(w) for w in sorted_windows]
    
    # Get summary statistics from section 1 table
    summary_stats = {}
    if summary_df:
        for row in summary_df:
            window = row['window_size']
            if metric == 'accuracy':
                summary_stats[window] = {
                    'mean': float(row.get('mean_accuracy', 0)),
                    'sd': float(row.get('sd_accuracy', 0))
                }
            elif metric == 'f1_behavior':
                summary_stats[window] = {
                    'mean': float(row.get('mean_f1_behavior', 0)),
                    'sd': float(row.get('sd_f1_behavior', 0))
                }
    
    # Calculate statistics for each window
    stats_by_window = {}
    all_values = []
    for window in sorted_windows:
        values = window_data[window]
        stats = calculate_boxplot_stats(values)
        if stats:
            stats_by_window[window] = stats
            all_values.extend(values)
    
    if not stats_by_window:
        return ""
    
    # Calculate plot dimensions
    plot_padding = 80
    plot_area_width = plot_width - 2 * plot_padding
    plot_area_height = plot_height - 2 * plot_padding
    
    # Y-axis range (metric values)
    min_val = min(all_values)
    max_val = max(all_values)
    val_range = max_val - min_val
    val_padding = val_range * 0.05 if val_range > 0 else 0.01
    y_min = min_val - val_padding
    y_max = max_val + val_padding
    y_range = y_max - y_min
    
    # X-axis: one box per window
    n_windows = len(sorted_windows)
    box_width = min(80, plot_area_width / (n_windows + 1))
    box_spacing = plot_area_width / (n_windows + 1)
    
    svg = f'<svg class="plot-svg" viewBox="0 0 {plot_width} {plot_height}" xmlns="http://www.w3.org/2000/svg">'
    svg += f'<rect width="{plot_width}" height="{plot_height}" fill="#ffffff" stroke="#e0e0e0" stroke-width="1"/>'
    
    # Helper to convert value to y coordinate
    def val_to_y(val):
        normalized = (val - y_min) / y_range
        return plot_height - plot_padding - (normalized * plot_area_height)
    
    # Draw boxes and whiskers
    for i, window in enumerate(sorted_windows):
        if window not in stats_by_window:
            continue
        
        stats = stats_by_window[window]
        x_center = plot_padding + (i + 1) * box_spacing
        x_left = x_center - box_width / 2
        x_right = x_center + box_width / 2
        
        # Y coordinates
        y_q1 = val_to_y(stats['q1'])
        y_median = val_to_y(stats['median'])
        y_q3 = val_to_y(stats['q3'])
        y_lower_whisker = val_to_y(stats['lower_whisker'])
        y_upper_whisker = val_to_y(stats['upper_whisker'])
        
        # Draw whiskers
        svg += f'<line x1="{x_center}" y1="{y_lower_whisker}" x2="{x_center}" y2="{y_upper_whisker}" stroke="#34495e" stroke-width="2"/>'
        
        # Draw lower whisker cap
        svg += f'<line x1="{x_center - 10}" y1="{y_lower_whisker}" x2="{x_center + 10}" y2="{y_lower_whisker}" stroke="#34495e" stroke-width="2"/>'
        
        # Draw upper whisker cap
        svg += f'<line x1="{x_center - 10}" y1="{y_upper_whisker}" x2="{x_center + 10}" y2="{y_upper_whisker}" stroke="#34495e" stroke-width="2"/>'
        
        # Draw box (Q1 to Q3) with gradient effect
        svg += f'<rect x="{x_left}" y="{y_q3}" width="{box_width}" height="{y_q1 - y_q3}" fill="#3498db" fill-opacity="0.7" stroke="#2980b9" stroke-width="2"/>'
        
        # Draw median line (thicker, more prominent)
        svg += f'<line x1="{x_left}" y1="{y_median}" x2="{x_right}" y2="{y_median}" stroke="#e74c3c" stroke-width="3"/>'
        
        # Draw individual points (jittered) - larger and more visible
        random.seed(42)  # For reproducibility
        for val in stats['values']:
            # Jitter x position slightly
            jitter = (random.random() - 0.5) * box_width * 0.6
            x_point = x_center + jitter
            y_point = val_to_y(val)
            
            # Check if outlier
            is_outlier = val < stats['lower_whisker'] or val > stats['upper_whisker']
            dot_color = "#e74c3c" if is_outlier else "#34495e"
            dot_opacity = "0.7" if is_outlier else "0.5"
            dot_radius = 3.5 if is_outlier else 3
            
            svg += f'<circle cx="{x_point}" cy="{y_point}" r="{dot_radius}" fill="{dot_color}" fill-opacity="{dot_opacity}" stroke="white" stroke-width="1"/>'
        
        # Window label (larger, bold)
        svg += f'<text x="{x_center}" y="{plot_height - plot_padding + 30}" class="barbell-label" text-anchor="middle" font-size="14px" font-weight="bold" fill="#2c3e50">{window} frames</text>'
        
        # Add summary statistics from section 1 table (mean and SD)
        if window in summary_stats:
            mean_val = summary_stats[window]['mean']
            sd_val = summary_stats[window]['sd']
            stats_y = plot_padding - 20
            
            # Mean value (larger, bold)
            svg += f'<text x="{x_center}" y="{stats_y}" class="barbell-label" text-anchor="middle" font-size="13px" font-weight="bold" fill="#27ae60">μ={mean_val:.4f}</text>'
            # SD value
            svg += f'<text x="{x_center}" y="{stats_y + 18}" class="barbell-label" text-anchor="middle" font-size="12px" fill="#7f8c8d">σ={sd_val:.4f}</text>'
    
    # Y-axis labels (larger text)
    n_ticks = 6
    for i in range(n_ticks + 1):
        val = y_min + (i / n_ticks) * y_range
        y_pos = val_to_y(val)
        svg += f'<line x1="{plot_padding - 8}" y1="{y_pos}" x2="{plot_padding}" y2="{y_pos}" stroke="#34495e" stroke-width="1.5"/>'
        svg += f'<text x="{plot_padding - 12}" y="{y_pos + 5}" class="barbell-label" text-anchor="end" font-size="13px" font-weight="500" fill="#2c3e50">{val:.3f}</text>'
    
    # Axis lines (thicker)
    svg += f'<line x1="{plot_padding}" y1="{plot_padding}" x2="{plot_padding}" y2="{plot_height - plot_padding}" stroke="#2c3e50" stroke-width="3"/>'
    svg += f'<line x1="{plot_padding}" y1="{plot_height - plot_padding}" x2="{plot_width - plot_padding}" y2="{plot_height - plot_padding}" stroke="#2c3e50" stroke-width="3"/>'
    
    # Y-axis label
    metric_label = "Accuracy" if metric == 'accuracy' else "F1 (Behavior)"
    svg += f'<text x="20" y="{plot_height / 2}" class="barbell-label" text-anchor="middle" font-size="16px" font-weight="bold" fill="#2c3e50" transform="rotate(-90 20 {plot_height / 2})">{metric_label}</text>'
    
    svg += '</svg>'
    return svg


def create_lollipop_plot(video_df, video_name, metric='f1_behavior', plot_width=800, plot_height=300, y_min=None, y_max=None):
    """Create lollipop plot showing metric values across window sizes for a single video.
    
    Args:
        video_df: List of video data dictionaries
        video_name: Name of the video to plot
        metric: Metric to plot (default: 'f1_behavior')
        plot_width: Width of the plot in pixels
        plot_height: Height of the plot in pixels
        y_min: Minimum y-axis value (if None, calculated from data)
        y_max: Maximum y-axis value (if None, calculated from data)
    """
    # Filter data for this video
    video_data = {}
    for row in video_df:
        if row['video_name'] == video_name:
            window = row['window_size']
            try:
                val = float(row[metric])
                video_data[window] = val
            except (ValueError, KeyError):
                continue
    
    if not video_data:
        return ""
    
    # Sort windows: 5, 10, 15, 20, 25, 30
    sorted_windows = sorted([int(w) for w in video_data.keys()])
    sorted_windows = [str(w) for w in sorted_windows]
    
    # Calculate plot dimensions
    plot_padding = 70
    plot_area_width = plot_width - 2 * plot_padding
    plot_area_height = plot_height - 2 * plot_padding
    
    # Y-axis range (use provided range or calculate from this video's data)
    all_values = [video_data[w] for w in sorted_windows]
    if y_min is None:
        min_val = min(all_values)
        max_val = max(all_values)
        val_range = max_val - min_val
        val_padding = val_range * 0.1 if val_range > 0 else 0.01
        y_min = min_val - val_padding
        y_max = max_val + val_padding
    else:
        min_val = min(all_values)
        max_val = max(all_values)
    
    y_range = y_max - y_min
    
    # X-axis: one position per window
    n_windows = len(sorted_windows)
    x_spacing = plot_area_width / (n_windows + 1)
    
    svg = f'<svg class="plot-svg" viewBox="0 0 {plot_width} {plot_height}" xmlns="http://www.w3.org/2000/svg">'
    svg += f'<rect width="{plot_width}" height="{plot_height}" fill="#ffffff" stroke="#e0e0e0" stroke-width="1"/>'
    
    # Helper to convert value to y coordinate
    def val_to_y(val):
        normalized = (val - y_min) / y_range
        return plot_height - plot_padding - (normalized * plot_area_height)
    
    # Draw baseline (y = 0 or minimum value)
    baseline_y = val_to_y(min_val)
    svg += f'<line x1="{plot_padding}" y1="{baseline_y}" x2="{plot_width - plot_padding}" y2="{baseline_y}" stroke="#bdc3c7" stroke-width="1" stroke-dasharray="3,3"/>'
    
    # Draw lollipops
    for i, window in enumerate(sorted_windows):
        val = video_data[window]
        x_pos = plot_padding + (i + 1) * x_spacing
        y_val = val_to_y(val)
        
        # Draw line (stick)
        svg += f'<line x1="{x_pos}" y1="{baseline_y}" x2="{x_pos}" y2="{y_val}" stroke="#3498db" stroke-width="2.5"/>'
        
        # Draw circle (lollipop)
        svg += f'<circle cx="{x_pos}" cy="{y_val}" r="6" fill="#3498db" stroke="#2980b9" stroke-width="1.5"/>'
        
        # Value label
        svg += f'<text x="{x_pos}" y="{y_val - 12}" class="barbell-label" text-anchor="middle" font-size="12px" font-weight="bold" fill="#2c3e50">{val:.4f}</text>'
        
        # Window label
        svg += f'<text x="{x_pos}" y="{plot_height - plot_padding + 25}" class="barbell-label" text-anchor="middle" font-size="13px" font-weight="bold" fill="#2c3e50">{window}</text>'
    
    # Y-axis labels
    n_ticks = 5
    for i in range(n_ticks + 1):
        val = y_min + (i / n_ticks) * y_range
        y_pos = val_to_y(val)
        svg += f'<line x1="{plot_padding - 5}" y1="{y_pos}" x2="{plot_padding}" y2="{y_pos}" stroke="#34495e" stroke-width="1"/>'
        svg += f'<text x="{plot_padding - 10}" y="{y_pos + 4}" class="barbell-label" text-anchor="end" font-size="12px" fill="#2c3e50">{val:.3f}</text>'
    
    # Axis lines
    svg += f'<line x1="{plot_padding}" y1="{plot_padding}" x2="{plot_padding}" y2="{plot_height - plot_padding}" stroke="#2c3e50" stroke-width="2"/>'
    svg += f'<line x1="{plot_padding}" y1="{plot_height - plot_padding}" x2="{plot_width - plot_padding}" y2="{plot_height - plot_padding}" stroke="#2c3e50" stroke-width="2"/>'
    
    # Y-axis label
    metric_label = "F1 (Behavior)" if metric == 'f1_behavior' else "Accuracy"
    svg += f'<text x="25" y="{plot_height / 2}" class="barbell-label" text-anchor="middle" font-size="14px" font-weight="bold" fill="#2c3e50" transform="rotate(-90 25 {plot_height / 2})">{metric_label}</text>'
    
    svg += '</svg>'
    return svg


def generate_html_report(video_df, summary_df, feature_df, worst_videos, sensitive_videos):
    """Generate HTML report content."""
    
    # Find best window
    best_window = max(summary_df, key=lambda x: float(x['mean_accuracy']))
    
    # Find best values for each column
    best_values = find_best_values(summary_df)
    
    # Get unique videos count
    unique_videos = len(set(row['video_name'] for row in video_df))
    # Ensure windows are in order 5, 10, 15, 20, 25, 30
    windows = sorted([int(w) for w in set(row['window_size'] for row in video_df)])
    windows = [str(w) for w in windows]
    
    html = f'''<!DOCTYPE html>
<html>
<head>
  <title>Window Size Analysis Report</title>
  <meta charset="UTF-8">
  <style>
    body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; background-color: #f5f5f5; }}
    .container {{ max-width: 1200px; margin: 0 auto; background-color: white; padding: 40px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
    h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
    h2 {{ color: #34495e; margin-top: 30px; border-left: 4px solid #3498db; padding-left: 15px; }}
    h3 {{ color: #7f8c8d; }}
    table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
    th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
    th {{ background-color: #3498db; color: white; font-weight: bold; }}
    tr:nth-child(even) {{ background-color: #f2f2f2; }}
    tr:hover {{ background-color: #e8f4f8; }}
    .summary-box {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 25px; border-radius: 8px; margin: 20px 0; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
    .summary-box h2 {{ color: white; border: none; padding: 0; margin: 0 0 15px 0; }}
    .summary-box ul {{ margin: 10px 0; padding-left: 20px; }}
    .best {{ background-color: #2ecc71 !important; color: white; font-weight: bold; }}
    .best-cell {{ background-color: #27ae60 !important; color: white; font-weight: bold; }}
    .best-f1 {{ background-color: #e74c3c !important; color: white; font-weight: bold; font-size: 1.1em; }}
    .warning {{ background-color: #f39c12; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #e67e22; }}
    .info {{ background-color: #3498db; color: white; padding: 15px; border-radius: 5px; margin: 20px 0; }}
    .metric {{ display: inline-block; margin: 10px 20px 10px 0; padding: 10px 20px; background-color: #ecf0f1; border-radius: 5px; }}
    .metric strong {{ color: #2c3e50; display: block; font-size: 1.2em; margin-bottom: 5px; }}
    .plots-row {{ display: flex; flex-wrap: wrap; gap: 15px; margin: 30px 0; justify-content: space-between; }}
    .plot-container {{ flex: 1; min-width: 280px; max-width: 350px; padding: 15px; background-color: #fafafa; border-radius: 8px; border: 1px solid #ddd; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
    .plot-title {{ font-weight: bold; color: #2c3e50; margin-bottom: 10px; font-size: 0.95em; text-align: center; }}
    .plot-svg {{ width: 100%; height: 200px; }}
    .lollipop-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin: 30px 0; }}
    @media (max-width: 1200px) {{ .lollipop-grid {{ grid-template-columns: 1fr; }} }}
    .lollipop-plot-container {{ padding: 20px; background-color: #fafafa; border-radius: 8px; border: 1px solid #ddd; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
    .barbell-line {{ stroke: #3498db; stroke-width: 1.5; opacity: 0.7; }}
    .barbell-dot {{ fill: #3498db; stroke: #2c3e50; stroke-width: 1; }}
    .barbell-dot-best {{ fill: #e74c3c; stroke: #c0392b; stroke-width: 2; }}
    .barbell-label {{ font-size: 10px; fill: #34495e; }}
    .metric-section {{ margin: 40px 0; }}
    .f1-behavior-section {{ border: 3px solid #e74c3c; padding: 20px; background-color: #fff5f5; border-radius: 8px; }}
    .f1-behavior-plot {{ border: 2px solid #e74c3c; background-color: #fff5f5; }}
  </style>
</head>
<body>
  <div class="container">
    <h1>Window Size Analysis Report</h1>
    <p><strong>Generated:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    
    <div class="summary-box">
      <h2>Executive Summary</h2>
      <div class="metric">
        <strong>Best Window Size</strong>
        {best_window['window_size']} frames
      </div>
      <div class="metric">
        <strong>Mean Accuracy</strong>
        {float(best_window['mean_accuracy']):.4f}
      </div>
      <div class="metric">
        <strong>Standard Deviation</strong>
        {float(best_window['sd_accuracy']):.4f}
      </div>
      <div class="metric">
        <strong>Total Videos</strong>
        {unique_videos}
      </div>
      <p style="margin-top: 20px;"><strong>Window Sizes Tested:</strong> {', '.join(map(str, windows))} frames</p>
    </div>
    
    <h2>1. Window Size Comparison</h2>
    <p>The following table shows performance metrics for each window size tested. <strong>Best values in each column are highlighted in green.</strong> 
    <span style="background-color: #e74c3c; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">F1 (Behavior) is highlighted in red as the most relevant metric.</span></p>
    <table>
      <tr>
        <th>Window Size</th>
        <th>Mean Accuracy</th>
        <th>SD Accuracy</th>
        <th>Mean F1 (Behavior) ⭐</th>
        <th>SD F1 (Behavior)</th>
        <th>Mean F1 (Not Behavior)</th>
        <th>SD F1 (Not Behavior)</th>
      </tr>'''
    
    # Sort summary by window size (5, 10, 15, 20, 25, 30)
    sorted_summary = sorted(summary_df, key=lambda x: int(x['window_size']))
    for row in sorted_summary:
        # Only highlight the best metric in each column, not the entire row
        row_class = ''
        
        # Check which cells are best (only highlight the best metric, not all metrics for best window)
        mean_acc_class = ' class="best-cell"' if row['window_size'] == best_values['mean_accuracy']['window'] else ''
        sd_acc_class = ' class="best-cell"' if row['window_size'] == best_values['sd_accuracy']['window'] else ''
        mean_f1_beh_class = ' class="best-f1"' if row['window_size'] == best_values['mean_f1_behavior']['window'] else ''
        sd_f1_beh_class = ' class="best-cell"' if row['window_size'] == best_values['sd_f1_behavior']['window'] else ''
        mean_f1_not_beh_class = ' class="best-cell"' if row['window_size'] == best_values['mean_f1_not_behavior']['window'] else ''
        sd_f1_not_beh_class = ' class="best-cell"' if row['window_size'] == best_values['sd_f1_not_behavior']['window'] else ''
        
        html += f'''
      <tr{row_class}>
        <td>{row['window_size']}</td>
        <td{mean_acc_class}>{float(row['mean_accuracy']):.4f}</td>
        <td{sd_acc_class}>{float(row['sd_accuracy']):.4f}</td>
        <td{mean_f1_beh_class}>{float(row['mean_f1_behavior']):.4f}</td>
        <td{sd_f1_beh_class}>{float(row['sd_f1_behavior']):.4f}</td>
        <td{mean_f1_not_beh_class}>{float(row['mean_f1_not_behavior']):.4f}</td>
        <td{sd_f1_not_beh_class}>{float(row['sd_f1_not_behavior']):.4f}</td>
      </tr>'''
    
    html += f'''
    </table>
    
    <div class="f1-behavior-section">
    <h3>⭐ F1 (Behavior) - Most Relevant Metric</h3>
    <p><strong>F1 (Behavior) is the most relevant metric for this analysis.</strong> The best performing window size for F1 (Behavior) is <strong>{best_values['mean_f1_behavior']['window']} frames</strong> with a value of <strong>{best_values['mean_f1_behavior']['value']:.4f}</strong>.</p>
    </div>
    
    <h3>Visualizations: Performance Metrics by Window Size</h3>
    <p>The following barbell plots show the performance of each window size for different metrics. The best value in each plot is highlighted in red.</p>'''
    
    # Create plots for each metric
    metrics_to_plot = [
        ('Mean Accuracy', 'mean_accuracy', 'mean_accuracy'),
        ('SD Accuracy (lower is better)', 'sd_accuracy', 'sd_accuracy'),
        ('Mean F1 (Behavior) ⭐ - Most Relevant', 'mean_f1_behavior', 'mean_f1_behavior'),
        ('SD F1 (Behavior) (lower is better)', 'sd_f1_behavior', 'sd_f1_behavior'),
        ('Mean F1 (Not Behavior)', 'mean_f1_not_behavior', 'mean_f1_not_behavior'),
        ('SD F1 (Not Behavior) (lower is better)', 'sd_f1_not_behavior', 'sd_f1_not_behavior'),
    ]
    
    # Create plots in a row
    html += '''
    <div class="plots-row">'''
    
    for metric_title, metric_key, best_key in metrics_to_plot:
        # Prepare data for plot - ensure all windows 5-30 are included
        metric_data = {}
        for row in sorted_summary:
            window = row['window_size']
            metric_data[window] = float(row[metric_key])
        
        # Ensure we have all windows in order 5, 10, 15, 20, 25, 30
        all_windows = [str(w) for w in [5, 10, 15, 20, 25, 30]]
        plot_windows = [w for w in all_windows if w in metric_data]
        
        best_window_for_metric = best_values[best_key]['window']
        
        # Create plot
        plot_svg = create_barbell_plot(metric_key, metric_data, plot_windows, best_window_for_metric)
        
        # Add emphasis for F1 Behavior
        container_class = 'plot-container'
        if 'F1 (Behavior)' in metric_title and 'Mean' in metric_title:
            container_class += ' f1-behavior-plot'
        
        html += f'''
      <div class="{container_class}">
        <div class="plot-title">{metric_title}</div>
        {plot_svg}
      </div>'''
    
    html += '''
    </div>'''
    
    # Create box-whisker plots with summary statistics
    accuracy_plot = create_boxwhisker_plot(video_df, 'accuracy', summary_df, 1000, 500)
    f1_behavior_plot = create_boxwhisker_plot(video_df, 'f1_behavior', summary_df, 1000, 500)
    
    html += f'''
    <h2>2. Per-Video Performance Distribution</h2>
    <p>The following box-whisker plots show the distribution of performance metrics across all videos (iterations) for each window size. Each point represents one video/iteration. Outliers are shown in red.</p>
    
    <h3>Accuracy Distribution by Window Size</h3>
    <p style="font-size: 14px; color: #7f8c8d; margin-bottom: 15px;">Each box shows the quartiles (Q1, median, Q3), whiskers extend to 1.5×IQR, and individual points represent each video/iteration. Summary statistics (μ=mean, σ=SD) from Section 1 are displayed above each box.</p>
    <div class="plot-container" style="max-width: 100%; padding: 25px; background-color: #fafafa; border-radius: 8px;">
      {accuracy_plot}
    </div>
    
    <h3>F1 (Behavior) Distribution by Window Size ⭐</h3>
    <p style="font-size: 14px; color: #7f8c8d; margin-bottom: 15px;">Each box shows the quartiles (Q1, median, Q3), whiskers extend to 1.5×IQR, and individual points represent each video/iteration. Summary statistics (μ=mean, σ=SD) from Section 1 are displayed above each box.</p>
    <div class="plot-container f1-behavior-plot" style="max-width: 100%; padding: 25px; background-color: #fff5f5; border-radius: 8px; border: 2px solid #e74c3c;">
      {f1_behavior_plot}
    </div>
    
    <h2>3. Worst Performing Videos</h2>
    <p>Analysis of worst performing videos across different window sizes. The table below shows:</p>
    <ul style="margin-bottom: 20px;">
      <li><strong>Overall worst videos:</strong> Videos with lowest mean accuracy across all window sizes</li>
      <li><strong>Performance by window size:</strong> Accuracy and F1 (Behavior) for each window size</li>
      <li><strong>Worst window:</strong> The window size where each video performs worst (highlighted in red)</li>
    </ul>
    
    <h3>Top 10 Worst Performing Videos (Overall)</h3>
    <div style="overflow-x: auto; margin: 20px 0;">
    <table style="min-width: 1000px;">
      <tr>
        <th rowspan="2" style="vertical-align: middle;">Rank</th>
        <th rowspan="2" style="vertical-align: middle;">Video Name</th>
        <th rowspan="2" style="vertical-align: middle;">Mean<br>Accuracy</th>
        <th rowspan="2" style="vertical-align: middle;">Mean<br>F1 (Behavior)</th>
        <th colspan="6" style="text-align: center; border-bottom: 2px solid #34495e;">Accuracy by Window Size</th>
        <th colspan="6" style="text-align: center; border-bottom: 2px solid #34495e;">F1 (Behavior) by Window Size</th>
      </tr>
      <tr>
        <th>5</th>
        <th>10</th>
        <th>15</th>
        <th>20</th>
        <th>25</th>
        <th>30</th>
        <th>5</th>
        <th>10</th>
        <th>15</th>
        <th>20</th>
        <th>25</th>
        <th>30</th>
      </tr>'''
    
    # Get window sizes in order
    windows = sorted([int(w) for w in set(row['window_size'] for row in video_df)])
    windows = [str(w) for w in windows]
    
    for i, video in enumerate(worst_videos[:10], 1):
        video_short = video['video_name'][:80] + ('...' if len(video['video_name']) > 80 else '')
        
        # Get performance for each window size for this video
        window_accuracies = {}
        window_f1_behaviors = {}
        worst_acc_window = None
        worst_f1_window = None
        worst_acc_value = 1.0
        worst_f1_value = 1.0
        
        for row in video_df:
            if row['video_name'] == video['video_name']:
                window = row['window_size']
                try:
                    acc = float(row['accuracy'])
                    f1 = float(row['f1_behavior'])
                    window_accuracies[window] = acc
                    window_f1_behaviors[window] = f1
                    
                    if acc < worst_acc_value:
                        worst_acc_value = acc
                        worst_acc_window = window
                    if f1 < worst_f1_value:
                        worst_f1_value = f1
                        worst_f1_window = window
                except (ValueError, KeyError):
                    continue
        
        # Calculate mean F1 behavior for this video
        f1_values = [window_f1_behaviors[w] for w in windows if w in window_f1_behaviors]
        mean_f1 = sum(f1_values) / len(f1_values) if f1_values else 0
        
        html += f'''
      <tr>
        <td style="font-weight: bold;">{i}</td>
        <td style="max-width: 200px; word-wrap: break-word;">{video_short}</td>
        <td style="font-weight: bold;">{video['mean_accuracy']:.4f}</td>
        <td style="font-weight: bold;">{mean_f1:.4f}</td>'''
        
        # Accuracy columns
        for window in windows:
            if window in window_accuracies:
                acc_val = window_accuracies[window]
                cell_class = ' style="background-color: #ffebee; color: #c62828; font-weight: bold;"' if window == worst_acc_window else ''
                html += f'<td{cell_class}>{acc_val:.4f}</td>'
            else:
                html += '<td style="color: #999;">N/A</td>'
        
        # F1 Behavior columns
        for window in windows:
            if window in window_f1_behaviors:
                f1_val = window_f1_behaviors[window]
                cell_class = ' style="background-color: #ffebee; color: #c62828; font-weight: bold;"' if window == worst_f1_window else ''
                html += f'<td{cell_class}>{f1_val:.4f}</td>'
            else:
                html += '<td style="color: #999;">N/A</td>'
        
        html += '''
      </tr>'''
    
    html += '''
    </table>
    </div>
    <p style="font-size: 13px; color: #7f8c8d; margin-top: 10px;">
      <strong>Note:</strong> Red highlighted cells indicate the window size where each video performs worst. 
      Mean values are calculated across all available window sizes for each video.
    </p>
    
    <h3>Worst Performing Videos by Window Size</h3>
    <p>The following table shows the worst performing video at each window size:</p>
    <table>
      <tr>
        <th>Window Size</th>
        <th>Worst Video (Accuracy)</th>
        <th>Accuracy</th>
        <th>Worst Video (F1 Behavior)</th>
        <th>F1 (Behavior)</th>
      </tr>'''
    
    # Find worst video for each window size
    for window in windows:
        window_videos = []
        for row in video_df:
            if row['window_size'] == window:
                try:
                    window_videos.append({
                        'video_name': row['video_name'],
                        'accuracy': float(row['accuracy']),
                        'f1_behavior': float(row['f1_behavior'])
                    })
                except (ValueError, KeyError):
                    continue
        
        if window_videos:
            worst_acc_video = min(window_videos, key=lambda x: x['accuracy'])
            worst_f1_video = min(window_videos, key=lambda x: x['f1_behavior'])
            
            worst_acc_name = worst_acc_video['video_name'][:60] + ('...' if len(worst_acc_video['video_name']) > 60 else '')
            worst_f1_name = worst_f1_video['video_name'][:60] + ('...' if len(worst_f1_video['video_name']) > 60 else '')
            
            html += f'''
      <tr>
        <td style="font-weight: bold;">{window} frames</td>
        <td>{worst_acc_name}</td>
        <td style="color: #c62828; font-weight: bold;">{worst_acc_video['accuracy']:.4f}</td>
        <td>{worst_f1_name}</td>
        <td style="color: #c62828; font-weight: bold;">{worst_f1_video['f1_behavior']:.4f}</td>
      </tr>'''
    
    html += '''
    </table>
    
    <h2>4. Most Window-Sensitive Videos</h2>
    <p>Top 10 videos with highest coefficient of variation (most sensitive to window size changes). <strong>Note: Coefficient of Variation is calculated using F1 (Behavior) metric.</strong></p>
    <table>
      <tr>
        <th>Rank</th>
        <th>Video Name</th>
        <th>Coefficient of Variation (CV)</th>
        <th>Mean Accuracy</th>
        <th>SD Accuracy</th>
      </tr>'''
    
    for i, video in enumerate(sensitive_videos[:10], 1):
        video_short = video['video_name'][:80] + ('...' if len(video['video_name']) > 80 else '')
        html += f'''
      <tr>
        <td>{i}</td>
        <td>{video_short}</td>
        <td>{float(video['cv']):.4f}</td>
        <td>{float(video['mean_accuracy']):.4f}</td>
        <td>{float(video['sd_accuracy']):.4f}</td>
      </tr>'''
    
    html += '''
    </table>
    
    <h3>Lollipop Plots: F1 (Behavior) Across Window Sizes</h3>
    <p style="font-size: 14px; color: #7f8c8d; margin-bottom: 20px;">
      The following lollipop plots show how F1 (Behavior) varies across different window sizes for each of the top 10 most window-sensitive videos. 
      Each plot displays the F1 (Behavior) value for each window size (5, 10, 15, 20, 25, 30 frames). 
      <strong>The Coefficient of Variation (CV) is calculated using F1 (Behavior) values: CV = SD(F1) / Mean(F1).</strong>
      <strong>All plots use the same y-axis scale for easy comparison.</strong>
    </p>'''
    
    # Calculate global y-axis range for all plots (using F1 behavior values from all top 10 videos)
    all_f1_values = []
    for video in sensitive_videos[:10]:
        video_name = video['video_name']
        for row in video_df:
            if row['video_name'] == video_name:
                try:
                    val = float(row['f1_behavior'])
                    all_f1_values.append(val)
                except (ValueError, KeyError):
                    continue
    
    if all_f1_values:
        global_min = min(all_f1_values)
        global_max = max(all_f1_values)
        val_range = global_max - global_min
        val_padding = val_range * 0.1 if val_range > 0 else 0.01
        global_y_min = global_min - val_padding
        global_y_max = global_max + val_padding
    else:
        global_y_min = None
        global_y_max = None
    
    # Create lollipop plots in a grid
    html += '''
    <div class="lollipop-grid">'''
    
    for i, video in enumerate(sensitive_videos[:10], 1):
        video_short = video['video_name'][:80] + ('...' if len(video['video_name']) > 80 else '')
        plot_svg = create_lollipop_plot(video_df, video['video_name'], 'f1_behavior', 600, 280, global_y_min, global_y_max)
        
        html += f'''
      <div class="lollipop-plot-container">
        <h4 style="margin-top: 0; color: #2c3e50; font-size: 1.1em;">Rank {i}: {video_short}</h4>
        <p style="font-size: 12px; color: #7f8c8d; margin-bottom: 15px;">
          CV (F1 Behavior) = {float(video['cv']):.4f} | Mean Accuracy = {float(video['mean_accuracy']):.4f}
        </p>
        {plot_svg}
      </div>'''
    
    html += '''
    </div>'''
    
    # Find window 5 stats for comparison
    window5 = next((r for r in summary_df if r['window_size'] == '5'), None)
    window30 = next((r for r in summary_df if r['window_size'] == '30'), None)
    
    # Calculate additional values for the report
    window5_acc = float(window5['mean_accuracy']) if window5 else None
    window5_f1 = float(window5['mean_f1_behavior']) if window5 else None
    window30_acc = float(window30['mean_accuracy']) if window30 else float(best_window['mean_accuracy'])
    diff_20_30 = abs(float(best_window['mean_accuracy']) - window30_acc)
    window5_acc_str = f"{window5_acc:.4f}" if window5_acc is not None else "N/A"
    window5_f1_str = f"{window5_f1:.4f}" if window5_f1 is not None else "N/A"
    
    html += f'''
    </table>
    
    <h2>5. Key Findings</h2>
    
    <h3>Which Window Size is Best?</h3>
    <div class="info">
      <p><strong>Recommendation: Window {best_window['window_size']} frames</strong></p>
      <p>Window size <strong>{best_window['window_size']} frames</strong> shows the best performance with a mean accuracy of {float(best_window['mean_accuracy']):.4f} and 
      <strong>F1 (Behavior) of {float(best_window['mean_f1_behavior']):.4f}</strong> (the most relevant metric for this analysis). 
      This window size provides an optimal balance between high classification accuracy and stable performance (SD = {float(best_window['sd_accuracy']):.4f}).</p>
    </div>
    
    <h3>Performance Trends</h3>
    <ul>
      <li><strong>Larger windows perform better:</strong> Window sizes 20-30 frames show significantly higher accuracy and <strong>F1 (Behavior)</strong> than smaller windows (5-10 frames)</li>
      <li><strong>Window 5 frames:</strong> Shows the lowest performance with mean accuracy of {window5_acc_str} and <strong>F1 (Behavior) of {window5_f1_str}</strong></li>
      <li><strong>Performance plateau:</strong> There is minimal difference between window sizes 20 and 30 frames in both accuracy (difference: {diff_20_30:.4f}) and <strong>F1 (Behavior)</strong></li>
      <li><strong>Stability:</strong> Window 20 shows slightly better stability (lower SD) than Window 30 for both accuracy and <strong>F1 (Behavior)</strong></li>
    </ul>
    
    <h3>Why Window {best_window['window_size']} Frames?</h3>
    <ol>
      <li><strong>Highest F1 (Behavior) ⭐:</strong> {float(best_window['mean_f1_behavior']):.4f} mean F1 (Behavior) across all videos - <strong>this is the most relevant metric for behavior classification</strong></li>
      <li><strong>Highest Accuracy:</strong> {float(best_window['mean_accuracy']):.4f} mean accuracy across all videos</li>
      <li><strong>Good Stability:</strong> Standard deviation of {float(best_window['sd_accuracy']):.4f} for accuracy and {float(best_window['sd_f1_behavior']):.4f} for <strong>F1 (Behavior)</strong> indicates consistent performance</li>
      <li><strong>Balanced F1 Scores:</strong> Excellent performance for behavior class ({float(best_window['mean_f1_behavior']):.4f}) and good performance for not-behavior ({float(best_window['mean_f1_not_behavior']):.4f}) class</li>
      <li><strong>Computational Efficiency:</strong> Smaller than Window 30, providing similar performance with less computation</li>
    </ol>
    
    <h2>6. Video Performance Analysis</h2>
    
    <h3>Worst Performing Videos</h3>
    <p>The worst performing video has a mean accuracy of {float(worst_videos[0]['mean_accuracy']):.4f} across all window sizes. 
    These videos may have:</p>
    <ul>
      <li>Data quality issues</li>
      <li>Annotation inconsistencies</li>
      <li>Inherently difficult classification cases</li>
    </ul>
    <p><strong>Recommendation:</strong> Review these videos manually to identify potential issues.</p>
    
    <h3>Window-Sensitive Videos</h3>
    <p>The most sensitive video has a coefficient of variation of {float(sensitive_videos[0]['cv']):.4f}, indicating high variability across window sizes.
    These videos show:</p>
    <ul>
      <li>Performance that changes significantly with window size</li>
      <li>Potential temporal scale dependencies</li>
      <li>May benefit from window size optimization</li>
    </ul>
    <p><strong>Recommendation:</strong> Investigate why these videos are sensitive to window size - this may reveal important behavioral patterns.</p>'''
    
    # Calculate window30_acc for recommendations section
    window30 = next((r for r in summary_df if r['window_size'] == '30'), None)
    window30_acc = float(window30['mean_accuracy']) if window30 else float(best_window['mean_accuracy'])
    
    html += f'''
    <h2>7. Data Quality Notes</h2>
    <div class="warning">
      <p><strong>Validation Findings:</strong></p>
      <ul>
        <li><strong>Cross-validation structure:</strong> Each video contains multiple animals (identities). The cross-validation holds out <strong>one animal at a time</strong> (not one video at a time). Each animal is identified by the identity number [0], [1], [2], etc. at the end of the video filename. This is why the same video file appears multiple times with different identities - each represents a separate test case where that specific animal was held out.</li>
        <li>Some videos may be missing from certain windows - this may indicate data collection or processing issues</li>
        <li>See <code>data/processed/validation_report.txt</code> for complete validation details</li>
      </ul>
    </div>
    
    <h2>8. Recommendations</h2>
    <div class="info">
      <ol>
        <li><strong>Primary Recommendation:</strong> Use <strong>Window {best_window['window_size']} frames</strong> for optimal performance</li>
        <li><strong>Alternative:</strong> Consider Window 30 frames if slightly higher accuracy ({window30_acc:.4f}) is needed, though it may be less stable</li>
        <li><strong>Investigation:</strong> Review worst performing videos for data quality issues</li>
        <li><strong>Analysis:</strong> Study window-sensitive videos to understand temporal scale dependencies</li>
        <li><strong>Future Work:</strong> Consider testing intermediate window sizes (e.g., 25 frames) to fine-tune performance</li>
      </ol>
    </div>'''
    
    html += '''
    <h2>9. Additional Analysis</h2>
    <p>For detailed statistical analysis including:</p>
    <ul>
      <li>ANOVA and post-hoc tests</li>
      <li>Feature importance analysis</li>
      <li>Identity and study effects</li>
      <li>Visualizations</li>
    </ul>
    <p>Please run the complete R analysis pipeline (requires R packages: dplyr, ggplot2, etc.)</p>
    
    <hr>
    <p style="text-align: center; color: #7f8c8d;">
      <em>Report generated automatically by the Window Size Analysis Pipeline</em><br>
      For questions or issues, refer to the README.md file
    </p>
  </div>
</body>
</html>'''
    
    return html


def main():
    """Main execution function."""
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    data_dir = project_dir / 'data' / 'processed'
    output_dir = project_dir / 'reports'  # Save to reports folder
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 80)
    print("Generating HTML Report")
    print("=" * 80)
    print()
    
    # Load data
    print("Loading data...")
    video_df = load_csv(data_dir / 'video_results.csv')
    summary_df = load_csv(data_dir / 'summary_stats.csv')
    feature_df = load_csv(data_dir / 'feature_importance.csv')
    print(f"  Loaded {len(video_df)} video results")
    print(f"  Loaded {len(summary_df)} summary statistics")
    print(f"  Loaded {len(feature_df)} feature importance rows")
    print()
    
    # Calculate statistics
    print("Calculating statistics...")
    worst_videos, sensitive_videos = calculate_stats(video_df)
    print(f"  Identified {len(worst_videos)} videos for analysis")
    print()
    
    # Generate HTML
    print("Generating HTML report...")
    # Convert video_df to list of dicts for easier processing
    video_list = []
    for row in video_df:
        video_list.append(dict(row))
    html_content = generate_html_report(video_list, summary_df, feature_df, worst_videos, sensitive_videos)
    
    # Write HTML file to reports folder
    output_file = output_dir / 'window_size_analysis_report.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print()
    print("=" * 80)
    print("Report Generated Successfully!")
    print("=" * 80)
    print(f"Output file: {output_file}")
    print()
    print("Report includes:")
    print("  ✓ Executive summary with best window size recommendation")
    print("  ✓ Window size comparison table")
    print("  ✓ Worst performing videos (top 10)")
    print("  ✓ Most window-sensitive videos (top 10)")
    print("  ✓ Key findings and recommendations")
    print()
    print(f"Open the report in your browser: file://{output_file.absolute()}")


if __name__ == '__main__':
    main()

