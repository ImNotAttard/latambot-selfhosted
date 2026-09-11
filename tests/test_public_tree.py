from tools.check_public_tree import main


def test_public_tree_is_clean():
    assert main() == 0
