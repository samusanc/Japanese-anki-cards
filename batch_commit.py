import subprocess
import os
import sys

# Files to batch commit
BASE_DIR = '/home/samusanc/samusanc/anki'

def run_git(args):
    print(f"Running: git {' '.join(args)}")
    res = subprocess.run(['git'] + args, cwd=BASE_DIR, capture_output=True, text=True, encoding='utf-8')
    if res.returncode != 0:
        print(f"Error: {res.stderr}")
        return False, res.stderr
    return True, res.stdout

def main():
    # Configure git to not quote paths temporarily/globally for this run
    run_git(['config', 'core.quotepath', 'false'])

    # 1. Get current branch name
    ok, stdout = run_git(['symbolic-ref', '--short', 'HEAD'])
    if ok:
        branch = stdout.strip()
    else:
        # Fallback to main
        branch = 'main'
    print(f"Current branch: {branch}")

    # 2. Get all modified and untracked files
    ok, stdout = run_git(['ls-files', '--others', '--exclude-standard', '--modified'])
    if not ok:
        print("Failed to list files.")
        sys.exit(1)
        
    files = [f.strip() for f in stdout.splitlines() if f.strip()]
    
    if not files:
        print("No files to commit.")
        return

    # Filter out directory names if any, keeping only files
    files = [f for f in files if os.path.isfile(os.path.join(BASE_DIR, f))]
    total_files = len(files)
    print(f"Found {total_files} files to commit.")

    if total_files == 0:
        print("No remaining files to commit.")
        return

    batch_size = 10
    total_batches = (total_files + batch_size - 1) // batch_size
    
    for i in range(total_batches):
        batch_files = files[i * batch_size : (i + 1) * batch_size]
        print(f"\n--- Processing Batch {i+1}/{total_batches} ({len(batch_files)} files) ---")
        
        # Add files in this batch
        add_ok, err = run_git(['add'] + batch_files)
        if not add_ok:
            print(f"Failed to add files for batch {i+1}")
            sys.exit(1)
            
        # Commit batch
        commit_msg = f"Add cards and audios batch {i+1}/{total_batches}"
        commit_ok, err = run_git(['commit', '-m', commit_msg])
        if not commit_ok:
            print(f"Failed to commit batch {i+1}")
            sys.exit(1)
            
        # Push batch
        push_ok, err = run_git(['push', 'origin', branch])
        if not push_ok:
            print(f"Failed to push batch {i+1}. Retrying push...")
            push_ok_retry, err_retry = run_git(['push', 'origin', branch])
            if not push_ok_retry:
                print("Push failed again. Aborting.")
                sys.exit(1)
                
    print("\nAll batches successfully committed and pushed!")

if __name__ == '__main__':
    main()
