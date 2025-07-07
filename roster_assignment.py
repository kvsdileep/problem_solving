#!/usr/bin/env python3
"""
Roster Assignment for Interviewers

This script reads a CSV file with interviewer details, their availability for shifts,
and their maximum interview slots per shift. It computes a proportional assignment, ensuring:
  - Only available interviewers (per selected shift) are considered.
  - Each interviewer is not assigned more slots than their per-shift limit.
  - 1 slot corresponds to a 40-minute interview (configurable).
  
Shifts:
  • Day shift: 6 am – 8 pm (typically 21 slots: 14 hours * 60 / 40)
  • Night shift: 8 pm – 6 am (typically 15 slots: 10 hours * 60 / 40)
  
Usage:
  python3 roster_assignment.py [options]

Options:
  --file, -f FILE       Path to CSV file with interviewer data (default: interviewers_formatted.csv)
  --shift, -s SHIFT     Shift to schedule ('day' or 'night', default: day)
  --slots, -n SLOTS     Override the number of slots for the shift
  --duration, -d MINS   Duration of each slot in minutes (default: 40)
  --output, -o FORMAT   Output format ('text', 'csv', or 'json', default: text)
  --output-file FILE    Output file path for CSV/JSON format
  --help, -h            Show this help message
"""

import csv
import math
import sys
import os
import argparse
import logging
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def read_interviewers(csv_filename: str) -> List[Dict[str, Any]]:
    """
    Reads the CSV file and returns a list of interviewer dictionaries.
    Expected CSV columns:
      Interviewer_ID, Name, Email, Day_Available, Night_Available, Day_Slots, Night_Slots
    
    Args:
        csv_filename (str): Path to the CSV file
        
    Returns:
        List[Dict[str, Any]]: List of dictionaries containing interviewer data
        
    Raises:
        FileNotFoundError: If the CSV file doesn't exist
        ValueError: If required columns are missing or data format is invalid
    """
    if not os.path.exists(csv_filename):
        raise FileNotFoundError(f"CSV file '{csv_filename}' not found.")
        
    interviewers = []
    required_columns = ['Interviewer_ID', 'Name', 'Day_Available', 'Night_Available', 'Day_Slots', 'Night_Slots']
    
    try:
        with open(csv_filename, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            # Validate CSV structure
            if not reader.fieldnames:
                raise ValueError("CSV file appears to be empty or improperly formatted.")
                
            if not all(col in reader.fieldnames for col in required_columns):
                missing = [col for col in required_columns if col not in reader.fieldnames]
                raise ValueError(f"CSV is missing required columns: {', '.join(missing)}")
            
            for row_num, row in enumerate(reader, start=2):  # Start at 2 to account for header row
                try:
                    # Convert availability flags from string to boolean (accepts "True"/"False" in any case)
                    for field in ['Day_Available', 'Night_Available']:
                        value = row.get(field, '').strip().lower()
                        if value not in ['true', 'false']:
                            raise ValueError(f"Field '{field}' must be 'True' or 'False', got '{row.get(field)}'") 
                        row[field] = (value == 'true')
                    
                    # Convert slot values to integers
                    for field in ['Day_Slots', 'Night_Slots']:
                        try:
                            row[field] = int(row[field])
                            if row[field] < 0:
                                raise ValueError(f"Field '{field}' must be a non-negative integer")
                        except ValueError:
                            raise ValueError(f"Field '{field}' must be an integer, got '{row.get(field)}'")
                    
                    interviewers.append(row)
                except (ValueError, KeyError) as e:
                    logger.warning(f"Skipping row {row_num} with ID {row.get('Interviewer_ID', 'unknown')}: {e}")
    except Exception as e:
        if isinstance(e, (FileNotFoundError, ValueError)):
            raise
        raise ValueError(f"Error reading CSV file: {e}") from e
                    
    if not interviewers:
        raise ValueError("No valid interviewer data found in the CSV file.")
        
    logger.info(f"Successfully loaded {len(interviewers)} interviewers from {csv_filename}")
    return interviewers

def assign_slots(interviewers: List[Dict[str, Any]], total_expected_slots: int, shift: str) -> Tuple[Dict[str, int], List[Dict[str, Any]]]:
    """
    Assigns slots for the specified shift ('day' or 'night') based on proportional availability.
    
    Steps:
      1. Select interviewers available for the shift.
      2. Calculate the total available slots for the shift.
      3. For each available interviewer, compute the ideal fractional assignment.
      4. Floor the ideal assignments to get initial integer assignments.
      5. Distribute remaining slots based on fractional remainders without exceeding capacity.
      
    Args:
        interviewers: List of interviewer dictionaries
        total_expected_slots: Total number of slots to assign
        shift: 'day' or 'night'
        
    Returns:
        Tuple containing:
            - Dictionary mapping interviewer IDs to assigned slot counts
            - List of available interviewer dictionaries
        
    Raises:
        ValueError: If shift is invalid, no interviewers are available, or no slots are available
    """
    # Validate inputs
    if not isinstance(total_expected_slots, int) or total_expected_slots <= 0:
        raise ValueError(f"Expected slots must be a positive integer, got {total_expected_slots}")
        
    shift = shift.lower()
    if shift == 'day':
        avail_field = 'Day_Available'
        slot_field = 'Day_Slots'
    elif shift == 'night':
        avail_field = 'Night_Available'
        slot_field = 'Night_Slots'
    else:
        raise ValueError(f"Shift must be either 'day' or 'night', got '{shift}'")
    
    # Filter interviewers based on availability in the chosen shift
    available_interviewers = [iv for iv in interviewers if iv[avail_field]]
    
    if not available_interviewers:
        raise ValueError(f"No interviewers available for the {shift} shift.")
    
    # Sum of maximum slots available for the chosen shift
    total_available = sum(iv[slot_field] for iv in available_interviewers)
    if total_available == 0:
        raise ValueError(f"No available slots for the {shift} shift. All interviewers have 0 capacity.")
    
    logger.info(f"Found {len(available_interviewers)} interviewers available for {shift} shift with {total_available} total capacity")
    logger.info(f"Assigning {total_expected_slots} slots for {shift} shift")
    
    assignments: Dict[str, int] = {}
    remainders: Dict[str, float] = {}
    
    # Calculate initial assignment based on proportional share
    for iv in available_interviewers:
        iid = iv['Interviewer_ID']
        capacity = iv[slot_field]
        ideal_slots = (capacity / total_available) * total_expected_slots
        assigned = math.floor(ideal_slots)
        assignments[iid] = assigned
        remainders[iid] = ideal_slots - assigned
    
    assigned_total = sum(assignments.values())
    remaining_slots = total_expected_slots - assigned_total

    # Allocate remaining slots based on highest fractional remainder,
    # ensuring no interviewer exceeds their maximum capacity.
    for iid, _ in sorted(remainders.items(), key=lambda x: (-x[1], x[0])):
        if remaining_slots <= 0:
            break
        interviewer = next(iv for iv in available_interviewers if iv['Interviewer_ID'] == iid)
        capacity = interviewer[slot_field]
        if assignments[iid] < capacity:
            assignments[iid] += 1
            remaining_slots -= 1
    
    # Check if we couldn't assign all slots due to capacity constraints
    if remaining_slots > 0:
        logger.warning(f"Could not assign {remaining_slots} slots due to interviewer capacity constraints")
    
    # Log assignment statistics
    total_assigned = sum(assignments.values())
    utilization = total_assigned / total_available * 100 if total_available > 0 else 0
    logger.info(f"Assigned {total_assigned} out of {total_expected_slots} slots ({utilization:.1f}% utilization)")
            
    return assignments, available_interviewers

def calculate_default_slots(shift: str, slot_duration: int = 40) -> int:
    """
    Calculate the default number of slots based on shift duration and slot duration.
    
    Args:
        shift: 'day' or 'night'
        slot_duration: Duration of each slot in minutes
        
    Returns:
        Number of slots for the specified shift
        
    Raises:
        ValueError: If shift is invalid or slot_duration is not positive
    """
    if not isinstance(slot_duration, int) or slot_duration <= 0:
        raise ValueError(f"Slot duration must be a positive integer, got {slot_duration}")
        
    shift = shift.lower()
    if shift == 'day':
        # Day shift: 6 am - 8 pm (14 hours)
        slots = int((14 * 60) / slot_duration)
    elif shift == 'night':
        # Night shift: 8 pm - 6 am (10 hours)
        slots = int((10 * 60) / slot_duration)
    else:
        raise ValueError(f"Shift must be either 'day' or 'night', got '{shift}'")
        
    logger.info(f"Calculated {slots} slots for {shift} shift with {slot_duration}-minute duration")
    return slots


def output_results_text(assignments: Dict[str, int], available_interviewers: List[Dict[str, Any]], 
                     shift: str, slot_duration: int) -> None:
    """
    Output assignment results in text format.
    
    Args:
        assignments: Dictionary of interviewer ID to assigned slots
        available_interviewers: List of available interviewer dictionaries
        shift: 'day' or 'night'
        slot_duration: Duration of each slot in minutes
    """
    shift = shift.lower()
    slot_field = 'Day_Slots' if shift == 'day' else 'Night_Slots'
    total_assigned = sum(assignments.values())
    
    print(f"\n{shift.capitalize()} Shift Roster Assignment")
    print(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Slot duration: {slot_duration} minutes")
    print(f"Total slots assigned: {total_assigned}")
    print("-" * 60)
    
    # Sort by name for better readability
    for iv in sorted(available_interviewers, key=lambda x: x['Name']):
        iid = iv['Interviewer_ID']
        capacity = iv[slot_field]
        assigned = assignments[iid]
        utilization = (assigned / capacity * 100) if capacity > 0 else 0
        
        print(f"{iv['Name']} (ID: {iid})")
        print(f"  Assigned: {assigned} slots out of {capacity} available ({utilization:.1f}%)")
        print(f"  Total time: {assigned * slot_duration} minutes")
    
    print("-" * 60)
    print(f"Total interviewers: {len(available_interviewers)}")
    print(f"Total assigned time: {total_assigned * slot_duration} minutes")
    logger.info(f"Text output generated for {shift} shift with {total_assigned} slots")


def output_results_csv(assignments: Dict[str, int], available_interviewers: List[Dict[str, Any]], 
                    shift: str, slot_duration: int, output_file: Optional[str] = None) -> None:
    """
    Output assignment results in CSV format.
    
    Args:
        assignments: Dictionary of interviewer ID to assigned slots
        available_interviewers: List of available interviewer dictionaries
        shift: 'day' or 'night'
        slot_duration: Duration of each slot in minutes
        output_file: Output file path. If None, generates a default filename.
    """
    shift = shift.lower()
    slot_field = 'Day_Slots' if shift == 'day' else 'Night_Slots'
    
    # Default output filename if not specified
    if output_file is None:
        output_file = f"roster_assignment_{shift}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['Interviewer_ID', 'Name', 'Email', 'Assigned_Slots', 
                        'Available_Slots', 'Assigned_Minutes', 'Utilization_Percentage']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for iv in sorted(available_interviewers, key=lambda x: x['Name']):
                iid = iv['Interviewer_ID']
                capacity = iv[slot_field]
                assigned = assignments[iid]
                utilization = (assigned / capacity * 100) if capacity > 0 else 0
                
                writer.writerow({
                    'Interviewer_ID': iid,
                    'Name': iv['Name'],
                    'Email': iv.get('Email', ''),
                    'Assigned_Slots': assigned,
                    'Available_Slots': capacity,
                    'Assigned_Minutes': assigned * slot_duration,
                    'Utilization_Percentage': f"{utilization:.1f}%"
                })
        
        print(f"CSV output written to: {output_file}")
        logger.info(f"CSV output written to: {output_file}")
    except IOError as e:
        logger.error(f"Error writing CSV file: {e}")
        print(f"Error writing CSV file: {e}")
        raise


def output_results_json(assignments: Dict[str, int], available_interviewers: List[Dict[str, Any]], 
                      shift: str, slot_duration: int, output_file: Optional[str] = None) -> None:
    """
    Output assignment results in JSON format.
    
    Args:
        assignments: Dictionary of interviewer ID to assigned slots
        available_interviewers: List of available interviewer dictionaries
        shift: 'day' or 'night'
        slot_duration: Duration of each slot in minutes
        output_file: Output file path. If None, generates a default filename.
    """
    shift = shift.lower()
    slot_field = 'Day_Slots' if shift == 'day' else 'Night_Slots'
    total_assigned = sum(assignments.values())
    
    # Default output filename if not specified
    if output_file is None:
        output_file = f"roster_assignment_{shift}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    # Prepare the JSON data structure
    result = {
        "metadata": {
            "generated_on": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "shift": shift,
            "slot_duration_minutes": slot_duration,
            "total_slots_assigned": total_assigned,
            "total_interviewers": len(available_interviewers),
            "total_assigned_minutes": total_assigned * slot_duration
        },
        "assignments": []
    }
    
    # Add individual interviewer assignments
    for iv in sorted(available_interviewers, key=lambda x: x['Name']):
        iid = iv['Interviewer_ID']
        capacity = iv[slot_field]
        assigned = assignments[iid]
        utilization = (assigned / capacity * 100) if capacity > 0 else 0
        
        result["assignments"].append({
            "interviewer_id": iid,
            "name": iv['Name'],
            "email": iv.get('Email', ''),
            "assigned_slots": assigned,
            "available_slots": capacity,
            "assigned_minutes": assigned * slot_duration,
            "utilization_percentage": round(utilization, 1)
        })
    
    try:
        with open(output_file, 'w', encoding='utf-8') as jsonfile:
            json.dump(result, jsonfile, indent=2)
        
        print(f"JSON output written to: {output_file}")
        logger.info(f"JSON output written to: {output_file}")
    except IOError as e:
        logger.error(f"Error writing JSON file: {e}")
        print(f"Error writing JSON file: {e}")
        raise


def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments.
    
    Returns:
        Parsed command line arguments
    """
    parser = argparse.ArgumentParser(
        description="Roster assignment for interviewers",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('--file', '-f', default='interviewers_formatted.csv',
                        help='Path to CSV file with interviewer data')
    parser.add_argument('--shift', '-s', choices=['day', 'night'], default='day',
                        help="Shift to schedule ('day' or 'night')")
    parser.add_argument('--slots', '-n', type=int,
                        help='Override the number of slots for the shift')
    parser.add_argument('--duration', '-d', type=int, default=40,
                        help='Duration of each slot in minutes')
    parser.add_argument('--output', '-o', choices=['text', 'csv', 'json'], default='text',
                        help="Output format ('text', 'csv', or 'json')")
    parser.add_argument('--output-file', default=None,
                        help='Output file path for CSV/JSON format')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose logging')
    
    return parser.parse_args()


def main() -> int:
    """
    Main function to run the roster assignment process.
    
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    args = parse_arguments()
    
    # Configure logging level based on verbose flag
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    
    # Handle relative paths for the CSV file
    file_path = args.file
    if not os.path.isabs(file_path):
        # Try current directory first
        if not os.path.exists(file_path):
            # Then try with problem_solving/ prefix
            problem_solving_path = os.path.join('problem_solving', file_path)
            if os.path.exists(problem_solving_path):
                file_path = problem_solving_path
                logger.debug(f"Using file path: {file_path}")
    
    try:
        # Validate slot duration
        if args.duration <= 0:
            raise ValueError(f"Slot duration must be positive, got {args.duration}")
            
        # Determine expected slots based on shift and slot duration
        if args.slots is not None:
            if args.slots <= 0:
                raise ValueError(f"Number of slots must be positive, got {args.slots}")
            total_expected_slots = args.slots
            logger.info(f"Using user-specified {total_expected_slots} slots")
        else:
            total_expected_slots = calculate_default_slots(args.shift, args.duration)
        
        # Read interviewer data
        interviewers = read_interviewers(file_path)
        
        # Assign slots
        assignments, available_interviewers = assign_slots(interviewers, total_expected_slots, args.shift)
        
        # Output results in the specified format
        if args.output == 'text':
            output_results_text(assignments, available_interviewers, args.shift, args.duration)
        elif args.output == 'csv':
            output_results_csv(assignments, available_interviewers, args.shift, args.duration, args.output_file)
        elif args.output == 'json':
            output_results_json(assignments, available_interviewers, args.shift, args.duration, args.output_file)
            
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        logger.error(f"Value error: {e}")
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1
        
    logger.info("Roster assignment completed successfully")
    return 0  # Success

if __name__ == "__main__":
    sys.exit(main())
