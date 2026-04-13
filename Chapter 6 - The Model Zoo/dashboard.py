import csv
import os
import matplotlib.pyplot as plt


RUNS_DIR = "runs"


def load_all_runs():
    data = []

    for file in os.listdir(RUNS_DIR):
        if file.endswith(".csv"):
            path = os.path.join(RUNS_DIR, file)
            with open(path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    row["Final Score"] = float(row["Final Score"])
                    row["Cost"] = float(row["Cost"])
                    row["Latency"] = float(row["Latency"])
                    row["Run"] = file
                    data.append(row)

    return data


def plot_score_vs_cost(data):
    x = [d["Cost"] for d in data]
    y = [d["Final Score"] for d in data]
    labels = [d["Model"] for d in data]

    plt.figure()
    plt.scatter(x, y)

    for i, label in enumerate(labels):
        plt.annotate(label, (x[i], y[i]))

    plt.xlabel("Cost (USD)")
    plt.ylabel("Final Score")
    plt.title("Score vs Cost (All Runs)")

    plt.savefig("score_vs_cost.png")
    print("📈 Saved: score_vs_cost.png")


def plot_latency_vs_score(data):
    x = [d["Latency"] for d in data]
    y = [d["Final Score"] for d in data]

    plt.figure()
    plt.scatter(x, y)

    plt.xlabel("Latency (s)")
    plt.ylabel("Final Score")
    plt.title("Latency vs Score")

    plt.savefig("latency_vs_score.png")
    print("📈 Saved: latency_vs_score.png")


if __name__ == "__main__":
    data = load_all_runs()
    plot_score_vs_cost(data)
    plot_latency_vs_score(data)