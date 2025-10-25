import os
from pathlib import Path

def process_file(filepath):
    """
    Placeholder function to process a single file.
    Replace this with your actual file processing logic.
    """
    print(f"Processing file: {filepath}")
    # Example: Read content, analyze, etc.
    # with open(filepath, 'r') as f:
    #     content = f.read()
    #     print(f"Content of {os.path.basename(filepath)}: {content[:50]}...")


def traverse_recursively(root_dir):
    """
    Recursively traverses a directory, processes each file,
    and extracts path prefixes for each level.
    """
    docs = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for f in filenames:
            docs.append(os.path.join(dirpath, f))
    
    return docs

def traverse_and_process(root_dir):
    """
    Recursively traverses a directory, processes each file,
    and extracts path prefixes for each level.
    """
    if not os.path.isdir(root_dir):
        print(f"Error: '{root_dir}' is not a valid directory.")
        return

    print(f"Starting traversal from: {root_dir}")

    docs = []

    for dirpath, dirnames, filenames in os.walk(root_dir):
        for f in filenames:
            #print("File: {}".format(f))
            docs.append(os.path.join(dirpath, f))
            # d = {"path" : os.path.join(dirpath, f)}
            # d["source"] = Path(f).stem
            # pathParts = dirpath.split(os.sep)
            # categories = [p for p in pathParts if p != "." and p != root_dir]
            # print("Categories: {}".format(categories))
            # #store 3 levels of category
            # d["category"] = categories[0] if len(categories) > 0 else ""
            # d["subcategory"] = categories[1] if len(categories) > 1 else ""
            # d["subsubcategory"] = categories[2] if len(categories) > 2 else ""
            # docs.append(d)
            
    return docs
        # # Extract path prefixes for the current level
        # relative_path = os.path.relpath(dirpath, root_dir)
        # path_parts = relative_path.split(os.sep) if relative_path != '.' else []
        # print("Path_parts: {}".format(path_parts)) 

        # # Print path prefixes for the current directory level
        # if path_parts:
        #     current_prefix = ""
        #     print(f"\nDirectory Level Prefixes for '{relative_path}':")
        #     for i, part in enumerate(path_parts):
        #         current_prefix = os.path.join(current_prefix, part) if current_prefix else part
        #         print(f"  Level {i+1}: {os.path.join(root_dir, current_prefix)}")
        # else:
        #     print("\nAt the root directory level.")


        # # Process files in the current directory
        # for filename in filenames:
        #     filepath = os.path.join(dirpath, filename)
        #     process_file(filepath)

# Example usage:
if __name__ == "__main__":
    # # Create a dummy directory structure for testing
    test_dir = "/Users/cwts/Documents/"
    # os.makedirs(os.path.join(test_dir, "subdir1", "subsubdirA"), exist_ok=True)
    # os.makedirs(os.path.join(test_dir, "subdir2"), exist_ok=True)

    # with open(os.path.join(test_dir, "file1.txt"), "w") as f:
    #     f.write("This is file 1.")
    # with open(os.path.join(test_dir, "subdir1", "file2.log"), "w") as f:
    #     f.write("Log entry 1.")
    # with open(os.path.join(test_dir, "subdir1", "subsubdirA", "data.csv"), "w") as f:
    #     f.write("header1,header2\nvalue1,value2")

    docs = traverse_and_process(test_dir)
    print("Docs: {}".format(docs))
    print("Number of docs: {}".format(len(docs)))

    # Clean up the dummy directory (optional)
    #import shutil
    #shutil.rmtree(test_dir)