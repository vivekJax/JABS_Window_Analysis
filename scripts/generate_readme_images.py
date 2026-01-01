#!/usr/bin/env python3
"""
Generate sample visualizations for README.md
Creates SVG images that can be displayed on GitHub.
"""

import sys
from pathlib import Path

# Add scripts directory to path
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from generate_html_report import load_csv, find_best_values, create_barbell_plot, create_boxwhisker_plot, create_lollipop_plot, calculate_stats

def main():
    """Generate sample visualizations for README."""
    project_dir = script_dir.parent
    data_dir = project_dir / 'data' / 'processed'
    output_dir = project_dir / 'docs' / 'images'
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("Generating README visualizations...")
    
    # Load data
    video_df = load_csv(data_dir / 'video_results.csv')
    summary_df = load_csv(data_dir / 'summary_stats.csv')
    
    # Find best values
    best_values = find_best_values(summary_df)
    
    # Get window sizes
    windows = sorted(set(row['window_size'] for row in summary_df))
    
    # 1. Generate F1 (Behavior) barbell plot - most important metric
    print("  Generating F1 (Behavior) barbell plot...")
    f1_data = {}
    for row in summary_df:
        f1_data[row['window_size']] = float(row['mean_f1_behavior'])
    
    best_f1_window = best_values['mean_f1_behavior']['window']
    f1_plot = create_barbell_plot('mean_f1_behavior', f1_data, windows, best_f1_window, plot_width=400, plot_height=250)
    
    with open(output_dir / 'f1_behavior_barbell.svg', 'w') as f:
        f.write(f1_plot)
    
    # 2. Generate Accuracy barbell plot
    print("  Generating Accuracy barbell plot...")
    acc_data = {}
    for row in summary_df:
        acc_data[row['window_size']] = float(row['mean_accuracy'])
    
    best_acc_window = best_values['mean_accuracy']['window']
    acc_plot = create_barbell_plot('mean_accuracy', acc_data, windows, best_acc_window, plot_width=400, plot_height=250)
    
    with open(output_dir / 'accuracy_barbell.svg', 'w') as f:
        f.write(acc_plot)
    
    # 3. Generate F1 (Behavior) box-whisker plot
    print("  Generating F1 (Behavior) box-whisker plot...")
    f1_boxplot = create_boxwhisker_plot(video_df, 'f1_behavior', summary_df, plot_width=800, plot_height=400)
    
    with open(output_dir / 'f1_behavior_boxplot.svg', 'w') as f:
        f.write(f1_boxplot)
    
    # 4. Generate sample lollipop plot (first sensitive video)
    print("  Generating sample lollipop plot...")
    _, sensitive_videos = calculate_stats(video_df)
    if sensitive_videos:
        sample_video = sensitive_videos[0]['video_name']
        lollipop_plot = create_lollipop_plot(video_df, sample_video, 'f1_behavior', plot_width=600, plot_height=300)
        
        with open(output_dir / 'lollipop_example.svg', 'w') as f:
            f.write(lollipop_plot)
    
    print(f"\n✓ Visualizations saved to {output_dir}/")
    print("  - f1_behavior_barbell.svg")
    print("  - accuracy_barbell.svg")
    print("  - f1_behavior_boxplot.svg")
    print("  - lollipop_example.svg")

if __name__ == '__main__':
    main()

