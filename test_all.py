from app import get_video_id, is_youtube_video_url
from subtitle import filter_crap


def test_tests():
    assert True


def test_get_video_id():
    assert get_video_id('https://www.youtube.com/watch?v=video_id&t=1s') == 'video_id'
    assert get_video_id('httpfwefwefd&t=1s') == None


def test_is_youtube_video_url():
    assert is_youtube_video_url('https://www.youtube.com/watch?v=pFobk_gjqtc')
    assert is_youtube_video_url('https://www.youtube.com/watch?v=pFobk_gjqtc&t=1s')
    assert not is_youtube_video_url('https://www.ya.ru/watch?v=pFobk_gjqtc&t=1s')
    assert not is_youtube_video_url(None)
    assert not is_youtube_video_url('')


def test_filter_crap():
    crappy_string = "the<00:00:08.400><c> world</c><00:00:08.639><c> sucks</c><c.colorE5E5E5><00:00:09.650><c> I'm</c>"
    words = crappy_string.replace('>', ' ').replace('<', ' ').replace('/', ' ').replace(' c ', '').split(' ')
    assert ' '.join(filter(filter_crap, filter(None, words))) == "the world sucks I'm"
