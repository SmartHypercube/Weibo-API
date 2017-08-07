#!/usr/bin/python3
# coding=utf-8

import urllib.request
from urllib.parse import urlencode

from bs4 import BeautifulSoup

from models import *
from parsers import *

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:49.0) Gecko/20100101 Firefox/49.0'
try:
    with open('cookie.txt') as f:
        COOKIE = f.read().strip()
except FileNotFoundError:
    COOKIE = ''


def set_cookie_from_file(path):
    global COOKIE
    import http.cookiejar
    cookie = http.cookiejar.MozillaCookieJar()
    cookie.load(path, ignore_discard=True, ignore_expires=True)
    COOKIE = '; '.join(i.name + '=' + i.value for i in cookie)


def set_cookie_from_curl(curl):
    global COOKIE
    start = curl.find('Cookie: ') + 8
    end = curl.find("'", start)
    COOKIE = curl[start:end]


def set_cookie(cookie):
    global COOKIE
    COOKIE = cookie


def paged(func):
    def wrapper(*args, page=1, **kwargs):
        max_page = page
        blank_pages = 0
        while page <= max_page or blank_pages < 10:
            print('page:', page, flush=True)
            result = yield from func(*args, page=page, **kwargs)
            if result:
                max_page = result
            if page > max_page:
                if result:
                    blank_pages = 0
                else:
                    blank_pages += 1
            page += 1

    return wrapper


def open_url(url, cookie=COOKIE, user_agent=USER_AGENT, data=None):
    if data:
        data = urlencode(data).encode()
    req = urllib.request.Request(url, data=data, headers={'Cookie': cookie, 'User-Agent': user_agent})
    with urllib.request.urlopen(req) as http:
        return BeautifulSoup(http, 'lxml')


def fetch_user(id, cookie=COOKIE, user_agent=USER_AGENT):
    data = parse_user_info(open_url('https://weibo.cn/%d/info' % id, cookie, user_agent))
    data.update(parse_user(open_url('https://weibo.cn/u/%d' % id, cookie, user_agent).find(class_='u')))
    user, created = User.get_or_create(uid=id, defaults={'name': data['name']})
    if not created:
        user.name = data['name']
        user.save()
    picture, created = Picture.get_or_create(uri=data['avatar'])
    data['avatar'] = picture.id
    for i in ('avatar',
              'member',
              'verification',
              'gender',
              'location',
              'birthday',
              'description',
              'post_count',
              'following_count',
              'follower_count'):
        info, created = UserInfo.get_or_create(user=user, key=i, defaults={'value': data.get(i)})
        if not created:
            info.value = data.get(i)
            info.save()
    return user


def url_to_user(url, name, cookie=COOKIE, user_agent=USER_AGENT):
    if url is None:
        return None
    if url.startswith('/'):
        url = 'https://weibo.cn' + url
    s = url[url.find('.cn/') + 4:].partition('?')[0]
    if s.startswith('u/'):
        user, created = User.get_or_create(uid=s[2:], defaults={'name': name})
        return user
    try:
        info = UserInfo.get(key='alias', value=s)
        user = info.user
    except UserInfo.DoesNotExist:
        data = parse_user(open_url(url, cookie, user_agent))
        user, created = User.get_or_create(uid=data['id'], defaults={'name': name})
        info, created = UserInfo.get_or_create(user=user, key='alias', defaults={'value': s})
        if not created:
            info.value = s
            info.save()
    return user


def search_user(name, cookie=COOKIE, user_agent=USER_AGENT):
    doc = open_url('https://weibo.cn/search/?pos=search', cookie, user_agent, data={'keyword': name, 'suser': '找人'})
    e = doc.table.find_all('a')[1]
    return url_to_user(e['href'], e.text)


