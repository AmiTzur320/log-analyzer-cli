import contextlib
import io
import os
import shutil
import tempfile
from datetime import datetime
from LogAnalyzer import (load_event_filters, process_logs, check_readable_file, check_timestamps_valid, print_results)
from helper import (parse_log_line, matches_filters, in_time_range, parse_event_filter_parts)


# === Tests for check_readable ===

# Test that an existing file is correctly recognized as readable
def test_check_readable_exists():
    # Create a temp file
    with tempfile.NamedTemporaryFile(delete=False) as tf:
        test_path = tf.name
    try:
        assert check_readable_file(test_path) is True
    finally:
        os.remove(test_path)


# Test that a non-existent file is correctly recognized as not readable
def test_check_readable_not_exists():
    fake_path = "this_file_does_not_exist_987654321.txt"
    assert check_readable_file(fake_path) is False


# === Tests for check_timestamps ===

# Test that valid (from_ts < to_ts) timestamps are accepted
def test_check_timestamps_valid():
    from_ts = datetime(2025, 6, 1, 10, 0, 0)
    to_ts = datetime(2025, 6, 1, 15, 0, 0)
    assert check_timestamps_valid(from_ts, to_ts) is True


# Test that invalid (from_ts >= to_ts) timestamps are rejected
def test_check_timestamps_invalid():
    from_ts = datetime(2025, 6, 1, 16, 0, 0)
    to_ts = datetime(2025, 6, 1, 15, 0, 0)
    assert check_timestamps_valid(from_ts, to_ts) is False


# Test that a None from_ts with a valid to_ts is accepted
def test_check_timestamps_from_none():
    from_ts = None
    to_ts = datetime(2025, 6, 1, 15, 0, 0)
    assert check_timestamps_valid(from_ts, to_ts) is True


# Test that a valid from_ts with a None to_ts is accepted
def test_check_timestamps_to_none():
    from_ts = datetime(2025, 6, 1, 10, 0, 0)
    to_ts = None
    assert check_timestamps_valid(from_ts, to_ts) is True


# Test that a None from_ts with a None to_ts is accepted
def test_check_timestamps_both_none():
    from_ts = None
    to_ts = None
    assert check_timestamps_valid(from_ts, to_ts) is True


# === Tests for parse_log_line ===

# Test parsing a valid log line into its components
def test_parse_log_line_valid():
    line = "2025-06-01T14:05:22 WARNING DEVICE detected high temperature"
    result = parse_log_line(line)
    assert result['timestamp'] == "2025-06-01T14:05:22"
    assert result['level'] == "WARNING"
    assert result['event_type'] == "DEVICE"
    assert result['message'] == "detected high temperature"


# Test that a log line with an invalid date is rejected
def test_parse_log_line_invalid_date():
    line = "badtime WARNING DEVICE msg"  # date invalid
    assert parse_log_line(line) is None


# Test that a log line with missing parts is rejected
def test_parse_log_line_missing_part():
    line = "2025-06-01T14:05:22 WARNING"  # not enough parts
    assert parse_log_line(line) is None


# Test that a log line with an invalid level is rejected
def test_parse_log_line_invalid_level():
    line = "2025-06-01T14:05:22 DANGER DEVICE something"  # level 'DANGER' is undefined
    assert parse_log_line(line) is None


# Test that a log line with an invalid event type is rejected
def test_parse_log_line_invalid_event_type():
    line = "2025-06-01T14:05:22 WARNING NOTANEVENT message"  # event type 'NOTANEVENT' is undefined
    assert parse_log_line(line) is None


# === Tests for matches_filters ===

# Test matching filters using only the event type
def test_matches_filters_event_type():
    parsed = {'event_type': 'DEVICE', 'level': 'INFO', 'message': 'test'}
    event_filter = {'event_type': 'DEVICE', 'level': None, 'pattern': None, 'count': False}
    assert matches_filters(parsed, event_filter) is True

    event_filter = {'event_type': 'TELEMETRY', 'level': None, 'pattern': None, 'count': False}
    assert matches_filters(parsed, event_filter) is False


# Test matching filters when both event type and level are specified
def test_matches_filters_level():
    parsed = {'event_type': 'DEVICE', 'level': 'INFO', 'message': 'test'}
    event_filter = {'event_type': 'DEVICE', 'level': 'INFO', 'pattern': None, 'count': False}
    assert matches_filters(parsed, event_filter) is True

    event_filter = {'event_type': 'DEVICE', 'level': 'WARNING', 'pattern': None, 'count': False}
    assert matches_filters(parsed, event_filter) is False


# Test matching filters when a regex pattern is specified for the message
def test_matches_filters_pattern():
    parsed = {'event_type': 'DEVICE', 'level': 'WARNING', 'message': 'disk space low: 92% full'}
    event_filter = {
        'event_type': 'DEVICE',
        'level': 'WARNING',
        'pattern': r'^disk space low:\s\d+%\sfull$',
        'count': False
    }
    assert matches_filters(parsed, event_filter) is True

    # Pattern that doesn't match
    event_filter['pattern'] = r'^detected high temperature'
    assert matches_filters(parsed, event_filter) is False


