#!/usr/bin/env python3
"""
Roster Assignment for Interviewers

This script reads a CSV file "interviewers.csv" with interviewer details,
their availability for shifts, and their maximum interview slots per shift.
It computes a proportional assignment, ensuring:
  - Only available interviewers (per selected shift) are considered.
  - Each interviewer is not assigned more slots than their per-shift limit.
  - 1 slot corresponds to a 40-minute interview.
  
Shifts:
  • Day shift: 6 am – 8 pm (typically 21 slots: 14 hours * 60 / 40)
  • Night shift: 8 pm – 6 am (typically 15 slots: 10 hours * 60 / 40)
  
Usage:
  Ensure the "interviewers.csv" file is present with appropriate structure.
  Run the script using: python3 roster_assignment.py
"""

import csv
import math
import sys

def read_interviewers(csv_filename):
    """
    Reads the CSV file and returns a list of interviewer dictionaries.
    Expected CSV columns:
      Interviewer_ID, Name, Email, Day_Available, Night_Available, Day_Slots, Night_Slots
    """
    interviewers = []
    with open(csv_filename, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Convert availability flags from string to boolean (accepts "True"/"False" in any case)
            row['Day_Available'] = row['Day_Available'].strip().lower() == 'true'
            row['Night_Available'] = row['Night_Available'].strip().lower() == 'true'
            # Convert slot values to integers
            row['Day_Slots'] = int(row['Day_Slots'])
            row['Night_Slots'] = int(row['Night_Slots'])
            interviewers.append(row)
    return interviewers

def assign_slots(interviewers, total_expected_slots, shift):
    """
    Assigns slots for the specified shift ('day' or 'night') based on proportional availability.
    
    Steps:
      1. Select interviewers available for the shift.
      2. Calculate the total available slots for the shift.
      3. For each available interviewer, compute the ideal fractional assignment.
      4. Floor the ideal assignments to get initial integer assignments.
      5. Distribute remaining slots based on fractional remainders without exceeding capacity.
    """
    if shift.lower() == 'day':
        avail_field = 'Day_Available'
        slot_field = 'Day_Slots'
    elif shift.lower() == 'night':
        avail_field = 'Night_Available'
        slot_field = 'Night_Slots'
    else:
        raise ValueError("Shift must be either 'day' or 'night'")
    
    # Filter interviewers based on availability in the chosen shift
    available_interviewers = [iv for iv in interviewers if iv[avail_field]]
    
    # Sum of maximum slots available for the chosen shift
    total_available = sum(iv[slot_field] for iv in available_interviewers)
    if total_available == 0:
        raise ValueError("No available slots for the selected shift.")
    
    assignments = {}
    remainders = {}
    
    # Calculate initial assignment based on proportional share
    for iv in available_interviewers:
        iid = iv['Interviewer_ID']
        capacity = iv[slot_field]
        ideal_slots = (capacity / total_available) * total_expected_slots
        assigned = math.floor(ideal_slots)
        assignments[iid] = assigned
        remainders[iid] = ideal_slots - assigned
    
    assigned_total = sum(assignments[iid] for iid in assignments)
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
            
    return assignments, available_interviewers

def main():
    csv_filename = 'interviewers.csv'
    
    # Specify the shift. Change to 'night' if needed.
    shift = 'day'
    # Determine expected slots based on shift:
    # Day shift (6 am - 8 pm) typically has 21 slots (840 mins / 40)
    # Night shift (8 pm - 6 am) typically has 15 slots (600 mins / 40)
    total_expected_slots = 21 if shift.lower() == 'day' else 15
    
    try:
        interviewers = read_interviewers(csv_filename)
    except FileNotFoundError:
        sys.exit(f"CSV file '{csv_filename}' not found.")
    except Exception as e:
        sys.exit(f"Error reading CSV: {e}")
        
    try:
        assignments, available_interviewers = assign_slots(interviewers, total_expected_slots, shift)
    except Exception as e:
        sys.exit(f"Error assigning slots: {e}")
    
    print(f"{shift.capitalize()} Shift Roster Slot Assignment (1 slot = 40 minutes):")
    for iv in available_interviewers:
        iid = iv['Interviewer_ID']
        capacity = iv['Day_Slots'] if shift.lower() == 'day' else iv['Night_Slots']
        print(f"{iv['Name']} (ID: {iid}) - Assigned Slots: {assignments[iid]} out of {capacity} available")

if __name__ == "__main__":
    main()
