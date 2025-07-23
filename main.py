import schedule
import time
import os
import subprocess

def job():
    print("Starting the daily LinkedIn posting job...")
    
    # Step 1: Run the agent to generate a new post
    print("Running agent.py to generate a new post...")
    subprocess.run(["python", "agent.py"], check=True)
    
    # Step 2: Run the poster to publish the post
    print("Running linkedin_poster.py to publish the post...")
    subprocess.run(["python", "linkedin_poster.py"], check=True)
    
    print("Daily job finished.")

# Schedule the job to run every day at 9:00 AM EAT.
# Note: The time is based on the system time of the computer running the script.
# Please ensure your system's timezone is set correctly or adjust the time accordingly.
schedule.every().day.at("09:00").do(job)

print("Scheduler started. The job will run every day at 9:00 AM EAT.")
print("Press Ctrl+C to exit.")

# Keep the script running to allow the scheduler to work
while True:
    schedule.run_pending()
    time.sleep(1)
