#!/usr/bin/env python3
"""
Parse window size cross-validation results from text file.
Extracts video performance metrics, summary statistics, and feature importance.

WHAT THIS SCRIPT DOES:
-----------------------
This script reads a text file containing machine learning experiment results and
extracts structured data from it. The input file contains results from testing
different "window sizes" (how many video frames to analyze at once) for behavior
classification in videos.

In computer vision, a "window" refers to a group of consecutive frames from a video.
For example, a window size of 10 means we analyze 10 frames together to determine
if an animal is performing a behavior (like "turning left"). Different window sizes
can affect how well the computer can detect behaviors.

The script extracts three types of information:
1. Video-level results: How well the classifier performed on each individual video
2. Summary statistics: Average performance across all videos for each window size
3. Feature importance: Which visual features were most important for classification

OUTPUT:
-------
The script creates CSV (Comma-Separated Values) files that can be opened in Excel
or analyzed with other tools:
- video_results.csv: One row per video/window combination
- summary_stats.csv: One row per window size with average metrics
- feature_importance.csv: Top features ranked by importance for each window size
"""

# IMPORT STATEMENTS - These bring in code from Python's standard library
# -------------------------------------------------------------------------
# 're' stands for "regular expressions" - a powerful way to search for patterns in text
# Example: Finding all phone numbers or email addresses in text
import re

# 'csv' provides tools for reading and writing CSV files
# CSV files are like spreadsheets - rows and columns separated by commas
import csv

# 'Path' from pathlib makes working with file paths easier and more reliable
# Instead of "folder/file.txt", we can use Path("folder") / "file.txt"
from pathlib import Path


def parse_window_size(line):
    """
    Extract window size number from a text line.
    
    WHAT IT DOES:
    ------------
    Looks for text like "Window 10" or "Window 15 frames" and extracts the number.
    This tells us which window size the following results are for.
    
    PARAMETERS:
    -----------
    line (str): A single line of text from the input file
               Example: "Window 10" or "Window 15 frames"
    
    RETURNS:
    --------
    int or None: The window size number (e.g., 10, 15, 20) if found,
                 or None if no window size is found in the line
    
    HOW IT WORKS:
    -------------
    Uses "regular expressions" (regex) to find patterns in text.
    The pattern r'Window\s+(\d+)' means:
    - 'Window' - literal text "Window"
    - '\s+' - one or more whitespace characters (spaces, tabs)
    - '(\d+)' - one or more digits (0-9), captured in parentheses
    - re.IGNORECASE - match "window", "Window", or "WINDOW"
    
    Example matches:
    - "Window 10" -> returns 10
    - "Window 15 frames" -> returns 15
    - "window 20" -> returns 20 (case-insensitive)
    - "No window here" -> returns None
    """
    # re.search() looks for the pattern anywhere in the line
    # If found, it returns a "match object" with information about what was found
    match = re.search(r'Window\s+(\d+)', line, re.IGNORECASE)
    
    # If a match was found, extract the number
    if match:
        # match.group(1) gets the first captured group (the digits in parentheses)
        # int() converts the string "10" to the integer 10
        return int(match.group(1))
    
    # If no match was found, return None (Python's way of saying "nothing")
    return None


