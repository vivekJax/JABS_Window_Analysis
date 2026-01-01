"""Unit tests for generate_html_report.py"""
import pytest
import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'scripts'))

from generate_html_report import (
    load_csv,
    calculate_stats,
    find_best_values,
    create_barbell_plot,
    calculate_boxplot_stats,
    escape_html
)


class TestLoadCSV:
    """Tests for load_csv function."""
    
    def test_load_csv_valid(self, create_test_csv, sample_video_results):
        """Test loading a valid CSV file."""
        csv_file = create_test_csv('test.csv', sample_video_results)
        
        data = load_csv(csv_file)
        
        assert len(data) == 3
        assert data[0]['window_size'] == '5'
        assert data[0]['video_name'] == 'test_video_1.mp4'
    
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
        
        # Check structure
        assert 'video_name' in worst_videos[0]
        assert 'mean_accuracy' in worst_videos[0]
        assert 'cv' in sensitive_videos[0]
    
    def test_calculate_stats_empty(self):
        """Test statistics calculation with empty data."""
        worst_videos, sensitive_videos = calculate_stats([])
        
        assert worst_videos == []
        assert sensitive_videos == []
    
    def test_calculate_stats_sorts_correctly(self, sample_video_results):
        """Test that worst videos are sorted correctly."""
        worst_videos, _ = calculate_stats(sample_video_results)
        
        # Worst videos should be sorted by mean_accuracy (ascending)
        if len(worst_videos) > 1:
            assert worst_videos[0]['mean_accuracy'] <= worst_videos[1]['mean_accuracy']


class TestFindBestValues:
    """Tests for find_best_values function."""
    
    def test_find_best_values_basic(self, sample_summary_stats):
        """Test finding best values from summary stats."""
        best = find_best_values(sample_summary_stats)
        
        assert 'mean_accuracy' in best
        assert 'mean_f1_behavior' in best
        assert 'window' in best['mean_accuracy']
        assert 'value' in best['mean_accuracy']
    
    def test_find_best_values_empty(self):
        """Test finding best values with empty data."""
        best = find_best_values([])
        
        assert best == {}


class TestCreateBarbellPlot:
    """Tests for create_barbell_plot function."""
    
    def test_create_barbell_plot_basic(self):
        """Test creating a basic barbell plot."""
        metric_values = {'5': 0.8, '10': 0.85, '15': 0.9}
        window_sizes = ['5', '10', '15']
        best_window = '15'
        
        plot_svg = create_barbell_plot('test_metric', metric_values, window_sizes, best_window)
        
        assert plot_svg != ""
        assert 'svg' in plot_svg.lower()
        assert '15' in plot_svg  # Best window should be highlighted
    
    def test_create_barbell_plot_empty(self):
        """Test creating plot with empty data."""
        plot_svg = create_barbell_plot('test', {}, [], None)
        
        assert plot_svg == ""


class TestCalculateBoxplotStats:
    """Tests for calculate_boxplot_stats function."""
    
    def test_calculate_boxplot_stats_basic(self):
        """Test calculating basic boxplot statistics."""
        values = [0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0]
        
        stats = calculate_boxplot_stats(values)
        
        assert stats is not None
        assert 'median' in stats
        assert 'q1' in stats
        assert 'q3' in stats
        assert stats['median'] == 0.85
    
    def test_calculate_boxplot_stats_empty(self):
        """Test calculating boxplot stats with empty data."""
        stats = calculate_boxplot_stats([])
        
        assert stats is None


class TestEscapeHTML:
    """Tests for escape_html function."""
    
    def test_escape_html_special_chars(self):
        """Test escaping special HTML characters."""
        from generate_html_report import escape_html
        
        text = "Test & <test> \"quote\""
        escaped = escape_html(text)
        
        assert '&amp;' in escaped
        assert '&lt;' in escaped
        assert '&quot;' in escaped

