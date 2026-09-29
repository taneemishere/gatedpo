from src.addition import main
import pytest

def test_main(capsys):
    main()
    captured = capsys.readouterr()
    assert '8' in captured.out