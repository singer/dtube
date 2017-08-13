from os import path

from settings import LINE_LEN


def skip_header_and_timestamps(lines):
    header = True
    for line in lines:
        if '00:0' in line:
            header = False
        if not header and '-->' not in line:
            yield line


def filter_crap(word):
    crap = [':', 'c.color']
    return all(c not in word for c in crap)


def gen_lines_with_newlines(words):
    current_len = 0
    for word in words:
        if current_len > LINE_LEN:
            current_len = 0
            yield '\n'
        current_len += len(word)
        yield word


def subtitles_to_text(files, out_dir):
    subtitle_files = filter(lambda name: name.endswith('vtt'), files)
    for filename in subtitle_files:
        with open(path.join(out_dir, filename), 'r') as f:
            lines = f.readlines()
        lines = filter(None, '\n'.join(lines).splitlines())
        lines = list(skip_header_and_timestamps(lines=lines))
        clean_words = list()
        for line in lines:
            words = line.replace('>', ' ').replace('<', ' ').replace('/', ' ').replace(' c ', '').split(' ')
            clean_words.extend(filter(filter_crap, filter(None, words)))
        out_text = ' '.join(gen_lines_with_newlines(clean_words)).replace('\n ', '\n')
        out_filename = filename.replace('vtt', 'txt')
        with open(path.join(out_dir, out_filename), 'w') as outfile:
            outfile.write(out_text)
    return True
