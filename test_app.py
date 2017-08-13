from app import get_video_id


def test_tests():
    assert True


def test_get_video_id():
    assert get_video_id('https://www.youtube.com/watch?v=video_id&t=1s') == 'video_id'
    assert get_video_id('httpfwefwefd&t=1s') == None