@paged
def fetch_all_posts(user, page, cookie=COOKIE, user_agent=USER_AGENT):
    doc = open_url('https://weibo.cn/u/%d?page=%d' % (user.uid, page), cookie, user_agent)
    state = False
    has_result = False
    for element in doc.body.find_all('div'):
        if 'class' not in element.attrs:
            continue
        if element['class'] == ['pms']:
            state = True
        if element['class'] == ['pa']:
            return int(element.text[element.text.rfind('/') + 1:-1]) if has_result else None
        if element['class'] == ['pm']:
            return
        if element['class'] != ['c']:
            continue
        if not state:
            continue
        if element.text.endswith('还没发过微博.'):
            return
        has_result = True
        data = parse_post(element)
        origin = None
        if data.get('origin_id'):
            origin, created = Post.get_or_create(pid=data['origin_id'], defaults={
                'loaded': False,
                'author': url_to_user(data.get('origin_author_url'), data.get('origin_author_name')),
                'text': data.get('origin_content'),  # XXX: we'll deal with origin_more in the next version
                'picture_count': data.get('origin_picture_count', int('origin_picture' in data)),
                'deleted': data.get('origin_deleted', False),
                'vote_count': data['origin_vote_count'],
                'forward_count': data['origin_forward_count'],
                'comment_count': data['origin_comment_count'],
            })
            if not created:
                if data.get('origin_deleted'):
                    origin.deleted = True
                else:
                    origin.vote_count = data['origin_vote_count']
                    origin.forward_count = data['origin_forward_count']
                    origin.comment_count = data['origin_comment_count']
                origin.save()
        post, created = Post.get_or_create(pid=data['id'], defaults={
            'author': user,
            'time': data['time'],
            'text': data['content'],
            'origin': origin,
            'picture_count': data.get('picture_count', int('picture' in data)),
            'vote_count': data['vote_count'],
            'forward_count': data['forward_count'],
            'comment_count': data['comment_count'],
        })
        if not created:
            if not data.get('more'):
                post.text = data['content']
            post.loaded = True
            post.author = user
            post.time = data['time']
            post.origin = origin
            post.picture_count = data.get('picture_count', int('picture' in data))
            post.vote_count = data['vote_count']
            post.forward_count = data['forward_count']
            post.comment_count = data['comment_count']
            post.save()
        yield post


@paged
def fetch_all_comments(post, page, cookie=COOKIE, user_agent=USER_AGENT):
    doc = open_url('https://weibo.cn/comment/%s?page=%d' % (post.pid, page), cookie, user_agent)
    state = False
    has_result = False
    for element in doc.body.find_all('div'):
        if 'class' not in element.attrs:
            continue
        if element['class'] == ['pms']:
            state = True
        if element['class'] == ['pa']:
            return int(element.text[element.text.rfind('/') + 1:-1]) if has_result else None
        if element['class'] == ['pm']:
            return
        if element['class'] != ['c']:
            continue
        if not state:
            continue
        if element.text == '查看更多热门>>':
            continue
        if element.text == '还没有人针对这条微博发表评论!':
            return
        has_result = True
        data = parse_comment(element)
        comment, created = Comment.get_or_create(cid=data['id'], defaults={
            'post': post,
            'author': url_to_user(data['author_url'], data['author_name']),
            'time': data['time'],
            'text': data['content'],
            'vote_count': data['vote_count'],
            'reply_count': 0,
        })
        if not created:
            comment.text = data['content']
            comment.vote_count = data['vote_count']
            comment.save()
        yield comment


@paged
def fetch_all_votes(post, page, cookie=COOKIE, user_agent=USER_AGENT):
    doc = open_url('https://weibo.cn/attitude/%s?page=%d' % (post.pid, page), cookie, user_agent)
    state = False
    has_result = False
    for element in doc.body.find_all('div'):
        if 'class' not in element.attrs:
            continue
        if element['class'] == ['pms']:
            state = True
        if element['class'] == ['pa']:
            return int(element.text[element.text.rfind('/') + 1:-1]) if has_result else None
        if element['class'] == ['pm']:
            return
        if element['class'] != ['c']:
            continue
        if not state:
            continue
        data = parse_vote(element)
        # XXX
        if 'time' not in data:
            return
        has_result = True
        vote, created = PostVote.get_or_create(post=post, user=url_to_user(data['user_url'], data['user_name']))
        yield vote
