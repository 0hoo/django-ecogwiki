# -*- coding: utf-8 -*-
def merge_dicts(dicts, sort_values=False, force_list=False):
    merged = {}

    # merge
    for d in dicts:
        for name, value in d.items():
            if name not in merged:
                merged[name] = value
            else:
                if type(merged[name]) != list:
                    merged[name] = [merged[name]]
                if type(value) == list:
                    merged[name] += value
                else:
                    merged[name].append(value)

    # dedup and sort
    dedup = {}
    for k, v in merged.items():
        if type(v) == list:
            v = list(set(v))
            if sort_values:
                v.sort()
            if not force_list and len(v) == 1:
                v = v[0]
        elif force_list:
            v = [v]
        if type(v) != list or len(v) > 0:
            dedup[k] = v
    return dedup


def pairs_to_dict(pairs):
    result = {}

    for k, v in pairs:
        if k not in result:
            result[k] = v
        else:
            if type(result[k]) is list:
                if v not in result[k]:
                    result[k].append(v)
            elif result[k] != v:
                result[k] = [result[k], v]

    return result


regions = {
    u'ㄱ': (u'가', u'나'),
    u'ㄴ': (u'나', u'다'),
    u'ㄷ': (u'다', u'라'),
    u'ㄹ': (u'라', u'마'),
    u'ㅁ': (u'마', u'바'),
    u'ㅂ': (u'바', u'사'),
    u'ㅅ': (u'사', u'아'),
    u'ㅇ': (u'아', u'자'),
    u'ㅈ': (u'자', u'차'),
    u'ㅊ': (u'차', u'카'),
    u'ㅋ': (u'카', u'타'),
    u'ㅌ': (u'타', u'파'),
    u'ㅍ': (u'파', u'하'),
    u'ㅎ': (u'하', u'힣'),
}


def title_grouper(title):
    title = title.upper()
    head = title[0]
    if 'A' <= head <= 'Z' or '0' <= head <= '9':
        return head

    for key, values in regions.items():
        if values[0] <= head < values[1]:
            return key

    return 'Misc'