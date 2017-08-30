#!/usr/bin/python3
# coding=utf-8

"""All dirty parsers are here."""

from time import strftime

import bs4.element


def catch(element, name=None, _class=None, startswith=''):
    if not isinstance(element, bs4.element.Tag):
        return name is None and _class is None and str(element).startswith(startswith)
    return all((name is None or element.name == name,
                _class is None or element.get('class', []) == ([_class] if _class else []),
                element.text.startswith(startswith)))


def parse_datetime(s):
    """'今天 %H:%M' | '%m月%d日 %H:%M' | '%Y-%m-%d %H:%M:%S'"""
    time_format = '%Y-%m-%d %H:%M:%S'
    date, _, time = s.partition(' ')
    if date == '今天':
        return strftime(time_format)[:11] + time
    if date.endswith('日'):
        return strftime(time_format)[:5] + date[:2] + '-' + date[3:5] + ' ' + time
    return s


def parse_user_info(soup):
    """https://weibo.cn/{user.uid}/info"""
    data = {}
    data['avatar'] = soup.find('img', alt='头像')['src']
    in_basic = False
    for e in soup.body.children:
        if catch(e, 'div', 'c', '会员等级：'):
            data['member'] = 0 if e.text.startswith('会员等级：未开通') else int(e.text[5:e.text.find('级', 6)])
        elif catch(e, 'div', 'tip', '基本信息'):
            in_basic = True
        elif in_basic:
            in_basic = False
            for s in e.children:
                if not isinstance(s, str):
                    continue
                if s.startswith('昵称:'):
                    data['name'] = s[3:]
                elif s.startswith('认证:'):
                    data['verification'] = s[3:]
                elif s.startswith('性别:'):
                    data['gender'] = {'女': 'F', '男': 'M'}[s[3:]]
                elif s.startswith('地区:'):
                    data['location'] = s[3:]
                elif s.startswith('生日:'):
                    data['birthday'] = s[3:]
                elif s.startswith('简介:'):
                    data['description'] = s[3:]
    return data


def parse_user(soup):
    """https://weibo.cn/u/{user.id} .u | https://weibo.cn/{user.alias} .u"""
    data = {}
    try:
        for e in soup.table.div.children:
            if catch(e, 'a', '', '资料'):
                data['id'] = e['href'][1:-5]
        for e in soup.find(class_='tip2').children:
            if catch(e, 'span', 'tc', '微博['):
                data['post_count'] = int(e.text[3:-1])
            elif catch(e, 'a', '', '关注['):
                data['following_count'] = int(e.text[3:-1])
            elif catch(e, 'a', '', '粉丝['):
                data['follower_count'] = int(e.text[3:-1])
        return data
    except:
        return {'id': 0, 'post_count': 0, 'following_count': 0, 'follower_count': 0}


def parse_post(soup):
    """https://weibo.cn/u/{user.uid}?page={page} .c"""
    data = {}
    in_origin = False
    in_forward_reason = False
    for element in soup.children:
        for e in element.children:
            if in_forward_reason and catch(e, 'a', '', '赞['):
                in_forward_reason = False
                data['vote_count'] = int(e.text[2:-1])
            elif in_forward_reason:
                data['content'] += e.text.strip() if isinstance(e, bs4.element.Tag) else e
            elif catch(e, 'span', 'cmt', '转发了微博：'):
                in_origin = True
                data['origin_deleted'] = True
            elif catch(e, 'span', 'cmt', '转发了'):
                in_origin = True
                for i in e.children:
                    if i.name == 'a':
                        if not i.text:
                            data['origin_deleted'] = True
                        else:
                            data['origin_author_url'] = i['href']
                            data['origin_author_name'] = i.text
                    elif i.name == 'img':
                        data.setdefault('origin_author_badges', '')
                        data['origin_author_badges'] += i['alt']
            elif catch(e, 'span', 'ctt'):
                if e.text.strip().endswith('全文'):
                    data[('origin_' if in_origin else '') + 'more'] = True
                data[('origin_' if in_origin else '') + 'content'] = e.text.strip()
            elif catch(e, 'a', '', '赞['):
                data['vote_count'] = int(e.text[2:-1])
            elif catch(e, 'a', '', '转发['):
                data['forward_count'] = int(e.text[3:-1])
            elif catch(e, 'a', 'cc', '评论['):
                data['comment_count'] = int(e.text[3:-1])
                data['id'] = e['href'][e['href'].find('comment/') + 8:e['href'].rfind('?')]
            elif catch(e, 'span', 'ct'):
                data['time'] = parse_datetime(e.text.partition('\xa0')[0])
            elif catch(e, 'a', '', '原图'):
                data[('origin_' if in_origin else '') + 'picture'] = e['href']
            elif catch(e, 'span', 'cmt', '赞['):
                data['origin_vote_count'] = int(e.text[2:-1])
            elif catch(e, 'span', 'cmt', '原文转发['):
                data['origin_forward_count'] = int(e.text[5:-1])
            elif catch(e, 'a', 'cc', '原文评论['):
                data['origin_comment_count'] = int(e.text[5:-1])
                data['origin_id'] = e['href'][e['href'].find('comment/') + 8:e['href'].rfind('?')]
            elif catch(e, 'span', 'cmt', '转发理由:'):
                in_origin = False
                data['content'] = ''
                in_forward_reason = True
            elif catch(e, 'a', '', '组图共'):
                data[('origin_' if in_origin else '') + 'picture_count'] = int(e.text[3:-1])
    return data


def parse_comment(soup):
    """https://weibo.cn/comment/{post.pid}?page={page} .c"""
    data = {}
    can_be_author = True
    for e in soup.children:
        if can_be_author and catch(e, 'a', ''):
            can_be_author = False
            data['author_url'] = e['href']
            data['author_name'] = e.text
        elif catch(e, 'img', ''):
            data.setdefault('author_badges', '')
            data['author_badges'] += e['alt']
        elif catch(e, 'span', 'ctt'):
            data['content'] = e.text.strip()
        elif catch(e, 'span', 'cc', ' 赞['):
            data['vote_count'] = int(e.text[3:-1])
        elif catch(e, 'span', 'cc', '赞['):
            data['vote_count'] = int(e.text[2:-1])
        elif catch(e, 'span', 'cc', '回复'):
            data['id'] = int(e.a['href'][e.a['href'].rfind('/') + 1:e.a['href'].rfind('?')])
        elif catch(e, 'span', 'ct'):
            data['time'] = parse_datetime(e.text.partition('\xa0')[0])
    return data


def parse_vote(soup):
    """https://weibo.cn/attitude/{post.pid}?page={page} .c"""
    data = {}
    for e in soup.children:
        if catch(e, 'a', ''):
            data['user_url'] = e['href']
            data['user_name'] = e.text
        elif catch(e, 'span', 'ct'):
            data['time'] = parse_datetime(e.text.partition('\xa0')[0])
    return data
