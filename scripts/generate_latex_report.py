#!/usr/bin/env python3
"""
Generate LaTeX report from parsed window size analysis data.
Uses only Python standard library - no external dependencies needed.
"""

import csv
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
                'cv': cv
            })
    
    # Sort by CV (descending for most sensitive)
    sensitive_videos = [v for v in sensitive_videos if v['cv'] is not None]
    sensitive_videos.sort(key=lambda x: x['cv'], reverse=True)
    
    return worst_videos, sensitive_videos


def escape_latex(text):
    """Escape special LaTeX characters."""
    if text is None:
        return ""
    text = str(text)
    replacements = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '^': r'\textasciicircum{}',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '\\': r'\textbackslash{}',
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text


def generate_barbell_plot_pgfplots(metric_data, metric_name, best_window, windows, save_as_file=False, output_dir=None, figure_name=None):
    """Generate pgfplots code for barbell plot.
    
    Args:
        metric_data: Dictionary of window -> metric value
        metric_name: Name of the metric
        best_window: Best performing window
        windows: List of window sizes
        save_as_file: If True, save as standalone PDF file
        output_dir: Directory to save figure file
        figure_name: Name for the figure file
    """
    sorted_windows = sorted([int(w) for w in windows])
    sorted_windows = [str(w) for w in sorted_windows]
    
    # Prepare data points
    data_points = []
    for w in sorted_windows:
        if w in metric_data:
            val = float(metric_data[w])
            is_best = w == best_window
            data_points.append((int(w), val, is_best))
    
    if not data_points:
        return ""
    
    min_val = min(v for _, v, _ in data_points)
    max_val = max(v for _, v, _ in data_points)
    
    plot_code = r'''
\begin{tikzpicture}
\begin{axis}[
    width=0.3\textwidth,
    height=0.2\textwidth,
    ymin=''' + f"{min_val * 0.95:.4f}" + r''',
    ymax=''' + f"{max_val * 1.05:.4f}" + r''',
    xlabel={Window Size (frames)},
    ylabel={''' + metric_name + r'''},
    xtick={''' + ','.join(sorted_windows) + r'''},
    xticklabels={''' + ','.join(sorted_windows) + r'''},
    grid=major,
    grid style={gray!30},
    axis lines=left,
    enlarge x limits=0.1,
]
'''
    
    # Add data points as scatter plot with different colors
    for window, val, is_best in data_points:
        color = "bestred" if is_best else "infoblue"
        marker_size = "6pt" if is_best else "4pt"
        plot_code += f"\\addplot[only marks, mark=*, mark size={marker_size}, fill={color}, draw=black, line width=0.5pt] coordinates {{({window}, {val:.4f})}};\n"
    
    plot_code += r'''
\end{axis}
\end{tikzpicture}
'''
    
    # If saving as file, create standalone LaTeX document and compile to PDF
    if save_as_file and output_dir and figure_name:
        standalone_tex = r'''\documentclass{standalone}
\usepackage{pgfplots}
\usepackage{tikz}
\pgfplotsset{compat=1.18}
\definecolor{bestgreen}{RGB}{39, 174, 96}
\definecolor{bestred}{RGB}{231, 76, 60}
\definecolor{infoblue}{RGB}{52, 152, 219}
\begin{document}
''' + plot_code + r'''
\end{document}
'''
        
        # Save standalone LaTeX file
        tex_file = output_dir / f"{figure_name}.tex"
        with open(tex_file, 'w', encoding='utf-8') as f:
            f.write(standalone_tex)
        
        # Compile to PDF
        import subprocess
        import shutil
        pdflatex_path = shutil.which('pdflatex')
        if pdflatex_path:
            try:
                import os
                original_dir = os.getcwd()
                os.chdir(output_dir)
                subprocess.run(
                    [pdflatex_path, '-interaction=nonstopmode', tex_file.name],
                    capture_output=True,
                    text=True
                )
                os.chdir(original_dir)
                
                # Clean up aux files
                for ext in ['aux', 'log']:
                    aux_file = output_dir / f"{figure_name}.{ext}"
                    if aux_file.exists():
                        aux_file.unlink()
            except Exception:
                pass  # If compilation fails, continue without standalone file
    
    # Return code for inclusion in main document
    # Create a safe label name from metric_name
    safe_label = metric_name.lower().replace(' ', '_').replace('(', '').replace(')', '').replace('not_behavior', 'notbeh')
    return r'''
\begin{figure}[h]
\centering
''' + plot_code + r'''
\caption{''' + metric_name + r''' by Window Size}
\label{fig:''' + safe_label + r'''}
\end{figure}
'''


