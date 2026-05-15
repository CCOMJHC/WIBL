#python ! /usr/bin/env python3
import pathlib
import argparse

def main():
    # 1. Set up the argument parser
    parser = argparse.ArgumentParser(description="Count GeoJSON files in a directory recursively.")
    
    # 2. Define the -path argument
    parser.add_argument("-path", type=str, required=True, help="The directory path to search.")
    
    # 3. Parse the arguments from the command line
    args = parser.parse_args()
    
    # 4. Perform the search
    folder_to_search = args.path
    path_obj = pathlib.Path(folder_to_search)
    
    # Check if path exists to avoid errors
    if not path_obj.exists():
        print(f"Error: The path '{folder_to_search}' does not exist.")
        return

    # Count the files (case-insensitive for reliability)
    total = sum(1 for f in path_obj.rglob('*') if f.suffix.lower() == '.geojson')
    
    # 5. Print the output in your requested format
    print(f"Found {total} files ending in 'GeoJSON' in {folder_to_search}")

if __name__ == "__main__":
    main()