def parse_video_row(line, window_size):
    """
    Parse a single row of video performance results.
    
    WHAT IT DOES:
    ------------
    Takes a line like:
    "1 0.978528 1.0 0.740741 0.977124 1.0 0.98843 0.851064 video_name.mp4 [0]"
    
    And extracts all the numbers and video information into a dictionary.
    
    WHAT ARE THESE METRICS?
    -----------------------
    In machine learning, we measure how well a classifier (the computer program
    that detects behaviors) performs using several metrics:
    
    - accuracy: Overall percentage of correct predictions (0.0 to 1.0, where 1.0 = 100%)
    - precision: Of the times we said "behavior", how many were actually behaviors?
               High precision = fewer false alarms
    - recall: Of all actual behaviors, how many did we catch?
             High recall = we don't miss many behaviors
    - f1 score: A balance between precision and recall (harmonic mean)
    
    Each metric is calculated separately for:
    - "behavior" class (the animal IS turning left)
    - "not behavior" class (the animal is NOT turning left)
    
    PARAMETERS:
    -----------
    line (str): A single line from the results table
               Format: video_id accuracy prec_nb prec_b recall_nb recall_b f1_nb f1_b video_name [identity]
               Where:
               - video_id: Unique number identifying the video
               - accuracy: Overall accuracy (one number)
               - prec_nb: Precision for "not behavior" class
               - prec_b: Precision for "behavior" class
               - recall_nb: Recall for "not behavior" class
               - recall_b: Recall for "behavior" class
               - f1_nb: F1 score for "not behavior" class
               - f1_b: F1 score for "behavior" class
               - video_name: Name of the video file
               - [identity]: Animal identity number in brackets (e.g., [0], [1])
    
    window_size (int): The window size this result is for (e.g., 10, 15, 20)
    
    RETURNS:
    --------
    dict or None: A dictionary containing all the parsed data, or None if parsing failed
                 Dictionary keys: 'window_size', 'video_id', 'video_name', 'identity',
                                 'accuracy', 'precision_not_behavior', 'precision_behavior',
                                 'recall_not_behavior', 'recall_behavior',
                                 'f1_not_behavior', 'f1_behavior'
    
    HOW IT WORKS:
    -------------
    1. Split the line into individual words/numbers
    2. Extract the first number as video_id
    3. Extract the next 7 numbers as performance metrics
    4. Everything else is the video name (which may contain spaces)
    5. Extract the identity number from brackets [0]
    6. Return everything as a dictionary
    """
    # .strip() removes leading and trailing whitespace (spaces, tabs, newlines)
    # This prevents errors from extra spaces at the start/end of the line
    line = line.strip()
    
    # .split() breaks the line into a list of words, separated by whitespace
    # Example: "1 0.5 0.6 video.mp4" -> ['1', '0.5', '0.6', 'video.mp4']
    parts = line.split()
    
    # We need at least 9 parts: video_id + 7 metrics + video_name
    # If there are fewer, the line is malformed and we can't parse it
    if len(parts) < 9:
        return None
    
    # Use try/except to handle errors gracefully
    # If something goes wrong (like a non-numeric value), we return None instead of crashing
    try:
        # parts[0] is the first element (video_id)
        # int() converts the string "1" to the integer 1
        video_id = int(parts[0])
        
        # Now extract the 7 floating-point numbers (the performance metrics)
        # A float is a number with decimals, like 0.978528
        floats = []  # Empty list to store the float values
        i = 1  # Start at index 1 (skip video_id which is at index 0)
        
        # Loop through the parts, trying to convert each to a float
        # Stop when we've found 7 floats or run out of parts
        while i < len(parts) and len(floats) < 7:
            try:
                # Try to convert this part to a float
                # float("0.5") works, but float("video.mp4") will fail
                floats.append(float(parts[i]))
                i += 1  # Move to next part
            except ValueError:
                # If conversion fails, we've probably hit the video name
                # (which contains text, not numbers)
                break
        
        # If we didn't get 7 floats, the line is malformed
        if len(floats) < 7:
            return None
        
        # Everything after the 7 floats is the video name
        # parts[i:] means "all elements from index i to the end"
        # ' '.join() combines them back into a single string with spaces
        # Example: ['video', 'name', 'with', 'spaces.mp4'] -> 'video name with spaces.mp4'
        remaining = ' '.join(parts[i:])
        
    except (ValueError, IndexError):
        # If anything went wrong (wrong data type, missing element), return None
        return None
    
    # Now extract the individual metrics from the floats list
    try:
        # floats[0] is the first float (accuracy)
        # floats[1] is the second float (precision_not_behavior)
        # etc.
        accuracy = floats[0]
        precision_not_behavior = floats[1]
        precision_behavior = floats[2]
        recall_not_behavior = floats[3]
        recall_behavior = floats[4]
        f1_not_behavior = floats[5]
        f1_behavior = floats[6]
        
        # Extract identity number from brackets using regex
        # Pattern r'\[(\d+)\]' means:
        # - '\[', '\]' - literal square brackets (escaped because [ ] are special in regex)
        # - '(\d+)' - one or more digits, captured in parentheses
        # Example: "video.mp4 [0]" -> finds "[0]" and extracts "0"
        identity_match = re.search(r'\[(\d+)\]', remaining)
        
        # If a match was found, extract the number; otherwise use None
        # This is a "ternary operator": value_if_true if condition else value_if_false
        identity = int(identity_match.group(1)) if identity_match else None
        
        # Extract video name (everything before the bracket)
        # Example: "video.mp4 [0]" -> "video.mp4"
        if ' [' in remaining:
            # Split on ' [' and take the first part (everything before the bracket)
            video_name = remaining.split(' [')[0].strip()
        else:
            # If no bracket found, use the whole remaining string
            video_name = remaining.strip()
        
        # Return a dictionary containing all the parsed data
        # A dictionary is like a labeled box: each piece of data has a name (key)
        # You can access values like: result['accuracy'] or result['video_name']
        return {
            'window_size': window_size,  # Which window size this result is for
            'video_id': video_id,  # Unique identifier for the video
            'video_name': video_name,  # Name of the video file
            'identity': identity,  # Animal identity (which animal in the video)
            'accuracy': accuracy,  # Overall classification accuracy
            'precision_not_behavior': precision_not_behavior,  # Precision for "not behavior" class
            'precision_behavior': precision_behavior,  # Precision for "behavior" class
            'recall_not_behavior': recall_not_behavior,  # Recall for "not behavior" class
            'recall_behavior': recall_behavior,  # Recall for "behavior" class
            'f1_not_behavior': f1_not_behavior,  # F1 score for "not behavior" class
            'f1_behavior': f1_behavior  # F1 score for "behavior" class (most important!)
        }
        
    except (ValueError, IndexError) as e:
        # If something went wrong, print a warning but don't crash
        # line[:80] shows first 80 characters (prevents very long error messages)
        print(f"Warning: Could not parse video row: {line[:80]}... Error: {e}")
        return None


