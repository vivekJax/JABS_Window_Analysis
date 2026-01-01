"""Unit tests for parse_window_results.py"""
import pytest
from pathlib import Path
import csv
import sys

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'scripts'))

from parse_window_results import (
    parse_window_size,
    parse_video_row,
    parse_summary_stats,
    parse_feature_importance,
    parse_file
)


class TestParseWindowSize:
    """Tests for parse_window_size function."""
    
    def test_parse_window_size_basic(self):
        """Test parsing basic window size."""
        assert parse_window_size("Window 5") == 5
        assert parse_window_size("Window 10") == 10
        assert parse_window_size("Window 15 frames") == 15
    
    def test_parse_window_size_case_insensitive(self):
        """Test case insensitive parsing."""
        assert parse_window_size("window 20") == 20
        assert parse_window_size("WINDOW 25") == 25
    
    def test_parse_window_size_no_match(self):
        """Test parsing with no window size."""
        assert parse_window_size("Some other text") is None
        assert parse_window_size("") is None


class TestParseVideoRow:
    """Tests for parse_video_row function."""
    
    def test_parse_video_row_complete(self):
        """Test parsing a complete video row."""
        line = "1 0.8234 0.8500 0.8000 0.8400 0.8100 0.8450 0.8050 test_video_1.mp4 [0]"
        result = parse_video_row(line, 5)
        
        assert result is not None
        assert result['video_id'] == '1'
        assert result['window_size'] == '5'
        assert result['accuracy'] == '0.8234'
        assert result['precision_not_behavior'] == '0.8500'
        assert result['precision_behavior'] == '0.8000'
        assert result['recall_not_behavior'] == '0.8400'
        assert result['recall_behavior'] == '0.8100'
        assert result['f1_not_behavior'] == '0.8450'
        assert result['f1_behavior'] == '0.8050'
        assert result['video_name'] == 'test_video_1.mp4'
        assert result['identity'] == '0'
    
    def test_parse_video_row_with_long_name(self):
        """Test parsing video row with long video name."""
        line = "2 0.7500 0.7600 0.7400 0.7500 0.7300 0.7550 0.7350 very_long_video_name_with_path.mp4 [1]"
        result = parse_video_row(line, 10)
        
        assert result is not None
        assert result['video_id'] == '2'
        assert result['window_size'] == '10'
        assert result['identity'] == '1'
    
    def test_parse_video_row_incomplete(self):
        """Test parsing incomplete video row."""
        line = "1 0.8234 0.8500"
        result = parse_video_row(line, 5)
        assert result is None
    
    def test_parse_video_row_empty(self):
        """Test parsing empty line."""
        result = parse_video_row("", 5)
        assert result is None


class TestParseSummaryStats:
    """Tests for parse_summary_stats function."""
    
    def test_parse_summary_stats_complete(self):
        """Test parsing complete summary statistics."""
        lines = [
            "Window Size: 5",
            "Mean Accuracy: 0.7867",
            "SD Accuracy: 0.0517",
            "Mean F1 (Behavior): 0.7700",
            "SD F1 (Behavior): 0.0495",
            "Mean F1 (Not Behavior): 0.8000",
            "SD F1 (Not Behavior): 0.0636"
        ]
        
        result = parse_summary_stats(lines, 5)
        
        assert result is not None
        assert result['window_size'] == '5'
        assert result['mean_accuracy'] == '0.7867'
        assert result['sd_accuracy'] == '0.0517'
        assert result['mean_f1_behavior'] == '0.7700'
        assert result['sd_f1_behavior'] == '0.0495'
        assert result['mean_f1_not_behavior'] == '0.8000'
        assert result['sd_f1_not_behavior'] == '0.0636'
    
    def test_parse_summary_stats_missing_fields(self):
        """Test parsing summary stats with missing fields."""
        lines = [
            "Window Size: 10",
            "Mean Accuracy: 0.8609"
        ]
        
        result = parse_summary_stats(lines, 10)
        # Should still return a dict, but with None/empty values for missing fields
        assert result is not None
        assert result['window_size'] == '10'
        assert result['mean_accuracy'] == '0.8609'


class TestParseFeatureImportance:
    """Tests for parse_feature_importance function."""
    
    def test_parse_feature_importance_basic(self):
        """Test parsing basic feature importance."""
        lines = [
            "1. feature_1 0.1234",
            "2. feature_2 0.0987",
            "3. feature_3 0.0765"
        ]
        
        results = parse_feature_importance(lines, 5)
        
        assert len(results) == 3
        assert results[0]['window_size'] == '5'
        assert results[0]['rank'] == '1'
        assert results[0]['feature_name'] == 'feature_1'
        assert results[0]['importance'] == '0.1234'
    
    def test_parse_feature_importance_empty(self):
        """Test parsing empty feature importance."""
        results = parse_feature_importance([], 5)
        assert results == []


class TestParseFile:
    """Tests for parse_file function."""
    
    def test_parse_file_complete(self, temp_dir, sample_window_scan_text):
        """Test parsing a complete file."""
        # Create test file
        test_file = temp_dir / 'test_scan.txt'
        test_file.write_text(sample_window_scan_text)
        
        # Parse file
        video_results, summary_stats, feature_importance, metadata = parse_file(test_file)
        
        # Check results
        assert len(video_results) > 0
        assert len(summary_stats) > 0
        assert isinstance(feature_importance, list)
        assert isinstance(metadata, dict)
        
        # Check video results structure
        assert 'window_size' in video_results[0]
        assert 'video_name' in video_results[0]
        assert 'accuracy' in video_results[0]
        
        # Check summary stats structure
        assert 'window_size' in summary_stats[0]
        assert 'mean_accuracy' in summary_stats[0]
    
    def test_parse_file_nonexistent(self):
        """Test parsing nonexistent file."""
        with pytest.raises(FileNotFoundError):
            parse_file(Path('nonexistent_file.txt'))
    
    def test_parse_file_empty(self, temp_dir):
        """Test parsing empty file."""
        test_file = temp_dir / 'empty.txt'
        test_file.write_text("")
        
        video_results, summary_stats, feature_importance, metadata = parse_file(test_file)
        
        assert video_results == []
        assert summary_stats == []
        assert feature_importance == []

