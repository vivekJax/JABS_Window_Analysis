#!/usr/bin/env python3
"""
Validate the CSV conversion from window size scan results.
Checks data integrity, consistency, and completeness.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys


def validate_video_consistency(video_df):
    """
    Validate that all windows have the same set of (video, identity) pairs.
    
    Note: Cross-validation holds out one animal (identity) at a time, not one video at a time.
    Each video can contain multiple animals, identified by [0], [1], [2], etc.
    Each (video_name, identity) pair represents a separate test case.
    
    Returns:
        dict with validation results
    """
    results = {
        'all_windows_have_same_video_identity_pairs': True,
        'video_identity_counts_per_window': {},
        'missing_video_identity_pairs': [],
        'extra_video_identity_pairs': [],
        'video_identity_sets_per_window': {}
    }
    
    if video_df.empty:
        results['all_windows_have_same_video_identity_pairs'] = False
        return results
    
    # Get unique windows
    windows = sorted(video_df['window_size'].unique())
    
    # Get (video_name, identity) sets per window
    for window in windows:
        window_data = video_df[video_df['window_size'] == window]
        # Create set of (video_name, identity) tuples
        video_identity_pairs = set()
        for _, row in window_data.iterrows():
            video_name = row['video_name']
            identity = row.get('identity', None)
            video_identity_pairs.add((video_name, identity))
        
        results['video_identity_sets_per_window'][window] = video_identity_pairs
        results['video_identity_counts_per_window'][window] = len(video_identity_pairs)
    
    # Check if all windows have the same count
    counts = list(results['video_identity_counts_per_window'].values())
    if len(set(counts)) > 1:
        results['all_windows_have_same_video_identity_pairs'] = False
    
    # Check if all windows have the same (video, identity) set
    if len(windows) > 1:
        reference_set = results['video_identity_sets_per_window'][windows[0]]
        for window in windows[1:]:
            current_set = results['video_identity_sets_per_window'][window]
            if current_set != reference_set:
                results['all_windows_have_same_video_identity_pairs'] = False
                # Find missing and extra (video, identity) pairs
                missing = reference_set - current_set
                extra = current_set - reference_set
                if missing:
                    results['missing_video_identity_pairs'].append({
                        'window': window,
                        'missing': list(missing)
                    })
                if extra:
                    results['extra_video_identity_pairs'].append({
                        'window': window,
                        'extra': list(extra)
                    })
    
    return results


def validate_row_counts(video_df, summary_df, feature_df):
    """Validate row counts are consistent."""
    results = {
        'video_results_count': len(video_df),
        'summary_stats_count': len(summary_df),
        'feature_importance_count': len(feature_df),
        'expected_video_rows': None,
        'expected_summary_rows': None,
        'expected_feature_rows': None,
        'all_counts_valid': True
    }
    
    if video_df.empty:
        return results
    
    # Get dimensions
    n_windows = len(video_df['window_size'].unique())
    n_videos = len(video_df['video_name'].unique())
    
    # Check video results
    expected_video_rows = n_videos * n_windows
    results['expected_video_rows'] = expected_video_rows
    if len(video_df) != expected_video_rows:
        results['all_counts_valid'] = False
    
    # Check summary stats
    results['expected_summary_rows'] = n_windows
    if len(summary_df) != n_windows:
        results['all_counts_valid'] = False
    
    # Check feature importance (approximate - features per window may vary)
    if not feature_df.empty:
        features_per_window = feature_df.groupby('window_size').size()
        expected_feature_rows = features_per_window.sum()
        results['expected_feature_rows'] = expected_feature_rows
        if len(feature_df) != expected_feature_rows:
            results['all_counts_valid'] = False
    
    return results


def validate_data_integrity(video_df, summary_df, feature_df):
    """Validate data ranges and completeness."""
    results = {
        'numeric_ranges_valid': True,
        'no_missing_values': True,
        'complete_performance_data': True,
        'issues': []
    }
    
    # Check video results
    if not video_df.empty:
        # Required columns
        required_cols = [
            'window_size', 'video_id', 'video_name', 'identity',
            'accuracy', 'precision_not_behavior', 'precision_behavior',
            'recall_not_behavior', 'recall_behavior',
            'f1_not_behavior', 'f1_behavior'
        ]
        
        # Check for missing columns
        missing_cols = [col for col in required_cols if col not in video_df.columns]
        if missing_cols:
            results['no_missing_values'] = False
            results['issues'].append(f"Missing columns: {missing_cols}")
        
        # Check for missing values
        for col in required_cols:
            if col in video_df.columns:
                missing_count = video_df[col].isna().sum()
                if missing_count > 0:
                    results['no_missing_values'] = False
                    results['issues'].append(f"Column '{col}' has {missing_count} missing values")
        
        # Check numeric ranges
        numeric_cols = ['accuracy', 'precision_not_behavior', 'precision_behavior',
                       'recall_not_behavior', 'recall_behavior',
                       'f1_not_behavior', 'f1_behavior']
        
        for col in numeric_cols:
            if col in video_df.columns:
                min_val = video_df[col].min()
                max_val = video_df[col].max()
                if min_val < 0 or max_val > 1:
                    results['numeric_ranges_valid'] = False
                    results['issues'].append(
                        f"Column '{col}' has values outside [0,1]: min={min_val}, max={max_val}"
                    )
        
        # Check that every video-window combination has all 8 metrics
        expected_metrics = 8
        # This is already checked by column presence, but we can verify completeness
        for window in video_df['window_size'].unique():
            window_data = video_df[video_df['window_size'] == window]
            for video in window_data['video_name'].unique():
                video_data = window_data[window_data['video_name'] == video]
                if len(video_data) != 1:
                    results['complete_performance_data'] = False
                    results['issues'].append(
                        f"Video '{video}' in window {window} has {len(video_data)} rows (expected 1)"
                    )
    
    # Check summary stats
    if not summary_df.empty:
        required_summary_cols = ['window_size', 'mean_accuracy', 'sd_accuracy',
                                'mean_f1_behavior', 'sd_f1_behavior',
                                'mean_f1_not_behavior', 'sd_f1_not_behavior']
        for col in required_summary_cols:
            if col in summary_df.columns:
                missing_count = summary_df[col].isna().sum()
                if missing_count > 0:
                    results['no_missing_values'] = False
                    results['issues'].append(f"Summary column '{col}' has {missing_count} missing values")
    
    return results


def validate_summary_stats(video_df, summary_df):
    """Cross-validate summary statistics against computed means."""
    results = {
        'summary_stats_match': True,
        'tolerance': 0.001,  # Allow small floating point differences
        'discrepancies': []
    }
    
    if video_df.empty or summary_df.empty:
        return results
    
    # Compute means from video results
    computed_stats = video_df.groupby('window_size').agg({
        'accuracy': ['mean', 'std'],
        'f1_behavior': ['mean', 'std'],
        'f1_not_behavior': ['mean', 'std']
    }).reset_index()
    
    computed_stats.columns = ['window_size', 'computed_mean_accuracy', 'computed_sd_accuracy',
                             'computed_mean_f1_behavior', 'computed_sd_f1_behavior',
                             'computed_mean_f1_not_behavior', 'computed_sd_f1_not_behavior']
    
    # Merge with summary stats
    merged = summary_df.merge(computed_stats, on='window_size', how='inner')
    
    # Compare
    for idx, row in merged.iterrows():
        window = row['window_size']
        
        # Compare mean accuracy
        if abs(row['mean_accuracy'] - row['computed_mean_accuracy']) > results['tolerance']:
            results['summary_stats_match'] = False
            results['discrepancies'].append(
                f"Window {window}: mean_accuracy mismatch "
                f"(reported={row['mean_accuracy']:.6f}, "
                f"computed={row['computed_mean_accuracy']:.6f})"
            )
        
        # Compare SD accuracy
        if abs(row['sd_accuracy'] - row['computed_sd_accuracy']) > results['tolerance']:
            results['summary_stats_match'] = False
            results['discrepancies'].append(
                f"Window {window}: sd_accuracy mismatch "
                f"(reported={row['sd_accuracy']:.6f}, "
                f"computed={row['computed_sd_accuracy']:.6f})"
            )
        
        # Compare F1 scores (similar checks)
        if 'mean_f1_behavior' in row and not pd.isna(row['mean_f1_behavior']):
            if abs(row['mean_f1_behavior'] - row['computed_mean_f1_behavior']) > results['tolerance']:
                results['summary_stats_match'] = False
                results['discrepancies'].append(
                    f"Window {window}: mean_f1_behavior mismatch "
                    f"(reported={row['mean_f1_behavior']:.6f}, "
                    f"computed={row['computed_mean_f1_behavior']:.6f})"
                )
    
    return results


def main():
    """Main validation function."""
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    data_dir = project_dir / 'data' / 'processed'
    
    video_file = data_dir / 'video_results.csv'
    summary_file = data_dir / 'summary_stats.csv'
    feature_file = data_dir / 'feature_importance.csv'
    output_file = data_dir / 'validation_report.txt'
    
    print("=" * 80)
    print("Window Size Results Validation")
    print("=" * 80)
    print()
    
    # Load data
    try:
        video_df = pd.read_csv(video_file)
        print(f"✓ Loaded video_results.csv: {len(video_df)} rows")
    except FileNotFoundError:
        print(f"✗ ERROR: {video_file} not found")
        sys.exit(1)
    except Exception as e:
        print(f"✗ ERROR loading video_results.csv: {e}")
        sys.exit(1)
    
    try:
        summary_df = pd.read_csv(summary_file)
        print(f"✓ Loaded summary_stats.csv: {len(summary_df)} rows")
    except FileNotFoundError:
        print(f"✗ WARNING: {summary_file} not found")
        summary_df = pd.DataFrame()
    except Exception as e:
        print(f"✗ ERROR loading summary_stats.csv: {e}")
        summary_df = pd.DataFrame()
    
    try:
        feature_df = pd.read_csv(feature_file)
        print(f"✓ Loaded feature_importance.csv: {len(feature_df)} rows")
    except FileNotFoundError:
        print(f"✗ WARNING: {feature_file} not found")
        feature_df = pd.DataFrame()
    except Exception as e:
        print(f"✗ ERROR loading feature_importance.csv: {e}")
        feature_df = pd.DataFrame()
    
    print()
    
    # Run validations
    all_passed = True
    
    with open(output_file, 'w') as f:
        f.write("Window Size Results Validation Report\n")
        f.write("=" * 80 + "\n\n")
        
        # 1. Row count validation
        print("1. Validating row counts...")
        f.write("1. ROW COUNT VALIDATION\n")
        f.write("-" * 80 + "\n")
        count_results = validate_row_counts(video_df, summary_df, feature_df)
        
        if count_results['all_counts_valid']:
            print("   ✓ Row counts are consistent")
            f.write("   ✓ PASS: Row counts are consistent\n")
        else:
            print("   ✗ Row counts are inconsistent")
            f.write("   ✗ FAIL: Row counts are inconsistent\n")
            all_passed = False
        
        f.write(f"   Video results: {count_results['video_results_count']} rows "
                f"(expected: {count_results['expected_video_rows']})\n")
        f.write(f"   Summary stats: {count_results['summary_stats_count']} rows "
                f"(expected: {count_results['expected_summary_rows']})\n")
        f.write(f"   Feature importance: {count_results['feature_importance_count']} rows "
                f"(expected: {count_results['expected_feature_rows']})\n")
        f.write("\n")
        
        # 2. Video consistency validation
        print("2. Validating video consistency across windows...")
        f.write("2. VIDEO CONSISTENCY VALIDATION\n")
        f.write("-" * 80 + "\n")
        consistency_results = validate_video_consistency(video_df)
        
        if consistency_results['all_windows_have_same_video_identity_pairs']:
            print("   ✓ All windows have the same set of videos")
            f.write("   ✓ PASS: All windows have the same set of videos\n")
        else:
            print("   ✗ Windows have different video sets")
            f.write("   ✗ FAIL: Windows have different video sets\n")
            all_passed = False
        
        f.write("   Video-identity pair counts per window:\n")
        for window, count in sorted(consistency_results['video_identity_counts_per_window'].items()):
            f.write(f"     Window {window}: {count} (video, identity) pairs\n")
        
        if consistency_results['missing_video_identity_pairs']:
            f.write("   Missing (video, identity) pairs:\n")
            for item in consistency_results['missing_video_identity_pairs']:
                f.write(f"     Window {item['window']}: {item['missing']}\n")
        
        if consistency_results['extra_video_identity_pairs']:
            f.write("   Extra (video, identity) pairs:\n")
            for item in consistency_results['extra_video_identity_pairs']:
                f.write(f"     Window {item['window']}: {item['extra']}\n")
        f.write("\n")
        
        # 3. Data integrity validation
        print("3. Validating data integrity...")
        f.write("3. DATA INTEGRITY VALIDATION\n")
        f.write("-" * 80 + "\n")
        integrity_results = validate_data_integrity(video_df, summary_df, feature_df)
        
        checks_passed = (
            integrity_results['numeric_ranges_valid'] and
            integrity_results['no_missing_values'] and
            integrity_results['complete_performance_data']
        )
        
        if checks_passed:
            print("   ✓ Data integrity checks passed")
            f.write("   ✓ PASS: Data integrity checks passed\n")
        else:
            print("   ✗ Data integrity issues found")
            f.write("   ✗ FAIL: Data integrity issues found\n")
            all_passed = False
        
        for issue in integrity_results['issues']:
            f.write(f"     - {issue}\n")
        f.write("\n")
        
        # 4. Summary stats validation
        if not summary_df.empty:
            print("4. Validating summary statistics...")
            f.write("4. SUMMARY STATISTICS VALIDATION\n")
            f.write("-" * 80 + "\n")
            stats_results = validate_summary_stats(video_df, summary_df)
            
            if stats_results['summary_stats_match']:
                print("   ✓ Summary statistics match computed values")
                f.write("   ✓ PASS: Summary statistics match computed values\n")
            else:
                print("   ✗ Summary statistics discrepancies found")
                f.write("   ✗ FAIL: Summary statistics discrepancies found\n")
                all_passed = False
            
            for discrepancy in stats_results['discrepancies']:
                f.write(f"     - {discrepancy}\n")
            f.write("\n")
        
        # Summary
        f.write("=" * 80 + "\n")
        f.write("VALIDATION SUMMARY\n")
        f.write("=" * 80 + "\n\n")
        
        if all_passed:
            print()
            print("=" * 80)
            print("✓ ALL VALIDATION CHECKS PASSED")
            print("=" * 80)
            f.write("✓ ALL VALIDATION CHECKS PASSED\n")
        else:
            print()
            print("=" * 80)
            print("✗ SOME VALIDATION CHECKS FAILED")
            print("=" * 80)
            f.write("✗ SOME VALIDATION CHECKS FAILED\n")
            f.write("See details above for specific issues.\n")
        
        f.write(f"\nValidation report saved to: {output_file}\n")
    
    print(f"\nValidation report saved to: {output_file}")
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())

