"""
Example test file for Python/ML service
Thêm các tests thực tế của bạn vào đây
"""
import pytest


def test_example_addition():
    """Test cơ bản để verify pytest hoạt động"""
    assert 1 + 1 == 2


def test_example_string():
    """Test string operations"""
    assert "hello".upper() == "HELLO"


@pytest.mark.unit
def test_example_list():
    """Test list operations"""
    my_list = [1, 2, 3]
    my_list.append(4)
    assert len(my_list) == 4
    assert my_list[-1] == 4


# Uncomment khi có app module setup
# def test_app_imports():
#     """Test that app modules can be imported"""
#     from app import config
#     assert config is not None


# def test_tensorflow_import():
#     """Test TensorFlow can be imported"""
#     import tensorflow as tf
#     assert tf.__version__ is not None
