import os
import shutil
import sys
import time

# Helper to restore state
def cleanup():
    if os.path.exists('data_test_created'):
        shutil.rmtree('data_test_created')
    if os.path.exists('data_backup'):
        if os.path.exists('data'):
            shutil.rmtree('data')
        os.rename('data_backup', 'data')

def verify():
    print("Starting verification...")
    
    # 1. Back up existing data folder if exists
    if os.path.exists('data'):
        print("Backing up 'data' to 'data_backup'...")
        os.rename('data', 'data_backup')
    
    # 2. Verify 'data' is GONE
    if os.path.exists('data'):
        print("ERROR: Failed to move data folder.")
        return

    print("Confirmed 'data' folder is missing. Attempting to import config/app...")

    # 3. Import app (triggers config execution which should create folder)
    try:
        # We need to make sure we import config from fresh if it was already imported, 
        # but here we are running a new process usually.
        # Adding project root to sys.path
        sys.path.append(os.getcwd())
        
        import config
        print(f"Config loaded. DATA_DIR: {config.DATA_DIR}")
        
        # Check if folder created by config
        if os.path.exists(config.DATA_DIR):
             print("SUCCESS: 'data' folder was created by config import.")
        else:
             print("FAILURE: 'data' folder was NOT created by config import.")

        from src.web.app import app, save_data
        
        # 4. Try save_data
        print("Testing save_data...")
        test_data = {"test": "value"}
        try:
            save_data(test_data)
            print("save_data execution successful.")
            if os.path.exists(os.path.join(config.DATA_DIR, 'data.json')):
                print("SUCCESS: data.json created.")
            else:
                print("FAILURE: data.json not found.")
        except Exception as e:
            print(f"FAILURE: save_data raised exception: {e}")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        # 5. Cleanup
        print("Cleaning up...")
        if os.path.exists('data'):
            shutil.rmtree('data') # Remove the one we created
        
        if os.path.exists('data_backup'):
            print("Restoring backup...")
            os.rename('data_backup', 'data')
        
if __name__ == "__main__":
    verify()
