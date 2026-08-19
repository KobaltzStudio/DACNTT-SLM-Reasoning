from datasets import load_dataset


DATASET_NAME = "openai/gsm8k"
DATASET_CONFIG = "main"


def main():
    print("=" * 60)
    print("GSM8K DATASET INSPECTION")
    print("=" * 60)

    print("\nLoading dataset...")
    print(f"Dataset: {DATASET_NAME}")
    print(f"Config:  {DATASET_CONFIG}")

    dataset = load_dataset(
        DATASET_NAME,
        DATASET_CONFIG,
    )

    print("\nDataset loaded successfully.")
    print("\nDataset:")
    print(dataset)

    # ---------------------------------------------------------
    # Check splits
    # ---------------------------------------------------------
    print("\n" + "=" * 60)
    print("SPLIT INFORMATION")
    print("=" * 60)

    for split_name in dataset:
        print(f"{split_name}: {len(dataset[split_name])} samples")

    if "train" not in dataset:
        raise RuntimeError("ERROR: train split not found.")

    if "test" not in dataset:
        raise RuntimeError("ERROR: test split not found.")

    print("\nTrain split: PASS")
    print("Test split:  PASS")

    # ---------------------------------------------------------
    # Check columns
    # ---------------------------------------------------------
    print("\n" + "=" * 60)
    print("COLUMN INFORMATION")
    print("=" * 60)

    columns = dataset["train"].column_names

    print("Columns:")
    for column in columns:
        print(f"  - {column}")

    required_columns = {"question", "answer"}

    if not required_columns.issubset(set(columns)):
        raise RuntimeError(
            f"ERROR: Required columns missing. "
            f"Expected: {required_columns}"
        )

    print("\nRequired columns: PASS")

    # ---------------------------------------------------------
    # Inspect examples
    # ---------------------------------------------------------
    print("\n" + "=" * 60)
    print("FIRST 3 TRAIN EXAMPLES")
    print("=" * 60)

    for i in range(min(3, len(dataset["train"]))):
        sample = dataset["train"][i]

        print("\n" + "-" * 60)
        print(f"Example {i}")
        print("-" * 60)

        print("\nQuestion:")
        print(sample["question"])

        print("\nAnswer:")
        print(sample["answer"])

    # ---------------------------------------------------------
    # Inspect test example
    # ---------------------------------------------------------
    print("\n" + "=" * 60)
    print("FIRST TEST EXAMPLE")
    print("=" * 60)

    test_sample = dataset["test"][0]

    print("\nQuestion:")
    print(test_sample["question"])

    print("\nAnswer:")
    print(test_sample["answer"])

    # ---------------------------------------------------------
    # Final result
    # ---------------------------------------------------------
    print("\n" + "=" * 60)
    print("GSM8K INSPECTION RESULT")
    print("=" * 60)

    print("Dataset loading:       PASS")
    print("Train split:           PASS")
    print("Test split:            PASS")
    print("Question field:        PASS")
    print("Answer field:          PASS")
    print("Dataset inspection:    PASS")

    print("\nGSM8K is ready for the next stage.")


if __name__ == "__main__":
    main()