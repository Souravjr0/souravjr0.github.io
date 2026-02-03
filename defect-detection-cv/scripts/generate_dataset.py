from src.data import generate_dataset


if __name__ == "__main__":
    df = generate_dataset()
    print("Generated", len(df), "samples")