def parse_summary_stats(lines, window_size):
    """
    Parse summary statistics from a block of text lines.
    
    WHAT IT DOES:
    ------------
    Looks through multiple lines of text to find summary statistics like:
    "Mean Accuracy: 0.90262"
    "Std-Dev Accuracy: 0.089034"
    "Mean F1 Score (Behavior): 0.82141"
    etc.
    
    WHAT ARE SUMMARY STATISTICS?
    ----------------------------
    Instead of individual video results, these are averages across ALL videos:
    - Mean: The average value (add all values, divide by count)
    - Std-Dev (Standard Deviation): How much the values vary
      Low std-dev = consistent results, High std-dev = results vary a lot
    
    PARAMETERS:
    -----------
    lines (list): A list of text lines containing summary statistics
                 Example: ["Mean Accuracy: 0.90262", "Std-Dev Accuracy: 0.089034", ...]
    
    window_size (int): The window size these statistics are for
    
    RETURNS:
    --------
    dict: A dictionary containing all found statistics
          Keys: 'window_size', 'mean_accuracy', 'sd_accuracy',
                'mean_f1_behavior', 'sd_f1_behavior',
                'mean_f1_not_behavior', 'sd_f1_not_behavior'
    
    HOW IT WORKS:
    -------------
    Loops through each line, checking if it contains a statistic we're looking for.
    Uses regex to extract the numeric value after the label.
    """
    # Start with a dictionary containing just the window size
    # We'll add statistics to this dictionary as we find them
    stats = {'window_size': window_size}
    
    # Loop through each line in the list
    for line in lines:
        # Remove leading/trailing whitespace
        line = line.strip()
        
        # Check for "Mean Accuracy:" (case-insensitive)
        # .lower() converts to lowercase so "Mean" and "mean" both match
        if 'mean accuracy:' in line.lower():
            # Use regex to extract the number after "Mean Accuracy:"
            # Pattern r'mean accuracy:\s*([\d.]+)' means:
            # - 'mean accuracy:' - literal text
            # - '\s*' - zero or more whitespace characters
            # - '([\d.]+)' - one or more digits or dots (captured)
            match = re.search(r'mean accuracy:\s*([\d.]+)', line, re.IGNORECASE)
            if match:
                # Extract the number and convert to float
                stats['mean_accuracy'] = float(match.group(1))
        
        # Check for standard deviation (can be "std-dev" or "std dev")
        elif 'std-dev accuracy:' in line.lower() or 'std dev accuracy:' in line.lower():
            # Pattern handles both "std-dev" and "std dev"
            # r'std[- ]dev' matches "std-dev" or "std dev"
            match = re.search(r'std[- ]dev accuracy:\s*([\d.]+)', line, re.IGNORECASE)
            if match:
                stats['sd_accuracy'] = float(match.group(1))
        
        # Check for Mean F1 Score (Behavior)
        elif 'mean f1 score (behavior):' in line.lower():
            # Need to escape parentheses in regex: \( and \)
            match = re.search(r'mean f1 score \(behavior\):\s*([\d.]+)', line, re.IGNORECASE)
            if match:
                stats['mean_f1_behavior'] = float(match.group(1))
        
        # Check for Std-Dev F1 Score (Behavior)
        elif 'std-dev f1 score (behavior):' in line.lower() or 'std dev f1 score (behavior):' in line.lower():
            match = re.search(r'std[- ]dev f1 score \(behavior\):\s*([\d.]+)', line, re.IGNORECASE)
            if match:
                stats['sd_f1_behavior'] = float(match.group(1))
        
        # Check for Mean F1 Score (Not Behavior)
        elif 'mean f1 score (not behavior):' in line.lower():
            match = re.search(r'mean f1 score \(not behavior\):\s*([\d.]+)', line, re.IGNORECASE)
            if match:
                stats['mean_f1_not_behavior'] = float(match.group(1))
        
        # Check for Std-Dev F1 Score (Not Behavior)
        elif 'std-dev f1 score (not behavior):' in line.lower() or 'std dev f1 score (not behavior):' in line.lower():
            match = re.search(r'std[- ]dev f1 score \(not behavior\):\s*([\d.]+)', line, re.IGNORECASE)
            if match:
                stats['sd_f1_not_behavior'] = float(match.group(1))
    
    # Return the dictionary with all found statistics
    return stats


