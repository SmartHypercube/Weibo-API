# Weibo API

Some useful API for fetching posts, comments and votes from Sina Weibo (Mobile Version) and save them into SQLite DB.

Any question, problem or suggestion? Feel free to [contact me](mailto:hypercube@0x01.me).

## Examples

```Python
# First, import the lib
from weibo import *

# You need to set the cookie. After logged in, there're 4 ways to do that (choose any one of them):
# 1. Press F12 in the browser, then open https://weibo.cn/. Get the raw cookie string at "Request Headers" -> "Cookie";
#    It should be a very long line like "_T_WM=1234; A=5678; B=abcd". Write it to a file called "cookie.txt" before the
#    program starts.
# 2. Call set_cookie(raw_cookie_string).
# 3. Install "Copy as Curl" plugin and copy a link as a curl command. You should get a very long line like
#    "curl --header 'Host: weibo.cn' --header 'User-Agent: ...' --header 'Cookie: a=1; b=2; c=3' 'https://weibo.cn/'".
#    Call set_cookie_from_curl(curl_command).
# 4. Try to get a "cookie file". I don't know what it is, but some people told me it's pretty easy to get.
#    Call set_cookie_from_file(path_to_the_file).
set_cookie()

# Fetch 微博小秘书's profile
user = fetch_user(1642909335)
print(user)
for info in user.info_set:
    print(info)

# Fetch 微博小秘书's posts
i = 0
for post in fetch_all_posts(user):
    print(post)
    i += 1
    if i == 10:
        break
# Note: You can get all her posts by removing the break, but it seems like if you send more that ~500 requests in ~10
# minutes, you'll get banned for ~10 minutes.

# Fetch comments of 微博小秘书's latest post
latest_post = user.post_set.order_by(Post.time.desc()).get()
i = 0
for comment in fetch_all_comments(latest_post):
    print(comment)
    i += 1
    if i == 10:
        break
# FYI: If you want to fetch comments begin with the 5th page, use fetch_all_comments(latest_post, page=5).

# Fetch votes of 微博小秘书's latest post
i = 0
for vote in fetch_all_votes(latest_post):
    print(vote)
    i += 1
    if i == 10:
        break

# Now, all the information you have fetched is in "weibo.db". That's a SQLite database. You can learn more about SQL to
# perform some powerful queries.
# Also, you can learn more about "peewee", which is the ORM framework I'm using.
for pic in UserInfo.select().where(UserInfo.key == 'avatar'):
    avatar = Picture.get(id=pic)
    print(pic.user.name, avatar.uri)

# Also, you can use other tools to browse "weibo.db" now.
```

## Todos

- Explain what does `Post.loaded` mean.
- Explain what does `Picture.hash` mean.
- Explain everything that are not explained well :-D
