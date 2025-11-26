from drun.cli import _iter_unique_env_items


def test_iter_unique_env_items_prefers_first_occurrence():
    env = {
        "BASE_URL": "https://api",
        "base_url": "https://override",
        "USER_USERNAME": "user",
        "user_username": "user_lower",
        "MIXED": "value",
        "mixed": "value_lower",
    }

    items = list(_iter_unique_env_items(env))

    assert items == [
        ("BASE_URL", "https://api"),
        ("USER_USERNAME", "user"),
        ("MIXED", "value"),
    ]
