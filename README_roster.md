# Roster Assignment Tool

This tool helps assign interview slots to interviewers based on their availability and capacity. It uses a proportional assignment algorithm to ensure fair distribution of slots.

## Features

- Supports both day and night shift scheduling
- Configurable slot duration (default: 40 minutes)
- Multiple output formats (text and CSV)
- Command-line interface with various options
- Robust error handling and validation
- Proportional slot assignment based on interviewer capacity

## Usage

```bash
python roster_assignment.py [options]
```

### Options

- `--file, -f FILE`: Path to CSV file with interviewer data (default: interviewers_formatted.csv)
- `--shift, -s SHIFT`: Shift to schedule ('day' or 'night', default: day)
- `--slots, -n SLOTS`: Override the number of slots for the shift
- `--duration, -d MINS`: Duration of each slot in minutes (default: 40)
- `--output, -o FORMAT`: Output format ('text' or 'csv', default: text)
- `--output-file`: Output file path for CSV format (default: auto-generated filename)
- `--help, -h`: Show help message

### Examples

```bash
# Basic usage with default settings (day shift, text output)
python roster_assignment.py

# Night shift scheduling
python roster_assignment.py --shift night

# Custom slot duration (30 minutes)
python roster_assignment.py --duration 30

# CSV output with custom filename
python roster_assignment.py --output csv --output-file my_roster.csv

# Specify custom number of slots
python roster_assignment.py --slots 25

# Use a different CSV file
python roster_assignment.py --file other_interviewers.csv
```

## CSV File Format

The input CSV file must contain the following columns:

- `Interviewer_ID`: Unique identifier for each interviewer
- `Name`: Interviewer's name
- `Email`: Interviewer's email (optional)
- `Day_Available`: Whether the interviewer is available for day shift ('True' or 'False')
- `Night_Available`: Whether the interviewer is available for night shift ('True' or 'False')
- `Day_Slots`: Maximum number of slots the interviewer can take during day shift
- `Night_Slots`: Maximum number of slots the interviewer can take during night shift

## Algorithm

The slot assignment algorithm works as follows:

1. Filter interviewers based on availability for the selected shift
2. Calculate the total available slots across all available interviewers
3. For each interviewer, compute the ideal fractional assignment based on their capacity
4. Floor the ideal assignments to get initial integer assignments
5. Distribute remaining slots based on highest fractional remainders, ensuring no interviewer exceeds their capacity

This approach ensures a fair distribution of slots proportional to each interviewer's capacity while respecting their maximum limits.