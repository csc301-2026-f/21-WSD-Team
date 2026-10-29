from backend.algorithms.algo01.greedy_selection import select_files_greedy

def test_greedy_sorts_candidates_independently():
    """Test even if frenquency is not guaranteed by order, greedy algo still pick most frequently read"""
    gb = 1024 ** 3

    candidates = [
        {"file_id": "A", "read_rate": 1, "size": 1 * gb},
        {"file_id": "B", "read_rate": 10, "size": 4 * gb},
        {"file_id": "C", "read_rate": 5, "size": 3 * gb},
    ]

    selected = select_files_greedy(candidates, 5*gb, 2, set())

    assert [row["file_id"] for row in selected] == ["B", "A"]