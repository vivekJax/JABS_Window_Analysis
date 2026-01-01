"""Unit tests for validate_conversion.py"""
import pytest
import pandas as pd
import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'scripts'))

from validate_conversion import (
    validate_video_consistency,
    validate_row_counts,
    validate_numeric_ranges,
    validate_summary_stats
)


class TestValidateVideoConsistency:
    """Tests for validate_video_consistency function."""
    
    def test_validate_consistent_videos(self):
        """Test validation with consistent video sets across windows."""
        data = {
            'window_size': ['5', '5', '10', '10'],
            'video_name': ['video1.mp4', 'video2.mp4', 'video1.mp4', 'video2.mp4'],
            'identity': ['0', '0', '0', '0'],
            'accuracy': [0.8, 0.9, 0.85, 0.95]
        }
        df = pd.DataFrame(data)
        
        result = validate_video_consistency(df)
        
        assert result['all_windows_have_same_video_identity_pairs'] is True
        assert result['video_identity_counts_per_window']['5'] == 2
        assert result['video_identity_counts_per_window']['10'] == 2
    
    def test_validate_inconsistent_videos(self):
        """Test validation with inconsistent video sets."""
        data = {
            'window_size': ['5', '5', '10'],
            'video_name': ['video1.mp4', 'video2.mp4', 'video1.mp4'],
            'identity': ['0', '0', '0'],
            'accuracy': [0.8, 0.9, 0.85]
        }
        df = pd.DataFrame(data)
        
        result = validate_video_consistency(df)
        
        assert result['all_windows_have_same_video_identity_pairs'] is False
    
    def test_validate_empty_dataframe(self):
        """Test validation with empty dataframe."""
        df = pd.DataFrame()
        
        result = validate_video_consistency(df)
        
        assert result['all_windows_have_same_video_identity_pairs'] is False


class TestValidateRowCounts:
    """Tests for validate_row_counts function."""
    
    def test_validate_row_counts_consistent(self):
        """Test validation with consistent row counts."""
        video_data = {
            'window_size': ['5', '5', '10', '10'],
            'video_name': ['video1.mp4', 'video2.mp4', 'video1.mp4', 'video2.mp4'],
            'accuracy': [0.8, 0.9, 0.85, 0.95]
        }
        video_df = pd.DataFrame(video_data)
        
        summary_data = {
            'window_size': ['5', '10'],
            'mean_accuracy': [0.85, 0.90]
        }
        summary_df = pd.DataFrame(summary_data)
        
        feature_df = pd.DataFrame()
        
        result = validate_row_counts(video_df, summary_df, feature_df)
        
        assert result['video_results_count'] == 4
        assert result['summary_stats_count'] == 2
    
    def test_validate_row_counts_empty(self):
        """Test validation with empty dataframes."""
        video_df = pd.DataFrame()
        summary_df = pd.DataFrame()
        feature_df = pd.DataFrame()
        
        result = validate_row_counts(video_df, summary_df, feature_df)
        
        assert result['video_results_count'] == 0
        assert result['summary_stats_count'] == 0


class TestValidateNumericRanges:
    """Tests for validate_numeric_ranges function."""
    
    def test_validate_numeric_ranges_valid(self):
        """Test validation with valid numeric ranges."""
        data = {
            'accuracy': [0.8, 0.9, 0.85],
            'f1_behavior': [0.75, 0.85, 0.80],
            'precision_behavior': [0.70, 0.90, 0.80]
        }
        df = pd.DataFrame(data)
        
        result = validate_numeric_ranges(df)
        
        assert result['all_values_in_range'] is True
    
    def test_validate_numeric_ranges_invalid(self):
        """Test validation with invalid numeric ranges."""
        data = {
            'accuracy': [1.5, 0.9, -0.1],  # Out of range values
            'f1_behavior': [0.75, 0.85, 0.80]
        }
        df = pd.DataFrame(data)
        
        result = validate_numeric_ranges(df)
        
        assert result['all_values_in_range'] is False
        assert len(result['out_of_range_values']) > 0


class TestValidateSummaryStats:
    """Tests for validate_summary_stats function."""
    
    def test_validate_summary_stats_consistent(self):
        """Test validation with consistent summary stats."""
        video_data = {
            'window_size': ['5', '5', '5'],
            'accuracy': [0.8, 0.85, 0.90],
            'f1_behavior': [0.75, 0.80, 0.85]
        }
        video_df = pd.DataFrame(video_data)
        
        summary_data = {
            'window_size': ['5'],
            'mean_accuracy': [0.85],
            'sd_accuracy': [0.05],
            'mean_f1_behavior': [0.80],
            'sd_f1_behavior': [0.05]
        }
        summary_df = pd.DataFrame(summary_data)
        
        result = validate_summary_stats(video_df, summary_df)
        
        # Should pass basic structure checks
        assert 'summary_stats_match_video_data' in result

