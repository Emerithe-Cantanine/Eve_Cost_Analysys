# call_find_jumps.py

from Hardcoded_pair_of_systems import find_jumps_between_systems

def main():
    db_path = r"F:\Eve Cost Analysis\CostAnalysis.db"
    start_system = "Jita"
    end_system = "Amarr"

    try:
        jumps = find_jumps_between_systems(db_path, start_system, end_system)
        print(f"Number of jumps between {start_system} and {end_system}: {jumps}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