def parse_feature_importance(lines, window_size):
    """
    Parse feature importance table from text lines.
    
    WHAT IT DOES:
    ------------
    Extracts a table showing which visual features were most important for
    classification. Features are ranked by importance (how much they help
    the classifier make correct predictions).
    
    WHAT ARE FEATURES?
    ------------------
    In computer vision, a "feature" is a measurable property of an image or video.
    Examples:
    - Speed of movement
    - Direction of movement
    - Body angle
    - Distance traveled
    - Number of pixels in a certain color
    
    "Feature importance" tells us which features the machine learning model
    relies on most to distinguish between "behavior" and "not behavior".
    High importance = this feature is very useful for classification.
    
    PARAMETERS:
    -----------
    lines (list): A list of text lines containing the feature importance table
                 Format: Each line has a feature name and an importance value
                 Example: "speed 0.5234" or "body angle 0.4123"
    
    window_size (int): The window size these features are for
    
    RETURNS:
    --------
    list: A list of dictionaries, one per feature
          Each dictionary has: 'window_size', 'rank', 'feature_name', 'importance'
    
    HOW IT WORKS:
    -------------
    1. Skip header lines (like "Feature Name" or "Importance")
    2. For each data line, extract the feature name and importance value
    3. Rank them in order (1st, 2nd, 3rd, etc.)
    4. Return as a list of dictionaries
    """
    # Initialize an empty list to store parsed features
    features = []
    
    # Flag to track if we're inside the table (past the header)
    in_table = False
    
    # Counter for ranking features (1st, 2nd, 3rd, etc.)
    rank = 0
    
    # Loop through each line
    for line in lines:
        # Remove leading/trailing whitespace
        line = line.strip()
        
        # Skip header lines (these identify the table but aren't data)
        # Check if line contains table header keywords
        if 'Feature Name' in line or 'Importance' in line or '---' in line:
            # We've found the table header, so mark that we're in the table
            in_table = True
            # Skip this line and move to the next one
            continue
        
        # Stop parsing if we hit a separator (marks end of table)
        # Separators are lines starting with '%' or lines with many dashes
        if line.startswith('%') or (len(line) > 50 and line.count('-') > 20):
            break
        
        # Skip empty lines (they don't contain data)
        if not line:
            continue
        
        # Parse a feature row
        # Format: feature_name ... importance_value
        # The feature name may contain spaces, so we split and take the last part as importance
        parts = line.split()  # Split into words
        
        # We need at least 2 parts: feature name and importance value
        if len(parts) >= 2:
            try:
                # The last part should be the importance value (a number)
                # parts[-1] means "last element" (negative index counts from the end)
                importance = float(parts[-1])
                
                # Everything before the last part is the feature name
                # parts[:-1] means "all elements except the last one"
                # ' '.join() combines them back into a string with spaces
                # Example: ['body', 'angle'] -> 'body angle'
                feature_name = ' '.join(parts[:-1])
                
                # Increment rank (1st feature, 2nd feature, etc.)
                rank += 1
                
                # Create a dictionary for this feature and add it to the list
                features.append({
                    'window_size': window_size,  # Which window size
                    'rank': rank,  # Ranking (1 = most important)
                    'feature_name': feature_name,  # Name of the feature
                    'importance': importance  # Importance value (higher = more important)
                })
            except ValueError:
                # If we can't convert the last part to a float, skip this line
                # (it's probably not a data row)
                continue
    
    # Return the list of all parsed features
    return features


