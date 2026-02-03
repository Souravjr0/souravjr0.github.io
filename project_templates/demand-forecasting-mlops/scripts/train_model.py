from src.train import train_and_evaluate


if __name__ == "__main__":
    metrics = train_and_evaluate()
    print("Training complete:", metrics)
