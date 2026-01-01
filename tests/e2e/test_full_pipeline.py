"""End-to-end tests for the full pipeline."""
import pytest
import sys
from pathlib import Path
import csv
import shutil
import tempfile

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'scripts'))

from parse_window_results import parse_file, main as parse_main
from validate_conversion import main as validate_main
from generate_html_report import main as html_main
from generate_latex_report import main as latex_main


class TestFullPipeline:
    """End-to-end tests for the complete pipeline."""
    
    def test_full_pipeline_parsing(self, project_root, temp_dir):
        """Test the full parsing pipeline."""
        # Copy input file to temp directory
        input_file = project_root / 'data' / 'raw' / 'Window size scan.txt'
        if not input_file.exists():
            pytest.skip("Input file not found")
        
        temp_input = temp_dir / 'input.txt'
        shutil.copy(input_file, temp_input)
        
        # Modify parse_file to use temp directory
        # This is a simplified test - in practice, we'd mock or refactor
        video_results, summary_stats, feature_importance, metadata = parse_file(temp_input)
        
        # Verify outputs
        assert len(video_results) > 0, "Should have video results"
        assert len(summary_stats) > 0, "Should have summary stats"
        assert isinstance(feature_importance, list), "Feature importance should be a list"
        assert isinstance(metadata, dict), "Metadata should be a dict"
        
        # Verify structure
        assert 'window_size' in video_results[0]
        assert 'video_name' in video_results[0]
        assert 'accuracy' in video_results[0]
        assert 'mean_accuracy' in summary_stats[0]
    
    def test_csv_output_structure(self, project_root):
        """Test that CSV outputs have correct structure."""
        video_file = project_root / 'data' / 'processed' / 'video_results.csv'
        summary_file = project_root / 'data' / 'processed' / 'summary_stats.csv'
        
        if not video_file.exists():
            pytest.skip("Video results CSV not found - run parsing first")
        
        # Check video results CSV
        with open(video_file, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
            assert len(rows) > 0, "Should have video result rows"
            
            # Check required columns
            required_cols = ['window_size', 'video_name', 'accuracy', 'f1_behavior']
            for col in required_cols:
                assert col in rows[0], f"Missing required column: {col}"
        
        # Check summary stats CSV
        if summary_file.exists():
            with open(summary_file, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                
                assert len(rows) > 0, "Should have summary stat rows"
                
                # Check required columns
                required_cols = ['window_size', 'mean_accuracy', 'mean_f1_behavior']
                for col in required_cols:
                    assert col in rows[0], f"Missing required column: {col}"
    
    def test_html_report_generation(self, project_root):
        """Test HTML report generation."""
        # Check if required input files exist
        video_file = project_root / 'data' / 'processed' / 'video_results.csv'
        summary_file = project_root / 'data' / 'processed' / 'summary_stats.csv'
        
        if not video_file.exists() or not summary_file.exists():
            pytest.skip("Required CSV files not found - run parsing first")
        
        # Run HTML report generation (this will create the report)
        # In a real test, we'd capture output and verify
        try:
            html_main()
            
            # Check output file exists
            html_file = project_root / 'reports' / 'window_size_analysis_report.html'
            assert html_file.exists(), "HTML report should be created"
            
            # Check file is not empty
            assert html_file.stat().st_size > 0, "HTML report should not be empty"
            
            # Check for key content
            content = html_file.read_text()
            assert 'Window Size Analysis' in content, "Should contain report title"
            assert '<html' in content.lower(), "Should be valid HTML"
            
        except Exception as e:
            pytest.fail(f"HTML report generation failed: {e}")
    
    def test_latex_report_generation(self, project_root):
        """Test LaTeX report generation."""
        # Check if required input files exist
        video_file = project_root / 'data' / 'processed' / 'video_results.csv'
        summary_file = project_root / 'data' / 'processed' / 'summary_stats.csv'
        
        if not video_file.exists() or not summary_file.exists():
            pytest.skip("Required CSV files not found - run parsing first")
        
        # Run LaTeX report generation
        try:
            latex_main()
            
            # Check output file exists
            tex_file = project_root / 'reports' / 'window_size_analysis_report.tex'
            assert tex_file.exists(), "LaTeX report should be created"
            
            # Check file is not empty
            assert tex_file.stat().st_size > 0, "LaTeX report should not be empty"
            
            # Check for key content
            content = tex_file.read_text()
            assert '\\documentclass' in content, "Should be valid LaTeX"
            assert 'Window Size Analysis' in content, "Should contain report title"
            
        except Exception as e:
            pytest.fail(f"LaTeX report generation failed: {e}")
    
    def test_data_consistency_across_pipeline(self, project_root):
        """Test that data remains consistent across the pipeline."""
        video_file = project_root / 'data' / 'processed' / 'video_results.csv'
        summary_file = project_root / 'data' / 'processed' / 'summary_stats.csv'
        
        if not video_file.exists() or not summary_file.exists():
            pytest.skip("Required CSV files not found")
        
        # Load data
        video_data = []
        with open(video_file, 'r') as f:
            reader = csv.DictReader(f)
            video_data = list(reader)
        
        summary_data = []
        with open(summary_file, 'r') as f:
            reader = csv.DictReader(f)
            summary_data = list(reader)
        
        # Check window sizes match
        video_windows = set(row['window_size'] for row in video_data)
        summary_windows = set(row['window_size'] for row in summary_data)
        
        assert video_windows == summary_windows, "Window sizes should match between video and summary data"
        
        # Check that all videos have required metrics
        required_metrics = ['accuracy', 'f1_behavior', 'f1_not_behavior']
        for row in video_data:
            for metric in required_metrics:
                assert metric in row, f"Missing metric: {metric}"
                # Check value is numeric
                try:
                    float(row[metric])
                except ValueError:
                    pytest.fail(f"Non-numeric value for {metric}: {row[metric]}")

