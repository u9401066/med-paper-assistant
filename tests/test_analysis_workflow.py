import sys
import os
import shutil
import pandas as pd
import numpy as np

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from med_paper_assistant.core.analyzer import Analyzer

def simulate_analysis_workflow():
    print("Simulating /mdpaper.data_analysis workflow...")
    
    # Setup
    data_dir = "data"
    results_dir = "results"
    analyzer = Analyzer(data_dir=data_dir, results_dir=results_dir)
    
    # 1. List Files (Mocking agent action)
    print(f"Listing files in {data_dir}...")
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        
    # Create dummy data if not exists
    csv_path = os.path.join(data_dir, "workflow_data.csv")
    if not os.path.exists(csv_path):
        df = pd.DataFrame({'Group': ['A']*50 + ['B']*50, 'Outcome': np.random.randn(100)})
        df.to_csv(csv_path, index=False)
        
    files = os.listdir(data_dir)
    print(f"Found: {files}")
    
    # 2. User Input (Mocking)
    user_file = "workflow_data.csv"
    user_col_group = "Group"
    user_col_val = "Outcome"
    print(f"User selected: {user_file}, Group={user_col_group}, Value={user_col_val}")
    
    # 3. Run Analysis
    print("Running T-Test...")
    res = analyzer.run_statistical_test(user_file, "t-test", user_col_val, user_col_group)
    print(res)
    
    print("Creating Boxplot...")
    plot_path = analyzer.create_plot(user_file, "box", user_col_group, user_col_val)
    print(f"Plot saved to: {plot_path}")
    
    # 4. Verify Result Exists
    if os.path.exists(plot_path):
        print("Analysis Workflow Simulation PASSED.")
    else:
        print("Analysis Workflow Simulation FAILED.")

if __name__ == "__main__":
    simulate_analysis_workflow()
