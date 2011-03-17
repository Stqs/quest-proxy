# -*- coding: utf8 -*-
import random
import urllib
from flask import Flask, redirect, abort, render_template, request
app = Flask(__name__)

from BeautifulSoup import BeautifulSoup
from MozillaEmulator import *
dl = MozillaEmulator()

class Params():
    
    username = u'Stqs'
    password = u'53377'
    
    session = None
    domain = None
    gid = None
    p__ufps = None
    
    post_params = None
    
    def get_rnd(self):
        return str(random.random())[:12].replace('.', ',')
    
    def get_GET_params(self):
        get = {'rnd': self.get_rnd()}
        if self.gid:
            get.update({'gid': self.gid})
        return get
    
    
params = Params()


def extract_params(form):
    post_params = {}
    for input in form.findAll('input'):
        if input.get('name', None) is None or input.get('value', None) is None:
            continue
            
        if input['name'] == u'Answer': # SKIP ANSWER FIELD = SHOULD BE TAKEN FROM REAL POST
            continue
        if input.get('alt', None) is not None:
            if input['alt'] == u'Ввод': # skip submit button should be taken from real POST
                continue
        post_params.update({input['name']: input['value']})
    params.p__ufps = form['action'].split('?')[-1].split('&')[0].split('=')[-1]
    params.post_params = post_params
    

def parse_html(content, is_game_url):
    """
    Splits page on  header and body and override the,
    """
    content = content.replace('<a href="/', '<a href="/http://%s/' % str(params.domain))
    soup = BeautifulSoup(content)
    soup.prettify()
    head = soup.html.head.contents
    body = soup.html.body.contents
    if is_game_url:
        extract_params(soup.html.body.form)        
    return head, body

def get_login_redirect_link(page):
    soup = BeautifulSoup(page)
    soup.prettify()
    link = soup.html.body.form.font.table.findAll('a')[0]['href']
    return urllib.unquote(link)

@app.route('/<domain>/', methods=['GET'])
def make_login(domain):
    if domain == 'favicon.ico':
        abort(404)
    params.domain = unicode(domain)
    login_url = 'http://%s/wap/Login.aspx?Login=%s&Password=%s' % (params.domain, 
                                                                   params.username,
                                                                   params.password)
    page = dl.download(urllib.unquote(login_url))
    next_url = get_login_redirect_link(page)
    session = next_url.split('/')[-2]
    return redirect('/http://%s%s' % (params.domain, next_url.replace('Default', 'ActiveGames')))


@app.route('/<path:url>', methods=['GET', 'POST'])
def fetch_url(url):
    
    if url == 'favicon.ico' or url == 'robots.txt':
        abort(404)
    if url.split('/')[-1] == 'default.aspx':
        return redirect(url_for('make_login', domain=url.split('/')[2]))
    is_game_url = False 
   
    if request.method == 'GET':
        if 'GameEngine.aspx' in url:
            if params.gid is None:
                params.gid = request.args.get('gid', '')
            new_url = url + "?" + urllib.urlencode(params.get_GET_params())
            is_game_url = True
        else:
            new_url = url
        page = dl.download(urllib.unquote(new_url))
      
    if request.method == 'POST':
        post_params = params.post_params
        # add answer, bonus answers, and put answer commands
        for key, value in request.form.items():
            if key == 'Answer' or key.startswith('PutAnswerCommand'):
                post_params.update({key: value})
                
        get_params = params.get_GET_params()
        get_params.update({'__ufps': params.p__ufps})
        new_url = url + "?" + urllib.urlencode(get_params)
        page = dl.download(urllib.unquote(new_url), postdata=urllib.urlencode(dict([k, v.encode('utf-8')] for k, v in post_params.items())))
        is_game_url = True
        if 'Логин или id' in page:
            return redirect(url_for('make_login', domain=url.split('/')[2]))    
    head, body = parse_html(page, is_game_url)
    return render_template('main.html', head=head, body=body)

if __name__ == "__main__":
    app.debug = True
    app.run(port=8080)