def parse_file(input_file):
    """
    Main parsing function that processes the entire input file.
    
    WHAT IT DOES:
    ------------
    This is the "orchestrator" function that:
    1. Reads the entire input file
    2. Loops through each line
    3. Identifies different sections (window sizes, video results, statistics, features)
    4. Calls the appropriate parsing function for each section
    5. Collects all the parsed data
    6. Returns everything organized in lists and dictionaries
    
    PARAMETERS:
    -----------
    input_file (str or Path): Path to the input text file containing results
    
    RETURNS:
    --------
    tuple: Four items:
        - video_results (list): List of dictionaries, one per video result
        - summary_stats (list): List of dictionaries, one per window size
        - feature_importance (list): List of dictionaries, one per feature
        - metadata (dict): Information about the parsing process
    
    HOW IT WORKS:
    -------------
    Uses a "state machine" approach:
    - Tracks which section we're currently in (window size, video table, etc.)
    - When it finds a section marker (like "Window 10"), it switches to that section
    - Parses all data in that section
    - Moves to the next section when it finds a new marker
    """
    # Initialize empty lists to store parsed data
    # Lists are like arrays - they can hold multiple items in order
    video_results = []  # Will hold all individual video results
    summary_stats = []  # Will hold summary statistics for each window size
    feature_importance = []  # Will hold feature importance data
    
    # Open the input file and read all lines
    # 'r' means "read mode" (we're reading, not writing)
    # encoding='utf-8' handles special characters correctly
    with open(input_file, 'r', encoding='utf-8') as f:
        # .readlines() reads all lines into a list
        # Each line is a string ending with a newline character
        lines = f.readlines()
    
    # Initialize variables for tracking our position in the file
    i = 0  # Current line index (starts at 0, which is the first line)
    current_window = None  # Which window size we're currently parsing (None = not in a window section yet)
    video_count_per_window = {}  # Dictionary to count videos per window: {10: 5, 15: 5, ...}
    
    # Main loop: process each line in the file
    # len(lines) gives us the total number of lines
    while i < len(lines):
        # Get the current line
        line = lines[i]
        
        # STEP 1: Check if this line marks the start of a new window size section
        # Example: "Window 10" or "Window 15 frames"
        window_size = parse_window_size(line)
        if window_size is not None:
            # We found a new window size! Update our tracking variable
            current_window = window_size
            print(f"Parsing window size: {window_size}")
            # Move to next line and start over (continue skips the rest of the loop)
            i += 1
            continue
        
        # STEP 2: If we're inside a window section, look for different types of data
        # current_window is None if we haven't found a window marker yet
        if current_window is not None:
            
            # STEP 2a: Check if this is the start of the video results table
            # Video tables have headers containing "accuracy", "precision", and "recall"
            if 'accuracy' in line.lower() and 'precision' in line.lower() and 'recall' in line.lower():
                # Skip the header lines (usually 2 lines: column names and a separator line)
                i += 2
                video_count = 0  # Counter for how many videos we find
                
                # Parse video rows until we hit the end of the table
                # This inner loop processes all video rows for this window size
                while i < len(lines):
                    # Get the current line and remove whitespace
                    line = lines[i].strip()
                    
                    # Check if we've reached the end of the video table
                    # End markers: summary stats starting or a new window size
                    if 'mean accuracy:' in line.lower() or parse_window_size(line) is not None:
                        break  # Exit the inner loop
                    
                    # Check for separator lines (mark end of section)
                    # Separators are long lines starting with '%'
                    if line.startswith('%') and len(line) > 50:
                        break
                    
                    # Skip empty lines (they don't contain data)
                    if not line:
                        i += 1  # Move to next line
                        continue  # Skip rest of loop, go to next iteration
                    
                    # Skip separator/dashed lines (visual separators in the file)
                    # These are lines with many dashes or equals signs
                    if line.startswith('--') or (line.startswith('=') and len(line) > 20):
                        i += 1
                        continue
                    
                    # Try to parse as a video row
                    # Video rows start with a number (video_id), then have numeric values
                    # Pattern r'^\d+\s+[\d.]' means:
                    # - '^' - start of line
                    # - '\d+' - one or more digits
                    # - '\s+' - one or more spaces
                    # - '[\d.]' - a digit or dot (start of a float)
                    if re.match(r'^\d+\s+[\d.]', line):
                        # This looks like a video row! Try to parse it
                        video_data = parse_video_row(line, current_window)
                        if video_data:
                            # Parsing succeeded! Add it to our list
                            video_results.append(video_data)
                            video_count += 1
                        # Continue even if parsing failed (don't crash on bad lines)
                    
                    # Check if we've hit a non-data line that suggests end of table
                    # These keywords indicate we've moved to a different section
                    elif any(x in line.lower() for x in ['mean accuracy', 'classifier:', 'behavior:', 'final classifier']):
                        break  # Exit the inner loop
                    
                    # Move to next line
                    i += 1
                
                # Record how many videos we found for this window size
                video_count_per_window[current_window] = video_count
                print(f"  Found {video_count} videos for window {current_window}")
                # Continue to next iteration of outer loop
                continue
            
            # STEP 2b: Check for summary statistics section
            # Summary stats start with lines containing "mean accuracy:" or "mean f1 score"
            if 'mean accuracy:' in line.lower() or 'mean f1 score' in line.lower():
                # Collect all lines that are part of the summary stats block
                stats_lines = []
                j = i  # Start from current line
                # Summary stats should be within the next 10 lines
                while j < len(lines) and j < i + 10:
                    stats_lines.append(lines[j])
                    # Stop if we hit a new section marker
                    if 'Feature Distance Unit' in lines[j] or parse_window_size(lines[j]) is not None:
                        # Actually, we want to check if it IS a window size (not None)
                        # Let me fix the logic: we stop if we find a new window or certain markers
                        if parse_window_size(lines[j]) is not None:
                            break
                    j += 1
                
                # Parse the collected lines to extract statistics
                stats = parse_summary_stats(stats_lines, current_window)
                if stats:
                    # Add the statistics to our list
                    summary_stats.append(stats)
                # Move to the line after the stats section
                i = j
                continue
            
            # STEP 2c: Check for feature importance section
            # Feature importance sections have keywords like "top", "feature", and "importance"
            if 'top' in line.lower() and 'feature' in line.lower() and 'importance' in line.lower():
                # Skip a few lines to get past the header to the actual table
                i += 2
                feature_lines = []
                # Collect all lines that are part of the feature importance table
                j = i
                while j < len(lines):
                    # Stop if we hit a new window size or a separator
                    if parse_window_size(lines[j]) is not None or (lines[j].startswith('%') and len(lines[j].strip()) > 50):
                        break
                    feature_lines.append(lines[j])
                    j += 1
                
                # Parse the collected lines to extract feature importance
                features = parse_feature_importance(feature_lines, current_window)
                # .extend() adds all items from the list to our main list
                # (instead of .append() which would add the list itself)
                feature_importance.extend(features)
                print(f"  Found {len(features)} features for window {current_window}")
                # Move to the line after the features section
                i = j
                continue
        
        # Move to next line in the file
        i += 1
    
    # After processing all lines, create metadata about what we found
    # Metadata is "data about data" - information about the parsing process
    metadata = {
        'n_windows': len(video_count_per_window),  # Number of different window sizes found
        # Get the number of videos from the first window (assuming all windows have same count)
        'n_videos': video_count_per_window.get(list(video_count_per_window.keys())[0], 0) if video_count_per_window else 0,
        'video_counts_per_window': video_count_per_window,  # Dictionary of counts per window
        'window_sizes': sorted(video_count_per_window.keys())  # List of window sizes, sorted
    }
    
    # Return all the parsed data
    return video_results, summary_stats, feature_importance, metadata


