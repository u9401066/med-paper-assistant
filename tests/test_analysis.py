import sys
import os
import shutil
import pandas as pd
import numpy as np

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from med_paper_assistant.core.analyzer import Analyzer

def test_analysis():
    # Setup
    data_dir = "test_data"
    results_dir = "test_results"
    
    if os.path.exists(data_dir):
        shutil.rmtree(data_dir)
    if os.path.exists(results_dir):
        shutil.rmtree(results_dir)
        
    analyzer = Analyzer(data_dir=data_dir, results_dir=results_dir)
    
    # 1. Create Dummy Data
    print("Creating dummy data...")
    np.random.seed(42)
    n = 100
    df = pd.DataFrame({
        'Group': np.random.choice(['Control', 'Treatment'], n),
        'Value': np.random.normal(10, 2, n),
        'Age': np.random.randint(20, 60, n)
    })
    # Add effect to Treatment
    df.loc[df['Group'] == 'Treatment', 'Value'] += 2
    
    csv_path = os.path.join(data_dir, "study_data.csv")
    df.to_csv(csv_path, index=False)
    print(f"Data saved to {csv_path}")
    
    # 2. Describe Data
    print("\n--- Describing Data ---")
    desc = analyzer.describe_data("study_data.csv")
    print(desc[:200] + "...")
    
    # 3. Run T-Test
    print("\n--- Running T-Test (Value by Group) ---")
    ttest_res = analyzer.run_statistical_test("study_data.csv", "t-test", "Value", "Group")
    print(ttest_res)
    
    # 4. Run Correlation
    print("\n--- Running Correlation (Value vs Age) ---")
    corr_res = analyzer.run_statistical_test("study_data.csv", "correlation", "Value", "Age")
    print(corr_res)
    
    # 5. Create Plot
    print("\n--- Creating Boxplot ---")
    plot_path = analyzer.create_plot("study_data.csv", "box", "Group", "Value", "group_comparison.png")
    print(f"Plot saved to: {plot_path}")
    
    if os.path.exists(plot_path):
        print("Test PASSED: Plot created.")
    else:
        print("Test FAILED: Plot missing.")

if __name__ == "__main__":
    test_analysis()
