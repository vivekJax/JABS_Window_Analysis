"""Pytest configuration and shared fixtures."""
import pytest
import csv
from pathlib import Path
import tempfile
import shutil


@pytest.fixture
def project_root():
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def test_data_dir(project_root):
    """Return the test data directory."""
    return project_root / 'tests' / 'fixtures'


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test outputs."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_video_results():
    """Sample video results data for testing."""
    return [
        {
            'window_size': '5',
            'video_id': '1',
            'video_name': 'test_video_1.mp4',
            'identity': '0',
            'accuracy': '0.8234',
            'precision_not_behavior': '0.8500',
            'precision_behavior': '0.8000',
            'recall_not_behavior': '0.8400',
            'recall_behavior': '0.8100',
            'f1_not_behavior': '0.8450',
            'f1_behavior': '0.8050'
        },
        {
            'window_size': '10',
            'video_id': '1',
            'video_name': 'test_video_1.mp4',
            'identity': '0',
            'accuracy': '0.8717',
            'precision_not_behavior': '0.8800',
            'precision_behavior': '0.8600',
            'recall_not_behavior': '0.8700',
            'recall_behavior': '0.8500',
            'f1_not_behavior': '0.8750',
            'f1_behavior': '0.8550'
        },
        {
            'window_size': '5',
            'video_id': '2',
            'video_name': 'test_video_2.mp4',
            'identity': '1',
            'accuracy': '0.7500',
            'precision_not_behavior': '0.7600',
            'precision_behavior': '0.7400',
            'recall_not_behavior': '0.7500',
            'recall_behavior': '0.7300',
            'f1_not_behavior': '0.7550',
            'f1_behavior': '0.7350'
        }
    ]


@pytest.fixture
def sample_summary_stats():
    """Sample summary statistics for testing."""
    return [
        {
            'window_size': '5',
            'mean_accuracy': '0.7867',
            'sd_accuracy': '0.0517',
            'mean_f1_behavior': '0.7700',
            'sd_f1_behavior': '0.0495',
            'mean_f1_not_behavior': '0.8000',
            'sd_f1_not_behavior': '0.0636'
        },
        {
            'window_size': '10',
            'mean_accuracy': '0.8717',
            'sd_accuracy': '0.0000',
            'mean_f1_behavior': '0.8550',
            'sd_f1_behavior': '0.0000',
            'mean_f1_not_behavior': '0.8750',
            'sd_f1_not_behavior': '0.0000'
        }
    ]


@pytest.fixture
def create_test_csv(temp_dir):
    """Factory fixture to create test CSV files."""
    def _create_csv(filename, data, fieldnames=None):
        filepath = temp_dir / filename
        if fieldnames is None and data:
            fieldnames = data[0].keys()
        
        with open(filepath, 'w', newline='') as f:
            if data:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
        
        return filepath
    
    return _create_csv


@pytest.fixture
def sample_window_scan_text():
    """Sample window scan text for testing parsing."""
    return """Window 5

Video Results:
video_id accuracy prec_nb prec_b recall_nb recall_b f1_nb f1_b video_name [identity]
1 0.8234 0.8500 0.8000 0.8400 0.8100 0.8450 0.8050 test_video_1.mp4 [0]
2 0.7500 0.7600 0.7400 0.7500 0.7300 0.7550 0.7350 test_video_2.mp4 [1]

Summary Statistics:
Window Size: 5
Mean Accuracy: 0.7867
SD Accuracy: 0.0517
Mean F1 (Behavior): 0.7700
SD F1 (Behavior): 0.0495
Mean F1 (Not Behavior): 0.8000
SD F1 (Not Behavior): 0.0636

Window 10

Video Results:
video_id accuracy prec_nb prec_b recall_nb recall_b f1_nb f1_b video_name [identity]
1 0.8717 0.8800 0.8600 0.8700 0.8500 0.8750 0.8550 test_video_1.mp4 [0]
2 0.8500 0.8600 0.8400 0.8500 0.8300 0.8550 0.8350 test_video_2.mp4 [1]

Summary Statistics:
Window Size: 10
Mean Accuracy: 0.8609
SD Accuracy: 0.0153
Mean F1 (Behavior): 0.8450
SD F1 (Behavior): 0.0141
Mean F1 (Not Behavior): 0.8650
SD F1 (Not Behavior): 0.0141
"""