def main():
    """
    Main execution function - this runs when the script is executed.
    
    WHAT IT DOES:
    ------------
    1. Sets up file paths (where to read from, where to write to)
    2. Calls parse_file() to extract data from the input file
    3. Writes the extracted data to CSV files
    4. Prints a summary of what was done
    
    HOW TO RUN:
    -----------
    From the command line:
    python3 scripts/parse_window_results.py
    
    Or make it executable and run directly:
    chmod +x scripts/parse_window_results.py
    ./scripts/parse_window_results.py
    """
    # SET UP FILE PATHS
    # ------------------
    # Path(__file__) is the path to this Python script file
    # .parent gets the directory containing this script (the 'scripts' folder)
    script_dir = Path(__file__).parent
    
    # .parent again gets the parent of 'scripts' (the 'window_size_analysis' folder)
    project_dir = script_dir.parent
    
    # Build the path to the input file
    # Using / operator to join path components (works on Windows, Mac, Linux)
    input_file = project_dir / 'data' / 'raw' / 'Window size scan.txt'
    
    # Build the path to the output directory (where we'll save CSV files)
    output_dir = project_dir / 'data' / 'processed'
    
    # Create the output directory if it doesn't exist
    # parents=True: create parent directories if needed
    # exist_ok=True: don't error if directory already exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Print a header to show the script is running
    print("=" * 80)  # Print 80 equals signs as a separator
    print("Window Size Results Parser")
    print("=" * 80)
    print(f"Input file: {input_file}")
    print(f"Output directory: {output_dir}")
    print()  # Empty line
    
    # PARSE THE INPUT FILE
    # --------------------
    # Call parse_file() to extract all data from the input file
    # This returns four things (a tuple), which we "unpack" into four variables
    video_results, summary_stats, feature_importance, metadata = parse_file(input_file)
    
    # SET UP OUTPUT FILE PATHS
    # -------------------------
    video_output = output_dir / 'video_results.csv'
    summary_output = output_dir / 'summary_stats.csv'
    feature_output = output_dir / 'feature_importance.csv'
    metadata_output = output_dir / 'metadata.txt'
    
    # WRITE VIDEO RESULTS TO CSV
    # --------------------------
    # Check if we have any video results to write
    if video_results and len(video_results) > 0:
        # Open the output file for writing
        # 'w' means "write mode" (creates new file or overwrites existing)
        # newline='' is required for proper CSV formatting on all operating systems
        with open(video_output, 'w', newline='') as f:
            # csv.DictWriter creates a CSV writer that works with dictionaries
            # fieldnames tells it what columns to create (uses keys from first dictionary)
            writer = csv.DictWriter(f, fieldnames=video_results[0].keys())
            
            # Write the header row (column names)
            writer.writeheader()
            
            # Write all the data rows
            # .writerows() writes multiple rows at once
            writer.writerows(video_results)
    else:
        print("WARNING: No video results found!")
    
    # WRITE SUMMARY STATISTICS TO CSV
    # -------------------------------
    if summary_stats and len(summary_stats) > 0:
        with open(summary_output, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=summary_stats[0].keys())
            writer.writeheader()
            writer.writerows(summary_stats)
    else:
        print("WARNING: No summary stats found!")
    
    # WRITE FEATURE IMPORTANCE TO CSV
    # -------------------------------
    if feature_importance and len(feature_importance) > 0:
        with open(feature_output, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=feature_importance[0].keys())
            writer.writeheader()
            writer.writerows(feature_importance)
    else:
        print("WARNING: No feature importance found!")
    
    # WRITE METADATA TO TEXT FILE
    # ----------------------------
    # Metadata is written as plain text (not CSV) for human readability
    with open(metadata_output, 'w') as f:
        f.write("Parsing Metadata\n")
        f.write("=" * 80 + "\n\n")  # Header separator
        f.write(f"Number of windows: {metadata['n_windows']}\n")
        f.write(f"Number of videos: {metadata['n_videos']}\n")
        f.write(f"Window sizes: {metadata['window_sizes']}\n\n")
        f.write("Video counts per window:\n")
        # Loop through window sizes and their counts
        # .items() gives us (key, value) pairs: (10, 5), (15, 5), etc.
        for window, count in sorted(metadata['video_counts_per_window'].items()):
            f.write(f"  Window {window}: {count} videos\n")
    
    # PRINT SUMMARY
    # -------------
    print()
    print("=" * 80)
    print("Parsing Complete")
    print("=" * 80)
    # len() gives the number of items in a list
    print(f"Video results: {len(video_results)} rows -> {video_output}")
    print(f"Summary stats: {len(summary_stats)} rows -> {summary_output}")
    print(f"Feature importance: {len(feature_importance)} rows -> {feature_output}")
    print()
    print(f"Metadata:")
    print(f"  Windows: {metadata['n_windows']}")
    print(f"  Videos per window: {metadata['n_videos']}")
    print(f"  Window sizes: {metadata['window_sizes']}")


# This special code runs main() only if the script is executed directly
# (not if it's imported as a module by another script)
# This is a Python convention that allows the script to be both:
# 1. Run directly: python3 parse_window_results.py
# 2. Imported: from parse_window_results import parse_file
if __name__ == '__main__':
    main()