# Test matching filters using event type, level, and pattern together
def test_matches_filters_combined():
    parsed = {
        'event_type': 'DEVICE',
        'level': 'WARNING',
        'message': 'detected high temperature of device 123: 40C'
    }
    event_filter = {
        'event_type': 'DEVICE',
        'level': 'WARNING',
        'pattern': r'^detected high temperature',
        'count': False
    }
    assert matches_filters(parsed, event_filter) is True

    # Wrong level
    event_filter['level'] = 'INFO'
    assert matches_filters(parsed, event_filter) is False

    # Wrong event_type
    event_filter['event_type'] = 'GNMI'
    assert matches_filters(parsed, event_filter) is False


# Test that in_time_range works correctly when only from_ts is specified
def test_in_time_range_from_only():
    ts = "2025-06-01T15:00:00"
    from_ts = datetime(2025, 6, 1, 14, 0, 0)
    assert in_time_range(ts, from_ts=from_ts, to_ts=None) is True

    ts_too_early = "2025-06-01T13:00:00"
    assert in_time_range(ts_too_early, from_ts=from_ts, to_ts=None) is False


# Test that in_time_range works correctly when only to_ts is specified
def test_in_time_range_to_only():
    ts = "2025-06-01T13:00:00"
    to_ts = datetime(2025, 6, 1, 14, 0, 0)
    assert in_time_range(ts, from_ts=None, to_ts=to_ts) == True

    ts_too_late = "2025-06-01T15:00:00"
    assert in_time_range(ts_too_late, from_ts=None, to_ts=to_ts) == False


# Test that in_time_range works correctly when both from_ts and to_ts are specified
def test_in_time_range_from_and_to():
    ts = "2025-06-01T15:00:00"
    from_ts = datetime(2025, 6, 1, 14, 0, 0)
    to_ts = datetime(2025, 6, 1, 16, 0, 0)
    assert in_time_range(ts, from_ts=from_ts, to_ts=to_ts) == True

    ts_too_early = "2025-06-01T13:00:00"
    ts_too_late = "2025-06-01T17:00:00"
    assert in_time_range(ts_too_early, from_ts=from_ts, to_ts=to_ts) == False
    assert in_time_range(ts_too_late, from_ts=from_ts, to_ts=to_ts) == False


# Test that in_time_range always returns True when no limits are specified
def test_in_time_range_no_limits():
    ts = "2025-06-01T15:00:00"
    assert in_time_range(ts, from_ts=None, to_ts=None) == True


# Test loading event filters from a config file with various filter type
def test_load_event_filters_simple():
    lines = [
        "DEVICE --count --level WARNING",
        "GNMI --level ERROR",
        "TELEMETRY --pattern ^Iteration time:\\s\\d+\\.\\d+\\ssec$",
        "# This is a comment",
        "",
    ]
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tf:  # creating temp file -fname
        tf.write("\n".join(lines))
        tf.flush()
        fname = tf.name

    try:
        filters = load_event_filters(fname)
        assert filters[0]['event_type'] == 'DEVICE'
        assert filters[0]['count'] is True
        assert filters[0]['level'] == 'WARNING'
        assert filters[0]['pattern'] is None

        assert filters[1]['event_type'] == 'GNMI'
        assert filters[1]['count'] is False
        assert filters[1]['level'] == 'ERROR'
        assert filters[1]['pattern'] is None

        assert filters[2]['event_type'] == 'TELEMETRY'
        assert filters[2]['count'] is False
        assert filters[2]['level'] is None
        assert filters[2]['pattern'] == r"^Iteration time:\s\d+\.\d+\ssec$"
    finally:
        os.remove(fname)  # delete temp file


# Test loading an event filter with a multi-word pattern from the config file
def test_load_event_filters_multiline_pattern():
    lines = [
        "DEVICE --pattern detected high temperature",
    ]
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tf:
        tf.write("\n".join(lines))
        tf.flush()
        fname = tf.name

    try:
        filters = load_event_filters(fname)
        assert filters[0]['event_type'] == 'DEVICE'
        assert filters[0]['pattern'] == "detected high temperature"
    finally:
        os.remove(fname)


