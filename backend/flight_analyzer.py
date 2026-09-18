"""
Cognitive CanSat - Automated Post-Flight Analysis & Mission Reporting System
Alias module linking to ml.flight_analyzer for flexible imports and CLI usage.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ml.flight_analyzer import FlightAnalyzer, analyze_single_flight, analyze_all_test_cases, DEFAULT_DATA_DIR, DEFAULT_OUTPUT_DIR

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Cognitive CanSat Automated Post-Flight Telemetry Analyzer")
    parser.add_argument("--file", help="Path to single telemetry CSV file")
    parser.add_argument("--dir", default=DEFAULT_DATA_DIR, help="Directory containing CSV test cases")
    parser.add_argument("--all", action="store_true", help="Batch analyze all CSV files in --dir")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_DIR, help="Output directory for generated PDFs and PNGs")

    args = parser.parse_args()

    if args.file:
        analyze_single_flight(args.file, args.output)
    else:
        analyze_all_test_cases(args.dir, args.output)
