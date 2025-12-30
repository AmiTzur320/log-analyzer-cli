import os
import gzip
import re
from collections import deque
from datetime import datetime
from typing import Optional, List, Dict, Deque

VALID_EVENT_TYPES = {"TELEMETRY", "DEVICE", "GNMI"}
VALID_LEVELS = {"INFO", "WARNING", "ERROR"}


def parse_log_line(line: str) -> Optional[dict]:
    """
        Parse a single log line into its components and validate format.

        Args:
            line (str): The log line to parse.
        Returns:
            Optional[dict]: Parsed fields if the line is valid, otherwise None.
        """
    parts = line.strip().split(' ', 3)
    if len(parts) < 4:
        return None

    timestamp, level, event_type, message = parts

    # Validate timestamp format
    try:
        datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return None

    # Validate level and event_type
    if level not in VALID_LEVELS:
        return None
    if event_type not in VALID_EVENT_TYPES:
        return None

    return {
        "timestamp": timestamp,
        "level": level,
        "event_type": event_type,
        "message": message
    }


def is_valid_event_filter_line(line: str) -> bool:
    """
    Check if the line is a non-empty, non-comment, well sized event filter line.

    Args:
        line (str): Line from the events file.

    Returns:
        bool: True if the line is valid for parsing, False otherwise.
    """
    if not line.strip():  # empty line
        return False
    if line.strip().startswith('#'):  # comment line
        return False

    return True


def pop_flag_value(tokens: Deque[str], flag: str, line_for_warning: str) -> Optional[str]:
    """
    If there is a value for this flag (not another flag or empty), pop and return it.
    Otherwise, print warning and return None.
    """
    if tokens and not tokens[0].startswith('--'):
        return tokens.popleft()
    print(f"Warning: {flag} flag requires a value (skipping), line: {line_for_warning}")
    return None


def pop_pattern_value(tokens: Deque[str], flag: str, line_for_warning: str) -> Optional[str]:
    """
    Pops all subsequent words from tokens for a multi-word flag until another flag or end.
    Returns the joined string or None if missing, and prints a warning if missing.
    """
    pattern_words = []
    while tokens and not tokens[0].startswith('--'):
        # create multi-word
        pattern_words.append(tokens.popleft())
    if pattern_words:
        return ' '.join(pattern_words)
    print(f"Warning: {flag} flag missing value (skipping), line: {line_for_warning}")
    return None


def parse_event_filter_parts(parts: list[str]) -> dict:
    """
    Parse tokens (already split) from a filter line into an event_filter dict,
    using deque for robust flag parsing.
    Prints warnings but does not crash on bad input.
    """
    event_filter = {
        "event_type": parts[0],
        "count": False,
        "level": None,
        "pattern": None
    }
    tokens = deque(parts[1:])  # deque without event type, just flags and values

    while tokens:
        # creating an event filter, checking if the event is valid. if there are two same flags take the last
        flag = tokens.popleft()
        if flag == '--count':
            # updating count
            event_filter['count'] = True

        elif flag == '--level':
            # update level or give a warning (if level is not valid)
            event_filter['level'] = pop_flag_value(tokens, '--level', ' '.join(parts))

        elif flag == '--pattern':
            # update pattern or give a warning (if pattern is not valid)
            event_filter['pattern'] = pop_pattern_value(tokens, '--pattern', ' '.join(parts))
        else:
            print(f"Warning: Unknown flag '{flag}' (skipping), line: {' '.join(parts)}")

    return event_filter


def matches_filters(parsed: dict, event_filter: dict) -> bool:
    """
       Check if a parsed log entry matches the given event filter.

       Args:
           parsed (dict): Parsed log entry.
           event_filter (dict): Event filter specification.

       Returns:
           bool: True if the entry matches the filter, False otherwise.
       """
    if parsed['event_type'] != event_filter['event_type']:
        return False
    if event_filter['level'] and parsed['level'] != event_filter['level']:
        return False
    if event_filter['pattern']:
        if not re.search(event_filter['pattern'], parsed['message']):
            return False
    return True


def in_time_range(parsed_ts_str: str, from_ts: Optional[datetime] = None
                  , to_ts: Optional[datetime] = None) -> bool:
    """
    Check if a log entry's timestamp is within the given time range (inclusive).

    Args:
        parsed_ts_str (str): Timestamp string from the log line.
        from_ts (Optional[datetime]): Start of the time range, or None.
        to_ts (Optional[datetime]): End of the time range, or None.

    Returns:
        bool: True if the timestamp is within range, False otherwise.
    """
    ts = datetime.strptime(parsed_ts_str, "%Y-%m-%dT%H:%M:%S")
    if from_ts and ts < from_ts:
        return False
    if to_ts and ts > to_ts:
        return False
    return True


def get_log_file_opener(filename: str):
    """
        Return the appropriate open function and mode for a log file.

        Args:
            filename (str): Name of the log file.

        Returns:
            tuple: (open function, mode string)
        """
    if filename.endswith('.log.gz'):
        open_func = gzip.open
        mode = 'rt'  # text mode for gzip
    else:
        open_func = open
        mode = 'r'
    return mode, open_func


def initialize_results(events_filters: list[dict]) -> list[dict]:
    """
        Create the initial results list for event filters, with a structure matching each filter's mode.

        For each event filter:
          - If the filter is set to 'count' mode (event_filter['count'] is True),
            initialize with {'count': 0} to store the number of matching events.
          - Otherwise, initialize with {'lines': []} to collect the matching log lines.

        Args:
            events_filters (list[dict]): List of event filter specifications.

        Returns:
            list[dict]: List of initialized results, one for each event filter.
        """
    results = []
    for event_filter in events_filters:
        # for each event put 0 if we need to count how many matching events, or [] for all matching lines
        if event_filter['count']:
            results.append({'count': 0})
        else:
            results.append({'lines': []})
    return results


def find_log_files(log_dir: str) -> list[str]:
    """
    Find all .log and .log.gz files in the specified directory.

    Args:
        log_dir (str): Path to the directory to search.

    Returns:
        List[str]: List of matching log file names.
    """
    log_files = []
    for fname in os.listdir(log_dir):
        if fname.endswith('.log') or fname.endswith('.log.gz'):  # regular log file or compressed log file
            log_files.append(fname)
    return log_files


def process_log_line(line: str, results: list[dict], events_filters: list[dict], from_ts: Optional[datetime],
                     to_ts: Optional[datetime]) -> None:
    """
    Parse a log line, check time range, and update results if the line matches any event filter.

    Args:
        line (str): The log line.
        results (list[dict]): The current results list to update.
        events_filters (list[dict]): List of event filter specifications.
        from_ts (Optional[datetime]): Start timestamp for filtering (inclusive).
        to_ts (Optional[datetime]): End timestamp for filtering (inclusive).
    """
    parsed = parse_log_line(line)
    if not parsed:
        return  # skip irrelevant lines
    if not in_time_range(parsed['timestamp'], from_ts, to_ts):
        return  # skip lines if time is not in range
    for idx, event_filter in enumerate(events_filters):
        if matches_filters(parsed, event_filter):
            if event_filter['count']:
                results[idx]['count'] += 1
            else:
                results[idx]['lines'].append(line.strip())