# Test processing logs for both count and matching lines filters with a time range
def test_process_logs_counts_and_lines():
    # Create a temporary log directory
    log_dir = tempfile.mkdtemp()
    try:
        # Create a sample log file
        log_path = os.path.join(log_dir, "test1.log")
        log_lines = [
            "2025-06-01T14:05:22 WARNING DEVICE detected high temperature of device 123: 40C",
            "2025-06-01T14:10:00 ERROR GNMI unresponsive telemetry at endpoint http://abc",
            "2025-06-01T14:15:00 WARNING DEVICE disk space low: 92% full",
            "2025-06-01T13:55:00 WARNING DEVICE detected high temperature of device 123: 38C",  # note-out time of range
        ]
        with open(log_path, "w") as f:
            for log in log_lines:
                f.write(log + "\n")

        # Define filters
        events_filters = [
            {'event_type': 'DEVICE', 'count': True, 'level': 'WARNING', 'pattern': None},
            {'event_type': 'GNMI', 'count': False, 'level': 'ERROR',
             'pattern': r'^unresponsive telemetry at endpoint\s.+'}
        ]

        # Define time range (14:00-15:00)
        from_ts = datetime(2025, 6, 1, 14, 0, 0)
        to_ts = datetime(2025, 6, 1, 15, 0, 0)

        results = process_logs(log_dir, events_filters, from_ts, to_ts)

        # Filter 0: DEVICE WARNING count, should match two lines (14:05, 14:15)
        assert results[0]['count'] == 2

        # Filter 1: GNMI ERROR + pattern, should match only one line (14:10)
        assert results[1]['lines'] == [
            "2025-06-01T14:10:00 ERROR GNMI unresponsive telemetry at endpoint http://abc"
        ]
    finally:
        shutil.rmtree(log_dir)  # delete temp folder


# Test printing results in the expected format for both count and matching lines filters
def test_print_results_output():
    events_filters = [
        {'event_type': 'DEVICE', 'count': True, 'level': 'WARNING', 'pattern': None},
        {'event_type': 'GNMI', 'count': False, 'level': 'ERROR', 'pattern': r'^unresponsive telemetry at endpoint\s.+$'}
    ]
    results = [
        {'count': 2},
        {'lines': ["2025-06-01T14:10:00 ERROR GNMI unresponsive telemetry at endpoint http://abc"]}
    ]

    expected_output = (
        "Event: DEVICE level [WARNING] count — matches: 2 entries\n"
        "Event: GNMI level [ERROR] pattern [^unresponsive telemetry at endpoint\\s.+$] — matching log lines:\n"
        "2025-06-01T14:10:00 ERROR GNMI unresponsive telemetry at endpoint http://abc\n"
    )

    f = io.StringIO()  # string that demonstrate a file
    with contextlib.redirect_stdout(f):  # save into f and don't print
        print_results(events_filters, results)
    output = f.getvalue()
    assert output == expected_output


# Test that the output exactly matches the example input and output from the PDF specification
def test_example_from_pdf():
    # Prepare events file
    events_lines = [
        "TELEMETRY --count --pattern ^Iteration time:\\s\\d+\\.\\d+\\ssec$",
        "DEVICE --count --level WARNING",
        "GNMI --level ERROR"
    ]

    log_lines = [
        "2025-06-01T14:05:22 WARNING DEVICE detected high temperature of device c95fe73e-14db-4ef4-909d-0c1db67c41ee: 40C",
        "2025-06-01T14:10:00 ERROR GNMI unresponsive telemetry at endpoint http://SWX1:9001/low_freq_debug",
        "2025-06-01T14:03:05 INFO TELEMETRY Iteration time: 1793.845 sec"
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        events_file = os.path.join(tmpdir, "events_sample.txt")
        log_file = os.path.join(tmpdir, "sample.log")

        # Write events file
        with open(events_file, "w") as f:
            f.write("\n".join(events_lines))
        # Write log file
        with open(log_file, "w") as f:
            f.write("\n".join(log_lines))

        # Run processing
        events_filters = load_event_filters(events_file)
        results = process_logs(tmpdir, events_filters, None, None)

        # Capture output
        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            print_results(events_filters, results)
        output = f.getvalue().strip()

    # The expected output, exactly as in the PDF
    expected = (
        "Event: TELEMETRY pattern [^Iteration time:\\s\\d+\\.\\d+\\ssec$] count — matches: 1 entries\n"
        "Event: DEVICE level [WARNING] count — matches: 1 entries\n"
        "Event: GNMI level [ERROR] — matching log lines:\n"
        "2025-06-01T14:10:00 ERROR GNMI unresponsive telemetry at endpoint http://SWX1:9001/low_freq_debug"
    )
    assert output == expected


# Test that a filter with a pattern value and a --level flag missing its value is parsed correctly
def test_pattern_with_value_and_level_missing_value():
    # --pattern has a value, --level is missing a value
    parts = [
        'DEVICE',
        '--pattern',
        '^detected high temperature of device\\s[a-f0-9\\-]{36}:\\s\\d+C$',
        '--level'
    ]
    result = parse_event_filter_parts(parts)
    assert result['pattern'] == '^detected high temperature of device\\s[a-f0-9\\-]{36}:\\s\\d+C$'
    assert result['level'] is None


# Test that a filter with a missing pattern value but a valid level value is parsed correctly
def test_pattern_missing_value_but_level_ok():
    # --pattern is missing a value, but --level has a value
    parts = [
        'GNMI',
        '--pattern',
        '--level',
        'ERROR'
    ]
    result = parse_event_filter_parts(parts)
    assert result['pattern'] is None
    assert result['level'] == 'ERROR'