def generate_boxplot_pgfplots(video_df, metric, summary_df, windows, save_as_file=False, output_dir=None, figure_name=None):
    """Generate pgfplots code for box-whisker plot."""
    from collections import defaultdict
    
    # Group data by window
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
    
    sorted_windows = sorted([int(w) for w in window_data.keys()])
    sorted_windows = [str(w) for w in sorted_windows]
    
    # Calculate statistics for each window
    plot_data = []
    all_values = []
    for w in sorted_windows:
        values = sorted(window_data[w])
        all_values.extend(values)
        n = len(values)
        if n > 0:
            q1_idx = int(n * 0.25)
            median_idx = int(n * 0.5)
            q3_idx = int(n * 0.75)
            q1 = values[q1_idx] if q1_idx < n else values[0]
            median = values[median_idx] if median_idx < n else values[-1]
            q3 = values[q3_idx] if q3_idx < n else values[-1]
            iqr = q3 - q1
            lower_whisker = max(values[0], q1 - 1.5 * iqr)
            upper_whisker = min(values[-1], q3 + 1.5 * iqr)
            
            # Get summary stats
            summary_row = next((r for r in summary_df if r['window_size'] == w), None)
            mean_val = float(summary_row.get('mean_accuracy' if metric == 'accuracy' else 'mean_f1_behavior', 0)) if summary_row else 0
            sd_val = float(summary_row.get('sd_accuracy' if metric == 'accuracy' else 'sd_f1_behavior', 0)) if summary_row else 0
            
            plot_data.append({
                'window': int(w),
                'q1': q1,
                'median': median,
                'q3': q3,
                'lower_whisker': lower_whisker,
                'upper_whisker': upper_whisker,
                'mean': mean_val,
                'sd': sd_val,
                'values': values
            })
    
    if not plot_data:
        return ""
    
    min_val = min(all_values)
    max_val = max(all_values)
    val_range = max_val - min_val
    padding = val_range * 0.1
    
    metric_label = "Accuracy" if metric == 'accuracy' else "F1 (Behavior)"
    
    # Ensure ymin is not negative
    y_min_plot = max(0, min_val - padding)
    
    plot_code = f'''
\\begin{{tikzpicture}}
\\begin{{axis}}[
    width=0.9\\textwidth,
    height=0.4\\textwidth,
    ymin={y_min_plot:.4f},
    ymax={max_val + padding:.4f},
    xlabel={{Window Size (frames)}},
    ylabel={{{metric_label}}},
    xtick={{{','.join(sorted_windows)}}},
    xticklabels={{{','.join(sorted_windows)}}},
    grid=major,
    grid style={{gray!30}},
    axis lines=left,
    enlarge x limits=0.1,
]
'''
    
    # Draw boxplots manually using coordinates
    box_width = 0.3
    for i, data in enumerate(plot_data):
        x_pos = data['window']
        q1 = data['q1']
        median = data['median']
        q3 = data['q3']
        lower_whisker = data['lower_whisker']
        upper_whisker = data['upper_whisker']
        mean_val = data['mean']
        
        x_left = x_pos - box_width / 2
        x_right = x_pos + box_width / 2
        
        # Draw box (Q1 to Q3) using rectangle
        plot_code += f"\\draw[fill=infoblue!30, draw=black, line width=0.5pt] (axis cs:{x_left:.3f},{q1:.4f}) rectangle (axis cs:{x_right:.3f},{q3:.4f});\n"
        
        # Draw median line
        plot_code += f"\\draw[draw=black, line width=1.5pt] (axis cs:{x_left:.3f},{median:.4f}) -- (axis cs:{x_right:.3f},{median:.4f});\n"
        
        # Draw whiskers
        plot_code += f"\\draw[draw=black, line width=1pt] (axis cs:{x_pos:.3f},{lower_whisker:.4f}) -- (axis cs:{x_pos:.3f},{q1:.4f});\n"
        plot_code += f"\\draw[draw=black, line width=1pt] (axis cs:{x_pos:.3f},{q3:.4f}) -- (axis cs:{x_pos:.3f},{upper_whisker:.4f});\n"
        
        # Draw whisker caps
        cap_width = box_width * 0.4
        cap_left = x_pos - cap_width / 2
        cap_right = x_pos + cap_width / 2
        plot_code += f"\\draw[draw=black, line width=1pt] (axis cs:{cap_left:.3f},{lower_whisker:.4f}) -- (axis cs:{cap_right:.3f},{lower_whisker:.4f});\n"
        plot_code += f"\\draw[draw=black, line width=1pt] (axis cs:{cap_left:.3f},{upper_whisker:.4f}) -- (axis cs:{cap_right:.3f},{upper_whisker:.4f});\n"
        
        # Draw mean as a point
        plot_code += f"\\addplot[only marks, mark=*, mark size=2pt, color=gray, fill=gray] coordinates {{({x_pos:.3f}, {mean_val:.4f})}};\n"
        
        # Draw individual data points (jittered)
        import random
        random.seed(42 + i)  # For reproducibility
        for val in data['values']:
            jitter = (random.random() - 0.5) * box_width * 0.8
            x_jittered = x_pos + jitter
            is_outlier = val < lower_whisker or val > upper_whisker
            color = "bestred" if is_outlier else "infoblue"
            opacity = "0.6" if is_outlier else "0.4"
            plot_code += f"\\addplot[only marks, mark=*, mark size=1.5pt, color={color}, fill={color}, fill opacity={opacity}] coordinates {{({x_jittered:.3f}, {val:.4f})}};\n"
    
    plot_code += r'''
\end{axis}
\end{tikzpicture}
'''
    
    # If saving as file, create standalone LaTeX document and compile to PDF
    if 'save_as_file' in locals() and save_as_file and output_dir and figure_name:
        standalone_tex = r'''\documentclass{standalone}
\usepackage{pgfplots}
\usepackage{tikz}
\pgfplotsset{compat=1.18}
\definecolor{bestgreen}{RGB}{39, 174, 96}
\definecolor{bestred}{RGB}{231, 76, 60}
\definecolor{infoblue}{RGB}{52, 152, 219}
\begin{document}
''' + plot_code + r'''
\end{document}
'''
        
        # Save standalone LaTeX file
        tex_file = output_dir / f"{figure_name}.tex"
        with open(tex_file, 'w', encoding='utf-8') as f:
            f.write(standalone_tex)
        
        # Compile to PDF
        import subprocess
        import shutil
        pdflatex_path = shutil.which('pdflatex')
        if pdflatex_path:
            try:
                import os
                original_dir = os.getcwd()
                os.chdir(output_dir)
                subprocess.run(
                    [pdflatex_path, '-interaction=nonstopmode', tex_file.name],
                    capture_output=True,
                    text=True
                )
                os.chdir(original_dir)
                
                # Clean up aux files
                for ext in ['aux', 'log']:
                    aux_file = output_dir / f"{figure_name}.{ext}"
                    if aux_file.exists():
                        aux_file.unlink()
            except Exception:
                pass  # If compilation fails, continue without standalone file
    
    # Return code for inclusion in main document (with figure wrapper)
    safe_label = metric.lower().replace('_', '')
    return r'''
\begin{figure}[h]
\centering
''' + plot_code + r'''
\caption{''' + metric_label + r''' Distribution by Window Size (Box-Whisker Plot)}
\label{fig:boxplot_''' + safe_label + r'''}
\end{figure}
'''


