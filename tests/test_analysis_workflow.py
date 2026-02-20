import os

import numpy as np
import pandas as pd

from med_paper_assistant.infrastructure.services.analyzer import Analyzer


def test_analysis_workflow(tmp_path):
    """Simulate /mdpaper.data_analysis workflow end-to-end."""
    data_dir = str(tmp_path / "data")
    results_dir = str(tmp_path / "results")
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(results_dir, exist_ok=True)

    analyzer = Analyzer(data_dir=data_dir, results_dir=results_dir)

    # Create dummy data
    csv_path = os.path.join(data_dir, "workflow_data.csv")
    df = pd.DataFrame({"Group": ["A"] * 50 + ["B"] * 50, "Outcome": np.random.randn(100)})
    df.to_csv(csv_path, index=False)

    # Run T-Test
    res = analyzer.run_statistical_test("workflow_data.csv", "t-test", "Outcome", "Group")
    assert "T-Test" in res or "T-statistic" in res

    # Create Boxplot
    plot_path = analyzer.create_plot("workflow_data.csv", "box", "Group", "Outcome")
    assert os.path.exists(plot_path)
