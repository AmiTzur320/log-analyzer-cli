from datetime import datetime
from typing import Optional
import click
from helper import *


def check_readable_file(file_path: str) -> bool:
    """
        Check if the specified file can be opened for reading.

        Args:
            file_path (str): The path to the file.
        Returns:
            bool: True if the file is readable, False otherwise.
        """
    try:
        with open(file_path, "r"):
            pass
    except Exception as e:
        click.echo(f"Error: Cannot read file '{file_path}': {e}", err=True)
        return False
    return True


def check_timestamps_valid(from_ts: Optional[datetime], to_ts: Optional[datetime]) -> bool:
    """
        Validate that the INPUT start timestamp is not after the end timestamp.

        Args:
            from_ts (Optional[datetime]): Start timestamp (or None).
            to_ts (Optional[datetime]): End timestamp (or None).
        Returns:
            bool: True if the timestamps are valid or not provided, False otherwise.
        """
    if from_ts and to_ts and from_ts > to_ts:
        click.echo("Error: --from timestamp is after --to timestamp!", err=True)
        return False
    return True


def load_event_filters(events_file: str) -> list[dict]:
    """
        Load and parse event filters from the configuration file.

        Args:
            events_file (str): Path to the events configuration file.

        Returns:
            list[dict]: List of event filter dictionaries.
        """
    with open(events_file, 'r') as event_file:
        lines = event_file.read().splitlines()
        events_filters = []
        for line in lines:
            line = line.strip()
            if not is_valid_event_filter_line(line):  # check if event is not empty/comment
                continue
            parts = line.strip().split()
            event_filter = parse_event_filter_parts(parts)  # parse the parts tokens into a filter dictionary.
            events_filters.append(event_filter)
    return events_filters


def process_logs(log_dir: str, events_filters: list[dict], from_ts: Optional[datetime],
                 to_ts: Optional[datetime]) -> list[dict]:
    """
        Process all log files in the given directory and filter events according to the event filters.

        Args:
            log_dir (str): Path to the directory containing log files.
            events_filters (list[dict]): List of event filter specifications.
            from_ts (Optional[datetime]): Start timestamp for filtering (inclusive).
            to_ts (Optional[datetime]): End timestamp for filtering (inclusive).

        Returns:
            list[dict]: Results for each event filter, with either 'count' or 'lines' keys.
        """
    results = initialize_results(events_filters)  # init list with count= 0 if count=True or [] else in each filter cell
    log_files = find_log_files(log_dir)  # Collect all .log and .log.gz files
    if not log_files:
        click.echo(f"Warning: No log files found in {log_dir}", err=True)
        return results

    for filename in log_files:
        file_path = os.path.join(log_dir, filename)
        mode, open_func = get_log_file_opener(filename)  # Choose the correct open function for log. or log.gz

        with open_func(file_path, mode) as log_file:
            for line in log_file:
                process_log_line(line, results, events_filters, from_ts, to_ts)  # parse the current log line
    return results


def print_results(events_filters: list[dict], results: list[dict]) -> None:
    """
            Print the results for each event filter in the required output format.

            Args:
                events_filters (list[dict]): List of event filter specifications.
                results (list[dict]): List of results corresponding to each filter.
            """
    for idx, event_filter in enumerate(events_filters):
        info = []
        if event_filter['level']:
            info.append(f"level [{event_filter['level']}]")
        if event_filter['pattern']:
            info.append(f"pattern [{event_filter['pattern']}]")
        info_str = ' '.join(info)

        if event_filter['count']:
            print(
                f"Event: {event_filter['event_type']} {info_str} count — matches: {results[idx]['count']} entries")
        else:
            print(f"Event: {event_filter['event_type']} {info_str} — matching log lines:")
            if not results[idx]['lines']:
                print("No log lines matching this filter")
            else:
                for line in results[idx]['lines']:
                    print(line)


@click.command()
@click.option('--log-dir', type=click.Path(exists=True, file_okay=False, dir_okay=True), required=True,
              help='Path to the folder containing log files (.log, .log.gz).  [required]')
@click.option('--events-file', type=click.Path(exists=True, file_okay=True, dir_okay=False), required=True,
              help='Path to the event filters configuration file (events_sample.txt). [required]')
@click.option('--from', 'from_ts', type=click.DateTime(formats=['%Y-%m-%dT%H:%M:%S']), required=False,
              help='Only include logs with timestamp >= this (YYYY-MM-DDTHH:MM:SS).')
@click.option('--to', 'to_ts', type=click.DateTime(formats=['%Y-%m-%dT%H:%M:%S']), required=False,
              help='Only include logs with timestamp <= this (YYYY-MM-DDTHH:MM:SS).')
def main(log_dir, events_file, from_ts, to_ts):
    if not check_readable_file(events_file):  # file exist but check if there is permission to the file
        return
    if not check_timestamps_valid(from_ts, to_ts):  # check if from <= to
        return
    events_filters = load_event_filters(events_file)  # load and filter events from config file
    results = process_logs(log_dir, events_filters, from_ts, to_ts)  # get results following the filters
    print_results(events_filters, results)  # print the results


if __name__ == '__main__':
    main()
