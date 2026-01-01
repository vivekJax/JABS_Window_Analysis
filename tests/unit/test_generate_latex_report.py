"""Unit tests for generate_latex_report.py"""
import pytest
import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'scripts'))

from generate_latex_report import (
    load_csv,
    calculate_stats,
    escape_latex,
    generate_barbell_plot_pgfplots,
    generate_lollipop_plot_pgfplots
)


class TestLoadCSV:
    """Tests for load_csv function."""
    
    def test_load_csv_valid(self, create_test_csv, sample_video_results):
        """Test loading a valid CSV file."""
        csv_file = create_test_csv('test.csv', sample_video_results)
        
        data = load_csv(csv_file)
        
        assert len(data) == 3
        assert data[0]['window_size'] == '5'
    
    def test_load_csv_empty(self, create_test_csv):
        """Test loading an empty CSV file."""
        csv_file = create_test_csv('empty.csv', [])
        
        data = load_csv(csv_file)
        
        assert data == []


class TestCalculateStats:
    """Tests for calculate_stats function."""
    
    def test_calculate_stats_basic(self, sample_video_results):
        """Test basic statistics calculation."""
        worst_videos, sensitive_videos = calculate_stats(sample_video_results)
        
        assert len(worst_videos) > 0
        assert len(sensitive_videos) > 0


class TestEscapeLatex:
    """Tests for escape_latex function."""
    
    def test_escape_latex_special_chars(self):
        """Test escaping special LaTeX characters."""
        text = "Test & % $ # ^ _ { } ~ \\"
        escaped = escape_latex(text)
        
        assert '\\&' in escaped
        assert '\\%' in escaped
        assert '\\$' in escaped
        assert '\\#' in escaped
        assert '\\_' in escaped
    
    def test_escape_latex_none(self):
        """Test escaping None value."""
        result = escape_latex(None)
        assert result == ""


class TestGenerateBarbellPlotPgfplots:
    """Tests for generate_barbell_plot_pgfplots function."""
    
    def test_generate_barbell_plot_basic(self):
        """Test generating a basic barbell plot."""
        metric_data = {'5': 0.8, '10': 0.85, '15': 0.9}
        windows = ['5', '10', '15']
        best_window = '15'
        
        plot_code = generate_barbell_plot_pgfplots(metric_data, 'Test Metric', best_window, windows)
        
        assert plot_code != ""
        assert 'tikzpicture' in plot_code
        assert 'axis' in plot_code
    
    def test_generate_barbell_plot_empty(self):
        """Test generating plot with empty data."""
        plot_code = generate_barbell_plot_pgfplots({}, 'Test', None, [])
        
        assert plot_code == ""


class TestGenerateLollipopPlotPgfplots:
    """Tests for generate_lollipop_plot_pgfplots function."""
    
    def test_generate_lollipop_plot_basic(self, sample_video_results):
        """Test generating a basic lollipop plot."""
        windows = ['5', '10']
        
        plot_code = generate_lollipop_plot_pgfplots(
            sample_video_results,
            'test_video_1.mp4',
            'f1_behavior',
            windows
        )
        
        assert plot_code != ""
        assert 'tikzpicture' in plot_code
    
    def test_generate_lollipop_plot_empty(self):
        """Test generating plot with empty data."""
        plot_code = generate_lollipop_plot_pgfplots([], 'test_video', 'f1_behavior', [])
        
        assert plot_code == ""

