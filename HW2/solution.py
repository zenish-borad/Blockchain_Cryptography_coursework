def two_sum(nums, target):
    """
    Two Sum — #1
    Approach: hash map for O(n) time, O(n) space.
    For each number, check if (target - number) was already seen.
    If yes, we found the pair. If no, store it for future lookups.
    """
    seen = {}  # value -> index
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []  # no solution found (problem guarantees one, but safe fallback)


def main():
    test_cases = [
        ([2, 7, 11, 15], 9),
        ([3, 2, 4], 6),
        ([3, 3], 6),
        ([1, 5, 8, 12, 7], 15),
    ]

    print("=" * 50)
    print("Two Sum — #1")
    print("Running inside a Docker container")
    print("=" * 50)

    for nums, target in test_cases:
        result = two_sum(nums, target)
        print(f"nums = {nums}, target = {target}  -->  indices {result}")


if __name__ == "__main__":
    main()