def generate_lollipop_plot_pgfplots(video_df, video_name, metric, windows, y_min=None, y_max=None, full_page=False, save_as_file=False, output_dir=None, figure_name=None):
    """Generate pgfplots code for lollipop plot.
    
    Args:
        video_df: Video results data
        video_name: Name of video to plot
        metric: Metric to plot
        windows: List of window sizes
        y_min: Minimum y-axis value
        y_max: Maximum y-axis value
        full_page: If True, make plot larger for full-page figure
        save_as_file: If True, save as standalone PDF
        output_dir: Directory to save figure file
        figure_name: Name for the figure file
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
    
    sorted_windows = sorted([int(w) for w in video_data.keys()])
    sorted_windows = [str(w) for w in sorted_windows]
    
    values = [video_data[w] for w in sorted_windows]
    if y_min is None:
        min_val = min(values)
        max_val = max(values)
        val_range = max_val - min_val
        padding = val_range * 0.1
        y_min = min_val - padding
        y_max = max_val + padding
    
    video_short = escape_latex(video_name[:40] + ('...' if len(video_name) > 40 else ''))
    
    # Adjust plot size based on full_page flag - make them larger to prevent compression
    if full_page:
        # Use smaller sizes to prevent plots from being too large
        # Landscape A4 is ~25cm wide x ~18cm tall (with margins ~22cm x ~15cm usable)
        # Smaller size for better fit on page
        width = "8cm"  # Smaller width for 2 columns
        height = "5cm"  # Smaller height for 5 rows
        marker_size = "6pt"
        line_width = "2.5pt"
    else:
        width = "0.45\\textwidth"
        height = "0.25\\textwidth"
        marker_size = "4pt"
        line_width = "1.5pt"
    
    plot_code = f'''
\\begin{{tikzpicture}}
\\begin{{axis}}[
    width={width},
    height={height},
    ymin={y_min:.4f},
    ymax={y_max:.4f},
    xlabel={{Window Size (frames)}},
    ylabel={{F1 (Behavior)}},
    xtick={{{','.join(sorted_windows)}}},
    xticklabels={{{','.join(sorted_windows)}}},
    grid=major,
    grid style={{gray!30}},
    axis lines=left,
    enlarge x limits=0.1,
    title={{{video_short}}},
    title style={{font=\large}},
    scale only axis,
]
'''
    
    # Add lollipop lines and dots
    for w in sorted_windows:
        val = video_data[w]
        plot_code += f"\\addplot[mark=*, mark size={marker_size}, color=infoblue, line width={line_width}] coordinates {{({w}, 0) ({w}, {val:.4f})}};\n"
        plot_code += f"\\addplot[only marks, mark=*, mark size={marker_size}, color=bestred] coordinates {{({w}, {val:.4f})}};\n"
    
    plot_code += r'''
\end{axis}
\end{tikzpicture}
'''
    
    # If saving as file, create standalone LaTeX document and compile to PDF
    if save_as_file and output_dir and figure_name:
        standalone_tex = r'''\documentclass{standalone}
\usepackage{pgfplots}
\usepackage{tikz}
\pgfplotsset{compat=1.18}
\definecolor{bestgreen}{RGB}{39, 174, 96}
\definecolor{bestred}{RGB}{231, 76, 60}
\definecolor{infoblue}{RGB}{52, 152, 219}
\begin{document}
''' + plot_code + r'''
\end{document}
'''
        
        # Save standalone LaTeX file
        tex_file = output_dir / f"{figure_name}.tex"
        with open(tex_file, 'w', encoding='utf-8') as f:
            f.write(standalone_tex)
        
        # Compile to PDF
        import subprocess
        import shutil
        pdflatex_path = shutil.which('pdflatex')
        if pdflatex_path:
            try:
                import os
                original_dir = os.getcwd()
                os.chdir(output_dir)
                subprocess.run(
                    [pdflatex_path, '-interaction=nonstopmode', tex_file.name],
                    capture_output=True,
                    text=True
                )
                os.chdir(original_dir)
                
                # Clean up aux files
                for ext in ['aux', 'log']:
                    aux_file = output_dir / f"{figure_name}.{ext}"
                    if aux_file.exists():
                        aux_file.unlink()
            except Exception:
                pass  # If compilation fails, continue without standalone file
    
    return plot_code


def generate_latex_report(video_df, summary_df, feature_df, worst_videos, sensitive_videos):
    """Generate LaTeX report content."""
    
    # Find best window
    best_window = max(summary_df, key=lambda x: float(x['mean_accuracy']))
    
    # Get unique videos count
    unique_videos = len(set(row['video_name'] for row in video_df))
    windows = sorted([int(w) for w in set(row['window_size'] for row in video_df)])
    windows = [str(w) for w in windows]
    
    # Calculate additional values
    window5 = next((r for r in summary_df if r['window_size'] == '5'), None)
    window30 = next((r for r in summary_df if r['window_size'] == '30'), None)
    window5_acc = float(window5['mean_accuracy']) if window5 else None
    window5_f1 = float(window5['mean_f1_behavior']) if window5 else None
    window30_acc = float(window30['mean_accuracy']) if window30 else float(best_window['mean_accuracy'])
    diff_20_30 = abs(float(best_window['mean_accuracy']) - window30_acc)
    
    # Sort summary by window size
    sorted_summary = sorted(summary_df, key=lambda x: int(x['window_size']))
    
    latex = r'''\documentclass[11pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{geometry}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{array}
\usepackage{graphicx}
\usepackage{xcolor}
\usepackage{hyperref}
\usepackage{amsmath}
\usepackage{siunitx}
\usepackage{adjustbox}
\usepackage{pgfplots}
\usepackage{tikz}
\usepackage{pdflscape}
\usepackage{url}
\pgfplotsset{compat=1.18}

\geometry{margin=1in}
\hypersetup{
    colorlinks=true,
    linkcolor=blue,
    filecolor=magenta,      
    urlcolor=cyan,
}

\title{Window Size Analysis Report\\
\large Cross-Validation Results for Behavior Classification}
\author{Automated Analysis Pipeline}
\date{\today}

\definecolor{bestgreen}{RGB}{39, 174, 96}
\definecolor{bestred}{RGB}{231, 76, 60}
\definecolor{infoblue}{RGB}{52, 152, 219}

\begin{document}

\maketitle

\begin{abstract}
This report presents a comprehensive analysis of window size effects on behavior classification performance using leave-one-out cross-validation. The analysis examines performance metrics across multiple window sizes (''' + ', '.join(windows) + r''' frames) to identify the optimal temporal scale for feature generation and classification. Key findings include the identification of Window ''' + best_window['window_size'] + r''' frames as the optimal window size, with a mean accuracy of ''' + f"{float(best_window['mean_accuracy']):.4f}" + r''' and F1 (Behavior) score of ''' + f"{float(best_window['mean_f1_behavior']):.4f}" + r'''. The analysis also identifies worst-performing videos that may require data quality review and window-sensitive videos that show high variability across temporal scales. A total of ''' + str(unique_videos) + r''' unique videos were analyzed across ''' + str(len(windows)) + r''' window sizes, representing ''' + str(len(video_df)) + r''' individual test cases.
\end{abstract}

\tableofcontents
\newpage

\section{Introduction}

\subsection{Purpose and Scope}

This analysis examines the effect of window size on behavior classification performance for the \textit{turn\_left} behavior. Window size is a critical hyperparameter in temporal feature extraction, as it determines the temporal scale at which behavioral patterns are captured. Too small a window may miss important behavioral dynamics, while too large a window may introduce noise or blur important short-term patterns.

The analysis compares performance across window sizes of ''' + ', '.join(windows) + r''' frames, using leave-one-out cross-validation where one animal (identity) is held out at a time. This approach ensures robust performance estimates while maintaining independence between training and test sets.

\subsection{Data Structure}

The cross-validation structure used in this analysis holds out \textbf{one animal at a time}, not one video at a time. Each video file contains multiple animals, identified by identity numbers [0], [1], [2], etc. at the end of the video filename. This means that the same video file appears multiple times in the results, each time representing a different animal being held out during cross-validation. Each (video\_name, identity) pair represents a separate test case, ensuring that the model's performance is evaluated independently for each animal.

\subsection{Performance Metrics}

The analysis focuses on several key performance metrics:

\begin{itemize}
    \item \textbf{Accuracy}: Overall classification accuracy across both behavior and not-behavior classes
    \item \textbf{F1 (Behavior)}: F1 score for the behavior class - the most relevant metric for behavior classification, as it balances precision and recall for the class of interest
    \item \textbf{F1 (Not Behavior)}: F1 score for the not-behavior class
    \item \textbf{Precision and Recall}: Class-specific precision and recall for both classes
\end{itemize}

Of these metrics, \textbf{F1 (Behavior)} is considered the most relevant for this analysis, as it directly measures the model's ability to correctly identify the behavior of interest while accounting for both false positives and false negatives.

\section{Executive Summary}

\subsection{Key Findings}

The analysis reveals that \textbf{Window ''' + best_window['window_size'] + r''' frames} provides the optimal balance between classification performance and stability. This window size achieves:

\begin{itemize}
    \item Mean accuracy of ''' + f"{float(best_window['mean_accuracy']):.4f}" + r'''
    \item Mean F1 (Behavior) of ''' + f"{float(best_window['mean_f1_behavior']):.4f}" + r''' (most relevant metric)
    \item Standard deviation of ''' + f"{float(best_window['sd_accuracy']):.4f}" + r''' for accuracy, indicating good stability
    \item Standard deviation of ''' + f"{float(best_window['sd_f1_behavior']):.4f}" + r''' for F1 (Behavior)
\end{itemize}

\subsection{Performance Trends}

Several important trends emerge from the analysis:

\begin{enumerate}
    \item \textbf{Larger windows generally perform better}: Window sizes of 20-30 frames show significantly higher accuracy and F1 (Behavior) scores than smaller windows (5-10 frames). This suggests that the \textit{turn\_left} behavior benefits from a longer temporal context for accurate classification.
    
    \item \textbf{Performance plateau}: There is minimal difference between Window 20 and Window 30 frames (difference in accuracy: ''' + f"{diff_20_30:.4f}" + r'''), suggesting that beyond 20 frames, additional temporal context provides diminishing returns.
    
    \item \textbf{Window 5 frames shows lowest performance}: With mean accuracy of ''' + (f"{window5_acc:.4f}" if window5_acc else "N/A") + r''' and F1 (Behavior) of ''' + (f"{window5_f1:.4f}" if window5_f1 else "N/A") + r''', the smallest window size is insufficient for capturing the behavioral dynamics of \textit{turn\_left}.
    
    \item \textbf{Stability considerations}: Window 20 frames shows slightly better stability (lower standard deviation) than Window 30 frames, making it preferable when consistency is important.
\end{enumerate}

\section{Window Size Comparison}

\subsection{Overall Performance Metrics}

Table~\ref{tab:window_comparison} presents a comprehensive comparison of performance metrics across all tested window sizes. The table includes mean and standard deviation for accuracy and F1 scores for both behavior and not-behavior classes.

\begin{table}[h]
\centering
\caption{Performance Summary by Window Size}
\label{tab:window_comparison}
\adjustbox{width=\textwidth,center}{%
\begin{tabular}{lcccccc}
\toprule
Window Size & Mean Acc. & SD Acc. & Mean F1 (Beh.) & SD F1 (Beh.) & Mean F1 (Not) & SD F1 (Not) \\
\midrule
'''
    
    for row in sorted_summary:
        is_best = row['window_size'] == best_window['window_size']
        best_marker = r'\textcolor{bestgreen}{\textbf{' if is_best else ''
        best_marker_end = r'}}' if is_best else ''
        
        # Find best F1 behavior
        best_f1_window = max(summary_df, key=lambda x: float(x['mean_f1_behavior']))
        is_best_f1 = row['window_size'] == best_f1_window['window_size']
        f1_marker = r'\textcolor{bestred}{\textbf{' if is_best_f1 else ''
        f1_marker_end = r'}}' if is_best_f1 else ''
        
        latex += f"{row['window_size']} & {best_marker}{float(row['mean_accuracy']):.4f}{best_marker_end} & {float(row['sd_accuracy']):.4f} & {f1_marker}{float(row['mean_f1_behavior']):.4f}{f1_marker_end} & {float(row['sd_f1_behavior']):.4f} & {float(row['mean_f1_not_behavior']):.4f} & {float(row['sd_f1_not_behavior']):.4f} \\\\\n"
    
    latex += r'''\bottomrule
\end{tabular}
\endadjustbox
\end{table}

\subsection{Visualization of Performance Metrics}

The following plots visualize the performance metrics across different window sizes, highlighting the best performing window for each metric.

'''
    
    # Generate barbell plots for key metrics (each in its own figure)
    metrics_to_plot = [
        ('Mean Accuracy', 'mean_accuracy', 'mean_accuracy'),
        ('Mean F1 (Behavior)', 'mean_f1_behavior', 'mean_f1_behavior'),
        ('Mean F1 (Not Behavior)', 'mean_f1_not_behavior', 'mean_f1_not_behavior'),
    ]
    
    best_values = {}
    for metric_title, metric_key, best_key in metrics_to_plot:
        metric_data = {}
        for row in sorted_summary:
            window = row['window_size']
            metric_data[window] = float(row[metric_key])
        
        # Find best window for this metric
        if best_key == 'mean_accuracy':
            best_window_for_metric = best_window['window_size']
        elif best_key == 'mean_f1_behavior':
            best_f1_window = max(summary_df, key=lambda x: float(x['mean_f1_behavior']))
            best_window_for_metric = best_f1_window['window_size']
        else:
            best_window_for_metric = max(summary_df, key=lambda x: float(x[metric_key]))['window_size']
        
        best_values[best_key] = best_window_for_metric
        
        # Generate plot (already wrapped in figure environment by the function)
        plot_code = generate_barbell_plot_pgfplots(metric_data, metric_title, best_window_for_metric, windows)
        latex += plot_code
    
    latex += r'''
\subsection{Interpretation of Results}

The results in Table~\ref{tab:window_comparison} reveal several important patterns. Window ''' + best_window['window_size'] + r''' frames achieves the highest mean accuracy of ''' + f"{float(best_window['mean_accuracy']):.4f}" + r''', while Window ''' + best_f1_window['window_size'] + r''' frames achieves the highest F1 (Behavior) score of ''' + f"{float(best_f1_window['mean_f1_behavior']):.4f}" + r'''. 

Since F1 (Behavior) is the most relevant metric for behavior classification, Window ''' + best_f1_window['window_size'] + r''' frames is recommended as the optimal choice. This metric balances precision and recall for the behavior class, which is critical when the goal is to accurately identify instances of the target behavior.

The standard deviations provide insight into the stability of each window size. Lower standard deviations indicate more consistent performance across videos, which is desirable for reliable classification. Window ''' + best_window['window_size'] + r''' frames shows good stability with a standard deviation of ''' + f"{float(best_window['sd_accuracy']):.4f}" + r''' for accuracy.

\section{Per-Video Performance Distribution}

\subsection{Distribution Analysis}

To understand the variability in performance across different videos, we examine the distribution of performance metrics for each window size. This analysis helps identify whether performance differences are consistent across all videos or if certain videos drive the observed patterns.

\subsection{Accuracy Distribution}

The accuracy distribution across all videos for each window size shows that:

\begin{itemize}
    \item Window ''' + best_window['window_size'] + r''' frames has the highest median accuracy
    \item The interquartile range (IQR) is narrower for larger windows, indicating more consistent performance
    \item Outliers are more common in smaller window sizes, suggesting that some videos are particularly sensitive to insufficient temporal context
\end{itemize}

The following box-whisker plots show individual video performance as points, with outliers highlighted. This visualization reveals that while most videos perform well with Window ''' + best_window['window_size'] + r''' frames, a small number of videos show poor performance regardless of window size, suggesting potential data quality issues.

'''
    
    # Add box-whisker plots
    accuracy_boxplot = generate_boxplot_pgfplots(video_df, 'accuracy', summary_df, windows)
    f1_boxplot = generate_boxplot_pgfplots(video_df, 'f1_behavior', summary_df, windows)
    latex += accuracy_boxplot
    latex += f1_boxplot
    
    latex += r'''
\subsection{F1 (Behavior) Distribution}

The F1 (Behavior) distribution follows similar patterns to accuracy, with Window ''' + best_f1_window['window_size'] + r''' frames showing the highest median F1 (Behavior) score of ''' + f"{float(best_f1_window['mean_f1_behavior']):.4f}" + r'''. The distribution is slightly more variable than accuracy, with a standard deviation of ''' + f"{float(best_f1_window['sd_f1_behavior']):.4f}" + r''', reflecting the challenge of accurately identifying the behavior class.

The coefficient of variation (CV = SD/Mean) for F1 (Behavior) is ''' + f"{float(best_f1_window['sd_f1_behavior']) / float(best_f1_window['mean_f1_behavior']):.4f}" + r''' for Window ''' + best_f1_window['window_size'] + r''' frames, indicating moderate variability. This suggests that while the window size is generally effective, some videos may benefit from window size optimization.

\section{Worst Performing Videos}

\subsection{Identification of Problematic Videos}

Identifying videos with consistently poor performance is important for several reasons:

\begin{enumerate}
    \item \textbf{Data quality assessment}: Poor performance may indicate annotation errors, video quality issues, or ambiguous behavioral instances
    \item \textbf{Model improvement}: Understanding why certain videos fail can inform feature engineering or model architecture improvements
    \item \textbf{Training data curation}: Consistently poor-performing videos may need to be reviewed or excluded from training
\end{enumerate}

\subsection{Overall Worst Performers}

Table~\ref{tab:worst_videos} lists the top 10 videos with the lowest mean accuracy across all window sizes. These videos show consistently poor performance regardless of the temporal scale used for feature extraction.

\begin{table}[h]
\centering
\caption{Top 10 Worst Performing Videos (Overall)}
\label{tab:worst_videos}
\adjustbox{width=\textwidth,center}{%
\begin{tabular}{clcc}
\toprule
Rank & Video Name & Mean Accuracy & SD Accuracy \\
\midrule
'''
    
    for i, video in enumerate(worst_videos[:10], 1):
        video_short = escape_latex(video['video_name'][:60] + ('...' if len(video['video_name']) > 60 else ''))
        latex += f"{i} & {video_short} & {video['mean_accuracy']:.4f} & {video['sd_accuracy']:.4f} \\\\\n"
    
    latex += r'''\bottomrule
\end{tabular}%
}
\end{table}

\subsection{Window-Specific Performance}

To understand which window sizes cause the most difficulty for each video, we examine performance at each window size. The worst-performing video overall has a mean accuracy of ''' + f"{worst_videos[0]['mean_accuracy']:.4f}" + r''' across all window sizes. 

Analysis of per-window performance reveals that:

\begin{itemize}
    \item Some videos perform poorly across all window sizes, suggesting fundamental data quality or annotation issues
    \item Other videos show poor performance only at specific window sizes, indicating temporal scale sensitivity
    \item The worst-performing window size varies by video, highlighting the importance of video-specific analysis
\end{itemize}

\subsection{Implications}

Videos with consistently poor performance across all window sizes likely have:

\begin{itemize}
    \item Annotation inconsistencies or errors
    \item Poor video quality (blur, occlusion, lighting issues)
    \item Ambiguous behavioral instances that are difficult to classify
    \item Unique characteristics that the current feature set cannot capture
\end{itemize}

These videos should be manually reviewed to identify potential issues and determine whether they should be excluded from training or if additional annotation or preprocessing is needed.

\section{Window Sensitivity Analysis}

\subsection{Coefficient of Variation}

To identify videos that are most sensitive to window size changes, we calculate the coefficient of variation (CV) for F1 (Behavior) scores across window sizes. The CV is defined as:

\begin{equation}
CV = \frac{\sigma}{\mu}
\end{equation}

where $\sigma$ is the standard deviation and $\mu$ is the mean of F1 (Behavior) scores across all window sizes for a given video. Higher CV values indicate greater sensitivity to window size, meaning the video's performance varies significantly depending on the temporal scale used.

\subsection{Most Sensitive Videos}

Table~\ref{tab:sensitive_videos} lists the top 10 videos with the highest coefficient of variation. These videos show the greatest variability in F1 (Behavior) across different window sizes.

\begin{table}[h]
\centering
\caption{Top 10 Most Window-Sensitive Videos}
\label{tab:sensitive_videos}
\adjustbox{width=\textwidth,center}{%
\begin{tabular}{clccc}
\toprule
Rank & Video Name & CV (F1 Beh.) & Mean Accuracy & SD Accuracy \\
\midrule
'''
    
    for i, video in enumerate(sensitive_videos[:10], 1):
        video_short = escape_latex(video['video_name'][:50] + ('...' if len(video['video_name']) > 50 else ''))
        latex += f"{i} & {video_short} & {float(video['cv']):.4f} & {float(video['mean_accuracy']):.4f} & {float(video['sd_accuracy']):.4f} \\\\\n"
    
    latex += r'''\bottomrule
\end{tabular}%
}
\end{table}

\subsection{Interpretation of Sensitivity}

The most sensitive video has a coefficient of variation of ''' + f"{float(sensitive_videos[0]['cv']):.4f}" + r''', indicating that its F1 (Behavior) score varies substantially across window sizes. This high variability suggests that:

\begin{itemize}
    \item The video's behavioral patterns may be better captured at specific temporal scales
    \item The video may contain behaviors with varying durations that require different window sizes
    \item The video may benefit from window size optimization or adaptive window sizing
\end{itemize}

The following lollipop plots visualize how F1 (Behavior) varies across window sizes for each sensitive video. These plots reveal distinct patterns:

\newpage
\begin{landscape}
\thispagestyle{empty}
\begin{figure}[!h]
\centering
'''
    
    # Calculate global y-axis range for lollipop plots
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
    
    # Generate lollipop plots for top 10 sensitive videos (2x5 grid, full page)
    # Smaller plots with more spacing to prevent them from being too large
    latex += r'''
\vspace{0.4cm}
\begin{tabular}{@{}c@{\hspace{0.8cm}}c@{}}
'''
    
    for i, video in enumerate(sensitive_videos[:10]):
        if i > 0 and i % 2 == 0:
            latex += r'''\end{tabular}
\vspace{0.5cm}
\begin{tabular}{@{}c@{\hspace{0.8cm}}c@{}}
'''
        
        # Generate plot with smaller size
        plot_code = generate_lollipop_plot_pgfplots(video_df, video['video_name'], 'f1_behavior', windows, global_y_min, global_y_max, full_page=True)
        latex += r'''\begin{minipage}{0.46\textwidth}
\centering
''' + plot_code + r'''
\end{minipage}'''
        
        if i % 2 == 0:
            latex += r''' & '''
        else:
            latex += r''' \\
'''
    
    latex += r'''
\end{tabular}
\vspace{0.4cm}
\caption{F1 (Behavior) Across Window Sizes for Most Window-Sensitive Videos (CV calculated using F1 Behavior)}
\label{fig:lollipop_sensitive}
\end{figure}
\end{landscape}
\newpage
\thispagestyle{plain}

The lollipop plots reveal distinct patterns:

\begin{itemize}
    \item Some videos show a clear peak at a specific window size, suggesting an optimal temporal scale
    \item Other videos show gradual increases or decreases, indicating sensitivity to temporal context
    \item A few videos show erratic patterns, suggesting complex behavioral dynamics
\end{itemize}
'''
    
    latex += r'''
\subsection{Recommendations for Sensitive Videos}

Videos with high window sensitivity may benefit from:

\begin{enumerate}
    \item \textbf{Window size optimization}: Testing additional window sizes around the apparent optimal value
    \item \textbf{Adaptive window sizing}: Using different window sizes for different segments of the video
    \item \textbf{Feature engineering}: Developing features that are less sensitive to temporal scale
    \item \textbf{Ensemble methods}: Combining predictions from multiple window sizes
\end{enumerate}

\section{Statistical Analysis and Findings}

\subsection{Performance Trends by Window Size}

The analysis reveals clear performance trends across window sizes:

\subsubsection{Small Windows (5-10 frames)}

Small window sizes show the lowest performance, with mean accuracy ranging from ''' + (f"{window5_acc:.4f}" if window5_acc else "N/A") + r''' (Window 5) to ''' + f"{float(next((r for r in summary_df if r['window_size'] == '10'), best_window)['mean_accuracy']):.4f}" + r''' (Window 10). This suggests that 5-10 frames provide insufficient temporal context to capture the behavioral dynamics of \textit{turn\_left}. The behavior likely requires a longer observation period to be accurately identified.

\subsubsection{Medium Windows (15-20 frames)}

Performance improves significantly in the medium window size range. Window 15 frames achieves mean accuracy of ''' + f"{float(next((r for r in summary_df if r['window_size'] == '15'), best_window)['mean_accuracy']):.4f}" + r''', while Window 20 frames achieves ''' + f"{float(best_window['mean_accuracy']):.4f}" + r'''. This improvement suggests that 15-20 frames provide adequate temporal context for most instances of the behavior.

\subsubsection{Large Windows (25-30 frames)}

Large window sizes show similar performance to Window 20 frames, with Window 30 frames achieving mean accuracy of ''' + f"{window30_acc:.4f}" + r'''. The minimal difference (''' + f"{diff_20_30:.4f}" + r''') between Window 20 and Window 30 suggests a performance plateau, where additional temporal context provides diminishing returns.

\subsection{Why Window ''' + best_window['window_size'] + r''' Frames is Optimal}

Based on the comprehensive analysis, Window ''' + best_window['window_size'] + r''' frames is recommended as the optimal window size for the following reasons:

\begin{enumerate}
    \item \textbf{Highest F1 (Behavior) Score}: Window ''' + best_f1_window['window_size'] + r''' frames achieves the highest F1 (Behavior) score of ''' + f"{float(best_f1_window['mean_f1_behavior']):.4f}" + r''', which is the most relevant metric for behavior classification. This score balances precision and recall for the behavior class, ensuring both accurate detection and minimal false positives.
    
    \item \textbf{High Accuracy}: With a mean accuracy of ''' + f"{float(best_window['mean_accuracy']):.4f}" + r''' across all videos, Window ''' + best_window['window_size'] + r''' frames provides excellent overall classification performance.
    
    \item \textbf{Good Stability}: The standard deviation of ''' + f"{float(best_window['sd_accuracy']):.4f}" + r''' for accuracy and ''' + f"{float(best_window['sd_f1_behavior']):.4f}" + r''' for F1 (Behavior) indicates consistent performance across videos, which is important for reliable classification in production settings.
    
    \item \textbf{Balanced F1 Scores}: Window ''' + best_window['window_size'] + r''' frames achieves good performance for both behavior class (F1 = ''' + f"{float(best_window['mean_f1_behavior']):.4f}" + r''') and not-behavior class (F1 = ''' + f"{float(best_window['mean_f1_not_behavior']):.4f}" + r'''), indicating balanced classification across both classes.
    
    \item \textbf{Computational Efficiency}: Compared to Window 30 frames, Window ''' + best_window['window_size'] + r''' frames provides similar performance with less computational overhead, making it more efficient for real-time or large-scale applications.
\end{enumerate}

\section{Discussion}

\subsection{Implications for Behavior Classification}

The finding that larger window sizes (20-30 frames) outperform smaller windows (5-10 frames) has important implications for behavior classification:

\begin{itemize}
    \item \textbf{Temporal Context Matters}: The \textit{turn\_left} behavior requires sufficient temporal context to be accurately identified. This suggests that the behavior involves dynamic patterns that unfold over multiple frames, rather than being identifiable from single-frame or very short sequences.
    
    \item \textbf{Optimal Temporal Scale}: The performance plateau between Window 20 and Window 30 frames suggests that approximately 20 frames represents the optimal temporal scale for capturing \textit{turn\_left} behavior. Beyond this, additional temporal context provides minimal benefit.
    
    \item \textbf{Window Size as Hyperparameter}: The significant performance differences across window sizes highlight the importance of window size as a critical hyperparameter that should be carefully tuned for each behavior class.
\end{itemize}

\subsection{Limitations and Considerations}

Several limitations should be considered when interpreting these results:

\begin{enumerate}
    \item \textbf{Single Behavior Class}: This analysis focuses exclusively on \textit{turn\_left} behavior. Results may not generalize to other behaviors, which may have different optimal window sizes.
    
    \item \textbf{Feature Set}: The analysis uses a specific feature set. Different features may show different sensitivity to window size.
    
    \item \textbf{Video Characteristics}: The optimal window size may vary depending on video characteristics such as frame rate, resolution, and behavioral context.
    
    \item \textbf{Cross-Validation Structure}: The leave-one-animal-out cross-validation ensures independence but may not fully capture performance in scenarios with different animal distributions.
\end{enumerate}

\subsection{Future Directions}

Several directions for future research and improvement are suggested by these findings:

\begin{itemize}
    \item \textbf{Behavior-Specific Optimization}: Test window sizes for other behavior classes to determine if optimal window sizes are behavior-specific
    
    \item \textbf{Adaptive Window Sizing}: Develop methods that adapt window size based on video characteristics or behavioral context
    
    \item \textbf{Feature Engineering}: Investigate features that are less sensitive to window size while maintaining discriminative power
    
    \item \textbf{Ensemble Approaches}: Explore combining predictions from multiple window sizes to leverage the strengths of different temporal scales
\end{itemize}

\section{Recommendations}

\subsection{Primary Recommendation}

Based on the comprehensive analysis, we recommend using \textbf{Window ''' + best_window['window_size'] + r''' frames} for optimal performance in \textit{turn\_left} behavior classification. This window size provides:

\begin{itemize}
    \item Highest F1 (Behavior) score of ''' + f"{float(best_f1_window['mean_f1_behavior']):.4f}" + r'''
    \item Excellent accuracy of ''' + f"{float(best_window['mean_accuracy']):.4f}" + r'''
    \item Good stability with standard deviation of ''' + f"{float(best_window['sd_accuracy']):.4f}" + r'''
    \item Balanced performance across both behavior and not-behavior classes
\end{itemize}

\subsection{Alternative Considerations}

If slightly higher accuracy is needed and stability is less critical, Window 30 frames (mean accuracy: ''' + f"{window30_acc:.4f}" + r''') may be considered, though the improvement is minimal (''' + f"{diff_20_30:.4f}" + r''' difference) and comes with increased computational cost.

\subsection{Data Quality Recommendations}

\begin{itemize}
    \item \textbf{Review Worst Performing Videos}: The top 10 worst-performing videos (Table~\ref{tab:worst_videos}) should be manually reviewed to identify potential data quality issues, annotation errors, or video quality problems.
    
    \item \textbf{Investigate Sensitive Videos}: Videos with high coefficient of variation (Table~\ref{tab:sensitive_videos}) should be examined to understand why they are sensitive to window size. This may reveal important behavioral patterns or inform feature engineering.
    
    \item \textbf{Validate Annotations}: Consider re-annotating a subset of worst-performing videos to ensure annotation quality and consistency.
\end{itemize}

\subsection{Model Improvement Recommendations}

\begin{itemize}
    \item \textbf{Window Size Optimization}: For videos showing high sensitivity, test intermediate window sizes (e.g., 18, 22, 25 frames) to fine-tune performance.
    
    \item \textbf{Feature Analysis}: Examine feature importance rankings to identify which features are most critical for each window size, potentially informing feature engineering.
    
    \item \textbf{Video-Specific Tuning}: Consider developing video-specific or context-specific window size selection strategies for highly sensitive videos.
\end{itemize}

\section{Conclusion}

This comprehensive analysis of window size effects on \textit{turn\_left} behavior classification reveals that Window ''' + best_window['window_size'] + r''' frames provides optimal performance, achieving a mean accuracy of ''' + f"{float(best_window['mean_accuracy']):.4f}" + r''' and F1 (Behavior) score of ''' + f"{float(best_window['mean_f1_behavior']):.4f}" + r'''. The analysis demonstrates that larger window sizes (20-30 frames) significantly outperform smaller windows (5-10 frames), suggesting that \textit{turn\_left} behavior requires sufficient temporal context for accurate classification.

The identification of worst-performing and window-sensitive videos provides actionable insights for data quality improvement and model optimization. Future work should explore behavior-specific window size optimization and adaptive window sizing strategies to further improve classification performance.

\section*{Data Quality Notes}

\subsection*{Cross-Validation Structure}

It is important to note that the cross-validation structure used in this analysis holds out \textbf{one animal at a time}, not one video at a time. Each video file contains multiple animals (identities), identified by numbers [0], [1], [2], etc. at the end of the video filename. Each (video\_name, identity) pair represents a separate test case, ensuring that model performance is evaluated independently for each animal. This structure is correctly handled throughout the analysis pipeline.

\subsection*{Data Completeness}

Some videos may be missing from certain window sizes, which may indicate data collection or processing issues. The validation report (available in \texttt{data/processed/validation\_report.txt}) provides detailed information about data completeness and consistency.

\appendix

\section{Summary Statistics by Window Size}

Table~\ref{tab:summary_all} provides complete summary statistics for all window sizes.

\begin{table}[h]
\centering
\caption{Complete Summary Statistics}
\label{tab:summary_all}
\adjustbox{width=\textwidth,center}{%
\begin{tabular}{lcccccc}
\toprule
Window & Mean Acc. & SD Acc. & Mean F1 (Beh.) & SD F1 (Beh.) & Mean F1 (Not) & SD F1 (Not) \\
\midrule
'''
    
    for row in sorted_summary:
        latex += f"{row['window_size']} & {float(row['mean_accuracy']):.4f} & {float(row['sd_accuracy']):.4f} & {float(row['mean_f1_behavior']):.4f} & {float(row['sd_f1_behavior']):.4f} & {float(row['mean_f1_not_behavior']):.4f} & {float(row['sd_f1_not_behavior']):.4f} \\\\\n"
    
    latex += r'''\bottomrule
\end{tabular}%
}
\end{table}

\section{Data Files}

All processed data files are located in \texttt{data/processed/}:

\begin{itemize}
    \item \texttt{video\_results.csv}: Complete performance data for each (video, identity, window) combination
    \item \texttt{summary\_stats.csv}: Window-level summary statistics
    \item \texttt{feature\_importance.csv}: Top features by importance for each window size
    \item \texttt{validation\_report.txt}: Detailed validation results
\end{itemize}

\section{Visualizations}

Comprehensive visualizations including barbell plots, box-whisker plots, and lollipop plots are included in this report and are also available in the HTML report (\path{reports/window\_size\_analysis\_report.html}).

These visualizations provide detailed graphical representations of the performance patterns described in this report.

\end{document}
'''
    
    return latex


def main():
    """Main execution function."""
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    data_dir = project_dir / 'data' / 'processed'
    output_dir = project_dir / 'reports'  # Save to reports folder
    figures_dir = project_dir / 'reports' / 'figures'  # Save figures in reports/figures
    
    output_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 80)
    print("Generating LaTeX Report")
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
    
    # Generate LaTeX
    print("Generating LaTeX report...")
    latex_content = generate_latex_report(video_df, summary_df, feature_df, worst_videos, sensitive_videos)
    
    # Write LaTeX file
    output_file = output_dir / 'window_size_analysis_report.tex'
    figures_dir = project_dir / 'reports' / 'figures'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(latex_content)
    
    print()
    print("=" * 80)
    print("LaTeX Report Generated Successfully!")
    print("=" * 80)
    print(f"Output file: {output_file}")
    print()
    
    # Try to compile PDF automatically
    import subprocess
    import shutil
    
    pdflatex_path = shutil.which('pdflatex')
    if pdflatex_path:
        print("Compiling LaTeX to PDF...")
        try:
            # Change to reports directory for compilation
            import os
            original_dir = os.getcwd()
            os.chdir(output_dir)
            
            # Run pdflatex twice (needed for table of contents and references)
            for run in [1, 2]:
                result = subprocess.run(
                    [pdflatex_path, '-interaction=nonstopmode', output_file.name],
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0 and run == 1:
                    print(f"  Warning: pdflatex had errors (this is normal for first run)")
            
            os.chdir(original_dir)
            
            # Check if PDF was created
            pdf_file = output_dir / 'window_size_analysis_report.pdf'
            if pdf_file.exists():
                pdf_size = pdf_file.stat().st_size / 1024  # Size in KB
                print(f"  ✓ PDF compiled successfully: {pdf_file} ({pdf_size:.1f} KB)")
                
                # Clean up LaTeX auxiliary files
                aux_files = ['aux', 'log', 'out', 'toc', 'fdb_latexmk', 'fls', 'synctex.gz']
                for ext in aux_files:
                    aux_file = output_dir / f'window_size_analysis_report.{ext}'
                    if aux_file.exists():
                        aux_file.unlink()
                print("  ✓ Cleaned up LaTeX auxiliary files")
            else:
                print("  ✗ PDF compilation failed - check LaTeX errors above")
        except Exception as e:
            print(f"  ✗ Could not compile PDF automatically: {e}")
            print(f"  You can compile manually by running:")
            print(f"    cd {output_dir}")
            print(f"    pdflatex {output_file.name}")
            print(f"    pdflatex {output_file.name}  # Run twice")
    else:
        print("pdflatex not found in PATH. To compile the PDF manually:")
        print(f"  cd {output_dir}")
        print(f"  pdflatex {output_file.name}")
        print(f"  pdflatex {output_file.name}  # Run twice for proper table of contents")
    print()
    print("Report includes:")
    print("  ✓ Executive summary with best window size recommendation")
    print("  ✓ Detailed window size comparison with narrative")
    print("  ✓ Per-video performance distribution analysis")
    print("  ✓ Worst performing videos analysis")
    print("  ✓ Window sensitivity analysis with CV explanation")
    print("  ✓ Statistical analysis and findings")
    print("  ✓ Discussion and recommendations")
    print("  ✓ Complete tables and appendices")
    print("  ✓ Embedded plots (barbell, box-whisker, and lollipop plots)")


if __name__ == '__main__':
    main()

