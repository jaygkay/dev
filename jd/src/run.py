# -*- coding: utf-8 -*-
from __future__ import with_statement
import ast
import csv
import time
import re
import numpy as np
import pandas as pd
from sqlite3 import dbapi2 as sqlite3
from hashlib import md5
import httplib2
import logging
import uuid
import json
import requests
from datetime import datetime
from contextlib import closing
import googleapiclient.discovery
import google.oauth2.credentials
from flask import Flask, request, session, url_for, redirect, \
     render_template, abort, g, flash, current_app
import oauth2client
from oauth2client.contrib.flask_util import UserOAuth2
from flask_login import current_user

# from flask_login import login_user , logout_user, LoginManager
from werkzeug.security import check_password_hash, generate_password_hash
from wtforms import Form, TextField, validators
# from flask_googlelogin import GoogleLogin
# from flask_login import LoginManager
# login_manager = LoginManager()
#
# login_manager.init_app(app)
'''
- Change Font
- create another DB that contains all infor that admin has editeed
- Finalizing the db with sending an email with attachment of docx
- 로그인 문구( 보인님께서 공유)
- switch 직렬 직무 on main home
- "특수문자" -> 그대로 살리 (researching)... ex) slash and &
- strings choppy
- 직무 category -> 직렬
- search bar from  직렬 to 직무
- 직무, 팀 네이밍 유지보수 프로그래밍 하나 짜야함 
- only new files to implement
=======
- 웹크롤링 이번주에 기능 끝내야함
'''

# configuration
DATABASE = 'People_Lab.db'
PER_PAGE = 30
DEBUG = True
SECRET_KEY = 'development key'

# --------------------------------------------------------------------------------------------------------
#                                              CONFIGURATIONS
# --------------------------------------------------------------------------------------------------------


# def _request_user_info(credentials):
#     """
#     Makes an HTTP request to the Google+ API to retrieve the user's basic
#     profile information, including full name and photo, and stores it in the
#     Flask session.
#     """
#     http = httplib2.Http()
#     credentials.authorize(http)
#     resp, content = http.request(
#         'https://www.googleapis.com/plus/v1/people/me')
#
#     if resp.status != 200:
#         current_app.logger.error(
#             "Error while obtaining user profile: \n%s: %s", resp, content)
#         return None
#     session['profile'] = json.loads(content.decode('utf-8'))


app = Flask(__name__)
app.config.from_object(__name__)
# app.config['SECRET_KEY'] = 'fearofgod_jd_web'
app.secret_key = str(uuid.uuid4())
# app.config['GOOGLE_OAUTH2_CLIENT_SECRETS_FILE'] = 'client_secret.json'
app.config['GOOGLE_OAUTH2_CLIENT_ID'] = '106867125570-6j0vgo05rqjqiq1uqvg03hcrf148lcvu.apps.googleusercontent.com'
app.config['GOOGLE_OAUTH2_CLIENT_SECRET'] = 'yymHdr1-gQuDq3VtLIhCF2VD'
# app.config.from_envvar('MINITWIT_SETTINGS', silent=True)
app.jinja_env.filters['zip'] = zip
logging.basicConfig(level=logging.INFO)

oauth2 = UserOAuth2()
oauth2.init_app(
    app,
    scopes=['email', 'profile'],
    # authorize_callback=_request_user_info,
    client_id=app.config['GOOGLE_OAUTH2_CLIENT_ID'],
    client_secret=app.config['GOOGLE_OAUTH2_CLIENT_SECRET'],
    prompt='consent'
)

# [START init_app]
# Initalize the OAuth2 helper.
# --------------------------------------------------------------------------------------------------------
#                                              LOGIN FUNCTION
# --------------------------------------------------------------------------------------------------------


# @app.route('/index')
# def index():
#     the_name = oauth2.credentials.id_token['name']
#     the_email = oauth2.credentials.id_token['email']
#     the_pic = oauth2.credentials.id_token['picture']
#     return render_template("layout_on.html", the_pic = the_pic)

@app.route('/')
@oauth2.required
def login():
    if oauth2.has_credentials():
        http = httplib2.Http()
        # credentials.authorize(http)
        resp, content = http.request(
            'https://www.googleapis.com/plus/v1/people/me')
        # print("***people",resp, content)
        session['profile'] = json.loads(content.decode('utf-8'))
        print('login OK')
        return redirect(url_for('main_page'))
    else:
        print('login NO')
        return redirect(url_for('main_page'))

@app.route('/logout')
def logout():
    # Delete the user's profile and the credentials stored by oauth2.
    del session['profile']
    session.modified = True
    oauth2.storage.delete()
    return 'log out'
    # return redirect(url_for('main_page'))


# --------------------------------------------------------------------------------------------------------
#                                              Route Functions
# --------------------------------------------------------------------------------------------------------

@app.route('/main')
@oauth2.required
def main_page():
    cnt_all = query_jd_db('''SELECT count(*) FROM JD_features ''')

    cnt_group_comp = query_jd_db('''SELECT 법인명, count(*) FROM JD_features 
                        GROUP BY 법인명 ORDER BY count(*) DESC''')
    cnt_group_comp1 = query_jd_db('''SELECT 직군, count(*) FROM JD_features
                   GROUP BY 직군 ORDER BY count(*) DESC''')
    cnt_group_comp2 = query_jd_db('''SELECT 직렬, count(*) FROM JD_features
                       GROUP BY 직렬 ORDER BY count(*) DESC''')
    # 1. 검색
    key_word = str(request.args.get('검색'))
    if key_word == str(None) or key_word == '' or key_word == None:
        query = query_jd_db('''select 법인명, 팀명, 직군, 직렬, 직무, 파일명 from JD_features''')
        comp_word = "전체 JD"
    else:
        comp_word = key_word
        query = query_jd_db('''
                select 법인명, 팀명, 직군, 직렬, 직무, 파일명
                from JD_features
                where 직무 LIKE '%''' + key_word + '''%'
                ''')
    key = ''

    # 2. 법인별, 직군별, 직무별
    for key, val in request.args.to_dict().items():
        if key == '법인':
            comp_word = str(request.args.get('법인'))
            query = query_jd_db('''
                                select 법인명, 팀명, 직군, 직렬, 직무, 파일명
                                from JD_features
                                where 법인명 = "''' + comp_word + '''"
                                ''')
        elif key == '직군':
            comp_word = str(request.args.get('직군'))
            query = query_jd_db('''
                                select 법인명, 팀명, 직군, 직렬, 직무, 파일명
                                from JD_features
                                where 직군 = "''' + comp_word + '''"
                                ''')
        elif key == '직렬':
            comp_word = str(request.args.get('직렬'))
            query = query_jd_db('''
                                select 법인명, 팀명, 직군, 직렬, 직무, 파일명
                                from JD_features
                                where 직렬 = "''' + comp_word + '''"
                                ''')
        elif key == '검색':
            comp_word = str(request.args.get('검색'))
            query = query_jd_db('''
                                select 법인명, 팀명, 직군, 직렬, 직무, 파일명
                                from JD_features
                                where 직무 LIKE '%''' + comp_word + '''%'
                ''')
        else:
            comp_word = key_word
            query = query_jd_db('''select 법인명, 팀명, 직군, 직렬, 직무, 파일명 from JD_features''')

    the_name = oauth2.credentials.id_token['name']
    the_email = oauth2.credentials.id_token['email']
    the_pic = oauth2.credentials.id_token['picture']
    return render_template('jd_list.html', cnt_all = cnt_all[0][0], messages=query,
                           comp_word=comp_word, key=key,cnt_group_comp = cnt_group_comp,
                           cnt_group_comp1 = cnt_group_comp1,cnt_group_comp2 = cnt_group_comp2,
                           the_name = the_name, the_pic= the_pic)


@app.route('/jd_show')
def show_jd():
    key_word = str(request.args.get('file_name'))

    aa = query_jd_db(''' 
        SELECT 파일명, 직무, 직무소개, 주요업무책임, 주요업무환경, 필수자격요건, 선호자격요건, 필요역량  
        FROM JD_features where 파일명 ="''' + key_word + '''"''')

    job_file = aa[0][0]
    val1 = aa[0][1]
    val2 = aa[0][2]
    ###
    ans_lst1 = []
    ans1 = aa[0][3]
    if ans1 != 'none' or ans1 != '':
        ans_lst1.append(ast.literal_eval(ans1))
    ans_lst1 = [i for i in ans_lst1[0] if i != '']
    ###
    ans_lst2 = []
    ans2 = aa[0][4]
    if ans2 != "['none']" :
        ans_lst2.append(ast.literal_eval(ans2))
    if len(ans_lst2) != 0:
        tit = "[주요 업무환경]"
        val4 = [" • "+str(i) for i in ans_lst2[0] if i != '']
    else:
        tit = " "
        val4 = " "
    ###
    ans_lst3 = []
    ans3 = aa[0][5]
    if ans3 != "['none']":
        ans_lst3.append(ast.literal_eval(ans3))
    ans_lst3 = [i for i in ans_lst3[0] if i != '']
    ###
    ans_lst4 = []
    ans4 = aa[0][6]
    if ans4 != "['none']" :
        ans_lst4.append(ast.literal_eval(ans4))
    ans_lst4 = [i for i in ans_lst4[0] if i != '']
    # print("**",ans_lst4)
    ###
    ans_lst5 = []
    ans5 = aa[0][7]
    if ans5 != "['none']" :
        ans_lst5.append(ast.literal_eval(ans5))
    ans_lst5 = [i for i in ans_lst5[0] if i != '']
    return render_template('jd_show.html',job_file = job_file,
                           val1=val1, val2=val2, val3=ans_lst1,
                           tit=tit, val4=val4, val5=ans_lst3,
                           val6=ans_lst4, val7=ans_lst5)

@app.route('/jd_create', methods=['GET'])
@oauth2.required
def jd_create():
    # if not g.user:
    #     return redirect(url_for('main_page'))

    key_word = str(request.args.get('검색')).strip()
    create_result = create_jd(key_word)
    if key_word == str(None) or key_word == '':
        query = query_jd_db('''select 법인명, 팀명, 직군, 직렬, 직무, 파일명 from JD_features''')
        key_word = "전체 직무"
    else:
        query = query_jd_db('''
                select 법인명, 팀명, 직군, 직렬, 직무, 파일명
                from JD_features
                where 직무 LIKE '%''' + key_word + '''%'
                ''')

    #####
    # create_result 하나씩 쪼개고, 리스트 변수들은 np.unique 처리 필요
    the_name = oauth2.credentials.id_token['name']
    the_email = oauth2.credentials.id_token['email']
    the_pic = oauth2.credentials.id_token['picture']
    print("line 307",the_name, the_email, the_pic)
    return render_template("jd_create.html", messages = query,key_word= key_word,
                           create_result = create_result, the_pic = the_pic,
                           the_name = the_name, the_email = the_email)


@app.route('/create_result/<key_word>')
def create_jd(key_word):
    key_word = str(request.args.get('검색')).strip()  # [:-1]

    file_lst = [i[0] for i in query_jd_db('''
            SELECT Distinct 파일명 from JD_features
            where 직무 LIKE '%''' + key_word + '''%'
                ''')]
    posi_lst = np.unique([i[0] for i in query_jd_db('''
            SELECT Distinct 직무 from JD_features
            where 직무 LIKE '%''' + key_word + '''%'
                ''')])
    summ_lst = np.unique([i[0] for i in query_jd_db('''
            SELECT Distinct 직무소개 from JD_features
            where 직무 LIKE '%''' + key_word + '''%'
                ''')])
    comp_lst = np.unique([i[0] for i in query_jd_db('''
            SELECT Distinct 법인명 from JD_features
            where 직무 LIKE '%''' + key_word + '''%'
                ''')])
    resp_lst = [ast.literal_eval(i[0]) for i in query_jd_db('''
            SELECT Distinct 주요업무책임 from JD_features
            where 직무 LIKE '%''' + key_word + '''%'
                ''')]
    resp_lst = np.unique(sum(resp_lst, []))

    main_lst = [ast.literal_eval(i[0]) for i in query_jd_db('''
            SELECT Distinct 필수자격 from JD_features
            where 직무 LIKE '%''' + key_word + '''%'
                ''')]
    main_lst = np.unique(sum(main_lst, []))
    main_lst = [i for i in main_lst if i != '']

    pref_lst = [ast.literal_eval(i[0]) for i in query_jd_db('''
            SELECT Distinct 필요역량 from JD_features
            where 직무 LIKE '%''' + key_word + '''%'
                ''')]

    pref_lst = np.unique(sum(pref_lst, []))

    capa_lst = [ast.literal_eval(i[0]) for i in query_jd_db('''
            SELECT Distinct 선호자격요건 from JD_features
            where 직무 LIKE '%''' + key_word + '''%'
                ''')]
    capa_lst = np.unique(sum(capa_lst, []))

    envr_lst1 = [ast.literal_eval(i[0]) for i in query_jd_db('''
            SELECT Distinct 주요업무환경 from JD_features
            where 직무 LIKE '%''' + key_word + '''%'
                ''')]
    envr_lst1 = np.unique([i[0] for i in envr_lst1 if i[0] != 'none'])
    envr_lst = ['주요업무환경 없음']
    for i in envr_lst1:
        envr_lst.append(i)
    degr_lst = ['학력 무관', '전문학사', '학사', '석사', '박사']

    all_lst = ['IT', 'S/W', '경영학', '공학계열', '교육공학', '교육학', '그래픽디자인', '기계', '마케팅',
       '법학', '브랜드매니지먼트', '산업공학', '수학', '스페인어', '시각디자인', '언어교육', '영상디자인',
       '의상디자인', '재무', '전공무관', '전기', '커뮤니케이션', '컴퓨터공학', '텍스타일디자인', '통계학',
       '통번역', '패션디자인', '회계']
    majo_lst = ['전공 무관']
    for i in all_lst:
        majo_lst.append(i)
    mino_lst = ['우대전공 없음']
    for i in all_lst:
        mino_lst.append(i)

    minn_lst = ['최소연차 없음', '신입지원 가능']
    for i in range(1, 4):
        minn_lst.append(str(i) + '년')

    year_lst = [str(i) + '년' for i in range(1, 6)]
    years = ['7년', '10년', '15년']
    for i in years:
        year_lst.append(i)

    back_lst = np.unique([i[0] for i in query_jd_db('''
                SELECT Distinct 경력배경 from JD_features
                where 직무 LIKE '%''' + key_word + '''%'
                    ''') if i[0] != 'none'])
     # back_lst =
    cert_lst1 = [ast.literal_eval(i[0]) for i in query_jd_db('''
                SELECT Distinct 자격증 from JD_features
                where 직무 LIKE '%''' + key_word + '''%'
                    ''')]
    cert_lst1 = np.unique([i[0] for i in cert_lst1 if i[0] != 'none'])

    cert_lst = ['자격증 없음']
    for i in cert_lst1:
        cert_lst.append(i)

    port_lst1 = [ast.literal_eval(i[0]) for i in query_jd_db('''
                SELECT Distinct 포트폴리오 from JD_features
                where 직무 LIKE '%''' + key_word + '''%'
                    ''')]
    port_lst1 = np.unique([i[0] for i in port_lst1 if i[0] != 'none'])
    port_lst = ['포트폴리오 없음']
    for i in port_lst1:
        port_lst.append(i)

    result = [file_lst, comp_lst, posi_lst, summ_lst, resp_lst, main_lst, pref_lst, capa_lst,
              envr_lst, degr_lst, majo_lst, mino_lst, minn_lst, year_lst, back_lst, cert_lst,
              port_lst, key_word]

    return result

def degree_final2(final_majo, final_mino):
    degree = [final_majo]

    if '없음' in final_mino:
        pass
    else:
        for resp in final_mino.split(',')[:-1]:
            degree.append(resp)

    deg_val = []
    if len(degree) == 1:

        if degree[0].strip() == '전공 무관':
            deg_val.append('전공 무관')
        else:
            deg_val.append(str(degree[0]) + ' 관련 전공자')
    else:
        val = str(degree[0]) + " 전공 또는 " + ', '.join(degree[1:]) + " 관련 전공자 우대"
        deg_val.append(val)

    return deg_val

@app.route('/preview_cal', methods=['POST'])
def preview_cal():
    # print("preview_cal")
    the_name = str(request.form.get('the_name'))
    the_email = str(request.form.get('the_email'))
    job_comp = str(request.form.get('job_comp'))
    job_posi = str(request.form.get('position'))
    job_summ = str(request.form.get('job_summ'))
    job_resp = str(request.form.get('job_resp'))
    job_envr = str(request.form.get('job_envr'))
    job_main = str(request.form.get('job_main'))
    job_pref = str(request.form.get('job_pref'))
    job_capa = str(request.form.get('job_capa'))

    job_degr = str(request.form.get('job_degr'))
    job_majo = str(request.form.get('job_majo'))
    job_mino = str(request.form.get('job_mino'))

    job_minn = str(request.form.get('job_minn'))
    job_expr = str(request.form.get('job_year'))
    job_back = str(request.form.get('job_back'))

    job_cert = str(request.form.get('cert_lst'))
    job_port = str(request.form.get('port_lst'))
    title = str(request.form.get("title"))

    if '없음' in job_envr:
        tit = " "
        val4 = " "
    else:
        tit = "[주요 업무환경]"
        val4 = [" • " + str(i) for i in job_envr.split('\n')[:-1]]

    deg_val = degree_final2(job_majo, job_mino)

    if '없음' in job_minn:
        val = ''
    elif '신입' in job_minn:
        val = '(신입 지원 가능)'
    else:
        val = '(최소 ' + job_minn + ')'

    job_lst = val + ' ' + job_expr + ' ' + job_back

    ############### main 3째 줄에 넣어야
    if '없음' in job_cert:
        job_cert = ''
    else:
        job_cert = job_cert
    if '없음' in job_port:
        job_port = ''
    else:
        job_port = job_port

    job_resp_lst = [re.sub('\r', '', i).strip() for i in job_resp.split('\n')[:-1]]
    # job_mino_lst = [re.sub('\r', '', i).strip() for i in job_mino.split('\n')[:-1]]
    job_mino_lst = [i.strip() for i in job_mino.split(',')[:-1]]
    # print("**", job_mino_lst)
    job_main_lst = [job_cert] + [re.sub('\r', '', i).strip() for i in job_main.split('\n')[:-1]]

    # majors = []
    job_pref_lst = [re.sub('\r', '', i).strip() for i in job_pref.split('\n')[:-1]] + [job_port]
    job_capa_lst = [re.sub('\r', '', i).strip() for i in job_capa.split('\n')[:-1]]

    job_main_lst = [i for i in job_main_lst if i != '']  # + job_mino_lst ######3
    job_pref_lst = [i for i in job_pref_lst if i != '']

    job_summ = [re.sub('\r', '', i).strip() for i in job_summ.split('\n')[:-1]]
    val4 = [re.sub('\r','',re.sub('•','', val4[0].strip()))]

    if job_degr == '학력 무관':
        job_print = job_degr
    else:
        job_print = job_degr + ' 이상'

    print("line457", deg_val)
    # if job_print
    allall = [[str(job_print)], deg_val, [job_lst], [job_main_lst]]
    allall = sum(allall,[])
    print("line:459",allall)
    thus = [the_name, the_email, job_posi, job_summ[0], job_resp_lst,
            tit, val4, job_degr, job_majo, job_mino_lst,
            deg_val, job_minn, job_expr, job_back, job_lst,
            job_main_lst, job_pref_lst, job_capa_lst, job_cert, job_port,
            allall]
    return thus

@app.route('/preview', methods=['POST'])
def preview():
    # print("preview")
    thus = preview_cal()
    # print("line477",thus[8])

    return render_template("preview.html",thus = thus, job_posi=thus[2],
                           job_summ=thus[3],job_resp=thus[4], tit=thus[5], val4=thus[6],
                           job_degr=thus[7],job_majo=thus[8], job_mino=thus[9],
                           deg_val=thus[10],job_minn=thus[11], job_expr=thus[12],
                           job_back=thus[13], job_lst=thus[14],job_main=thus[15],
                           job_pref=thus[16], job_capa=thus[17],job_cert=thus[18],
                           job_port=thus[19], job_all = thus[20])

@app.route('/feedback', methods=['POST'])
def add_feedback():
    """Registers a new message for the user."""
    # if 'user_id' not in session:
    #     abort(401)
    # else:
    # if request.form['text']:

    thus = preview_cal()
    # print("line 504",thus)
    today = re.sub("-", '', str(datetime.today()))
    ymd = today.split(" ")[0]
    ymd = ymd[:4]+"-"+ymd[4:6]+"-"+ymd[6:]
    hms = today.split(" ")[1].split('.')[0][:-3]
    at_datetime = ymd+" @"+hms
    # print(at_datetime)
    # print("line510",thus)
    # the_name = oauth2.credentials.id_token['name']
    # the_email = oauth2.credentials.id_token['email']
    # print(thus[0], thus[1])
    print("the_name", thus[0])
    print("the_email", thus[1])
    print("job_posi", thus[2])
    print("job_summ", thus[3])
    print("job_resp", thus[4])
    print("tit", thus[5])
    print("val4", thus[6])
    print("job_degr", thus[7])
    print("job_majo", thus[8])
    print("job_mino", thus[9])

    print("deg_val", thus[10])
    print("job_minn", thus[11])
    print("job_expr", thus[12])
    print("job_back", thus[13])
    print("job_lst", thus[14])
    print("job_main", thus[15])
    print("job_pref", thus[16])
    print("job_capa", thus[17])
    print("job_cert", thus[18])
    print("job_port", thus[19])

    print("pub_date", thus[20])
    print("req_date", thus[21])
    print("status", thus[22])

    g.db.execute('''INSERT INTO feedback 
                    (the_name, the_email, job_posi, job_summ, job_resp, 
                    tit, val4, job_degr, job_majo, job_mino, 
                    deg_val,job_minn, job_expr, job_back, job_lst, 
                    job_main, job_pref,job_capa, job_cert, job_port, 
                    pub_date, req_date, status)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                 (str(thus[0]), str(thus[1]), str(thus[2]),str(thus[3]), str(thus[4]),
                  str(thus[5]), str(thus[6]), str(thus[7]),str(thus[8]), str(thus[9]),
                  str(thus[10]), str(thus[11]), str(thus[12]),str(thus[13]), str(thus[14]),
                  str(thus[15]), str(thus[16]), str(thus[17]),str(thus[18]), str(thus[19]),
                  str(thus[20]),at_datetime, at_datetime, '요청'))
    g.db.commit()
    flash('새 JD를 작성하였습니다.')
    return redirect(url_for('feedback_timeline'))

@app.route('/reload', methods=['POST'])
def reload():
    # print("reload['all_data]",request.form['all_data'])
    # print("reload['author_id]", request.form['author_id'])
    # print("reload['pub_date]", request.form['pub_date'])
    # print(str(request.form))
    query = query_jd_db('''
        SELECT * FROM feedback
        WHERE feedback.author_id = "'''+str(request.form['author_id'])+'''"
        AND feedback.pub_date = "'''+str(request.form['pub_date']+'''"'''))

    # # res_lst = list(sum(query, ()))
    # print('직무명 - job_posi:', query[0][1])
    # print('직무 Summary -job_summ:', query[0][2])
    # print('주요업무책임 - job_resp', query[0][3])
    # print('주요업무환경 title - tit:', query[0][4])
    # print('주요업무환경 값 - val4:', query[0][5])
    # print('학위 - job_degr:', query[0][6])
    # print('전공 - job_majo:', query[0][7])
    # print('우대전공 - job_mino:', query[0][8])
    # print('전공 + 우대전공 - deg_val:', query[0][9])
    # print('최소경력 - job_minn:', query[0][10])
    # print('경력연차 - job_expr:', query[0][11])
    # print('경력배경 - job_back:', query[0][12])
    # print('최소+경력+배경- job_lst:', query[0][13])
    #
    # print('필수자격 - job_main:', query[0][14])
    # print('선호자격요건 - job_pref:', query[0][15])
    # print('필요역량 - job_capa:', query[0][16])
    # print('자격증 - job_cert:', query[0][17])
    # print('포트폴리오_port:', query[0][18])
    # print("status",query[0][-1])

    # print('포트폴리오_port:', query[0][18])
    # return redirect(url_for('jd_create'))
    # return render_template('reload.html', job_posi=thus[0],
    return render_template('preview.html', jd_id = query[0][1],job_posi=query[0][2],job_summ=query[0][3],
                           job_resp=ast.literal_eval(query[0][4]), tit=query[0][5],
                           job_envr=ast.literal_eval(query[0][6]),
                           job_degr=query[0][7],job_majo=query[0][8], job_mino=query[0][9],
                           deg_val=ast.literal_eval(query[0][10]),
                           job_minn=query[0][11],  job_expr=query[0][12],
                           job_back=query[0][13],job_lst=query[0][14],job_main=ast.literal_eval(query[0][15]),
                           job_pref=ast.literal_eval(query[0][16]),job_capa=ast.literal_eval(query[0][17]),
                           job_cert=query[0][18],job_port=query[0][19],status = query[0][-1], query = query)


@app.route('/edit', methods=['POST'])
def edit():

    query = query_jd_db('''
        SELECT * FROM feedback
        WHERE feedback.author_id = "'''+str(request.form['author_id'])+'''"
        AND feedback.pub_date = "'''+str(request.form['pub_date']+'''"'''))

    # 법인 리스트
    comp_query = query_jd_db('''
        SELECT DISTINCT 법인명 from JD_features
    ''')
    comp_query = [i[0] for i in comp_query]

    # 직군 리스트
    group_query = query_jd_db('''
            SELECT DISTINCT 직군 from JD_features
        ''')
    group_query = [i[0] for i in group_query]

    # 직무 리스트
    posi_query = query_jd_db('''
                SELECT DISTINCT 직무 from JD_features
            ''')
    posi_query = [i[0] for i in posi_query]

    pub_date = query[0][20]
    edi_date = query[0][21]
    status = query[0][22]

    if '무관' in query[0][7]:
        job = query[0][7]
    else:
        job = query[0][7] + ' 이상'
    allall = [job, query[0][12], query[0][14], ast.literal_eval(query[0][15])]
    who = request.form['username']

    return render_template('edit.html', jd_id=query[0][1],job_posi=query[0][2], job_summ=query[0][3],
                           job_resp=ast.literal_eval(query[0][4]), tit=query[0][5], val4=ast.literal_eval(query[0][6]),
                           job_degr=query[0][7], job_majo=query[0][8], job_mino=query[0][9],
                           deg_val=ast.literal_eval(query[0][10]), job_minn=query[0][11], job_expr=query[0][12],
                           job_back=query[0][13], job_lst=query[0][14], job_main=ast.literal_eval(query[0][15]),
                           job_pref=ast.literal_eval(query[0][16]), job_capa=ast.literal_eval(query[0][17]),
                           job_cert=query[0][18], job_port=query[0][19],status = status,
                           pub_date = pub_date, edi_date = edi_date, comp_query = comp_query,
                           group_query= group_query,posi_query = posi_query, allall = allall,who=who)


@app.route('/push', methods=['POST'])
def push():
    res_val = request.form
    today = re.sub("-", '', str(datetime.today()))
    ymd = today.split(" ")[0]
    ymd = ymd[:4] + "-" + ymd[4:6] + "-" + ymd[6:]
    hms = today.split(" ")[1].split('.')[0][:-3]
    at_datetime = ymd + " @" + hms
    # print("**PUSH", (res_val['author_id']))
    # print("line 648", res_val['jd_id'])
    ### 여기에 나머지값 merge
    g.db.execute('''
        UPDATE feedback
        SET edi_date = "'''+at_datetime+'''", status = "complete"
        WHERE 
            feedback.pub_date = "'''+res_val['pub_date']+'''"''')

        # AND
        #     pub_date = "'''+res_val['pub_date']+'''"''')

    g.db.commit()
    main_cert = [str(i).strip() for i in res_val['자격증'].split("\r\n") if str(i).strip() != '']
    if len(main_cert) == 0:
        main_cert = ['none']
    main_port = [str(i).strip() for i in res_val['포트폴리오'].split("\r\n") if str(i).strip() != '']
    if len(main_port) == 0:
        main_port = ['none']
    main_mino = [str(i).strip() for i in res_val['우대전공'].split("\r\n") if str(i).strip() != '']
    if len(main_mino) == 0:
        main_mino = ['none']
    main_resp = [str(i).strip() for i in res_val['주요업무책임'].split("\r\n") if str(i).strip() != '']
    main_evrm = [str(i).strip() for i in res_val['주요업무환경'].split("\r\n") if str(i).strip() != '']
    if len(main_evrm) == 0:
        main_evrm = ['none']
    main_qual = [str(i).strip() for i in res_val['필수자격'].split("\r\n") if str(i).strip() != '']
    main_pref = [str(i).strip() for i in res_val['선호자격요건'].split("\r\n") if str(i).strip() != '']
    main_capa = [str(i).strip() for i in res_val['필요역량'].split("\r\n") if str(i).strip() != '']
    main_all = [str(i).strip() for i in res_val['필수자격요건'].split("\r\n") if str(i).strip() != '']
    # print(main_all[1:-1])
    final_val = [res_val['일련번호'], res_val['파일명'], res_val['법인명'], res_val['팀명'], res_val['직군'],
        res_val['직렬'], res_val['직무'], res_val['직무소개'], res_val['학위'], res_val['전공'],
        str(main_mino[0]), res_val['최소연차'], res_val['경력연차'], res_val['경력배경'],
        str(main_cert),str(main_port), str(main_resp),str(main_evrm),str(main_qual), str(main_pref),
        str(main_capa), str(main_all[0])]

    g.db.execute('''INSERT INTO JD_features VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(final_val))
    g.db.commit()

    # final1 = query_jd_db('''
    #     SELECT * FROM feedback ''') #WHERE pub_date = "'''+res_val['pub_date']+'''"
    # # ''')
    final2 = query_jd_db('''
        SELECT * FROM JD_features WHERE 파일명 = "'''+res_val['파일명']+'''"
    ''')
    # print("line673", res_val['who'])
    flash('JD를 성공적으로 생성하였습니다.')

    # return redirect(url_for('feedback_timeline'))
    return render_template('to_db.html', val = res_val, final1 = final2)


# @app.route('/feedback_timeline')
# def feedback_timeline():
#     """Shows a users timeline or if no user is logged in it will
#     redirect to the public timeline.  This timeline shows the user's
#     messages as well as all the messages of followed users.
#     """
#     if not g.user:
#         return redirect(url_for('feedback_public'))
#     # print(g.user)
#     count = query_db('''
#                 SELECT COUNT(author_id) FROM feedback
#                 WHERE feedback.author_id = ''' + str(g.user['user_id']) + '''
#             ''')
#     # print("line688", count)
#     return render_template('feedback.html',cnt = count, messages=query_db('''
#         SELECT feedback.*, user.*
#         FROM feedback, user
#         WHERE feedback.author_id = user.user_id
#         AND user.user_id = ?
#         ORDER BY feedback.pub_date desc limit ?''', [session['user_id'], PER_PAGE]))
#

# @app.route('/feedback_public')
# def feedback_public():
#     """Displays the latest messages of all users."""
#     query = query_jd_db('''SELECT * FROM user''')
#     messages = query_db('''
#             SELECT feedback.*, user.*
#             FROM feedback, user
#             WHERE feedback.author_id = user.user_id
#             ORDER BY feedback.pub_date desc limit? ''', [PER_PAGE])
#     return render_template('feedback.html', query = query, messages = messages)


# @app.route('/<username>')
# def feedback_user(username):
#     """Display's a users tweets."""
#     # profile_user = query_db('select * from user where username = ?',
#     #                         [username], one=True)
#     # print("line759",profile_user)
#     messages = query_db('''
#         SELECT feedback.*, user.*
#         FROM feedback, user
#         WHERE user.user_id = feedback.author_id
#         ORDER BY feedback.pub_date desc limit ?''',
#                         [ PER_PAGE])
#     # WHERE user.user_id = feedback.author_id and user.user_id = ?
#     # if profile_user is None:
#     #     abort(404)
#
#     return render_template('feedback.html', messages = messages)
#             # profile_user=profile_user)



################# USER DB #################
def connect_db():
    """Returns a new connection to the database."""
    return sqlite3.connect(app.config['DATABASE'])

def init_db():
    """Creates the database tables."""
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

def init_db_user():
    """Creates the database tables."""
    # user_register_date
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()
    conn = sqlite3.connect('People_Lab.db')
    cur = conn.cursor()
    with open('//Users/jakang/Desktop/Flask/project/src/static/user.csv', 'r') as f:
        reader = csv.reader(f.readlines()[1:])
        # print("reader", reader)
    cur.executemany("""
            INSERT INTO user (user_id, username, email, pw_hash, auth, regi_date) 
            VALUES (?,?,?,?,?,?)""",
                    (row for row in reader))
    conn.commit()
    # conn.close()


def query_db(query, args=(), one=False):
    """Queries the database and returns a list of dictionaries."""
    cur = g.db.execute(query, args)
    rv = [dict((cur.description[idx][0], value)
               for idx, value in enumerate(row)) for row in cur.fetchall()]
    return (rv[0] if rv else None) if one else rv

# def get_user_id(username):
#     """Convenience method to look up the id for a username."""
#     rv = g.db.execute('select user_id from user where username = ?', [username]).fetchone()
#     return rv[0] if rv else None

def format_datetime(timestamp):
    from pytz import timezone
    """Format a timestamp for display."""
    return datetime.now(timezone('Asia/Seoul')).strftime('%Y-%m-%d @ %H:%M')

@app.before_request
def before_request():
    """Make sure we are connected to the database each request and look
    up the current user so that we know he's there.
    """
    g.db = connect_db()
    g.user = None
    if 'user_id' in session:
        g.user = query_db('select * from user where user_id = ?',
                          [session['user_id']], one=True)

@app.teardown_request
def teardown_request(exception):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'db'):
        g.db.close()

################# JD DB #################
def init_db_jd():
    with closing(connect_db()) as db:
        with app.open_resource('jd_schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()
    conn = sqlite3.connect('People_Lab.db')
    cur = conn.cursor()
    with open('/Users/jakang/Desktop/Flask/project/src/static/JD_0519.csv', 'r') as f:
        reader = csv.reader(f.readlines()[1:])  # exclude header line
        # print(reader)
        cur.executemany("""INSERT INTO JD_features VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (row for row in reader))
    conn.commit()
    # conn.close()


def query_jd_db(query):
    cur = g.db.execute(query)
    return cur.fetchall()

 # pct_group_comp = query_jd_db('''
    #         SELECT 법인명, ((count(*) * 100) / (select count(*) from JD_features)) as pct
    #         FROM JD_features GROUP BY 법인명 ORDER BY pct DESC''')


# messages=query_db('''
# #             select message.*, user.* from message, user where
# #             user.user_id = message.author_id and user.user_id = ?
# #             order by message.pub_date desc limit ?''',
# #             [profile_user['user_id'], PER_PAGE]),
# #             profile_user=profile_user)

################# Route-login #################

# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     if g.user:
#         if g.user['auth'] == 'admin':
#             return redirect(url_for('feedback_public'))
#         elif g.user['auth'] == 'user':
#             return redirect(url_for('feedback_timeline'))
#     error = None
#
#     if request.method == 'POST':
#         user = query_db('''select * from user where
#             email = ?''', [request.form['email']], one=True)
#         if user is None:
#             error = 'Invalid email'
#
#         elif user['pw_hash'] != request.form['password']:
#             error = 'Invalid password'
#         else:
#             flash(str(user['username']) + "님께서 로그인 하셨습니다.")
#             session['user_id'] = user['user_id']
#             # print("HERE:", user)
#             # return redirect(url_for('login'))
#             return redirect(url_for('jd_create'))
#     return render_template('login.html', error=error)
#
# @app.route('/login_page', methods=['GET', 'POST'])
# def login_from_page():
#     if g.user:
#         if g.user['auth'] == 'admin':
#             return redirect(url_for('feedback_public'))
#         elif g.user['auth'] == 'user':
#             return redirect(url_for('feedback_timeline'))
#     error = None
#
#     if request.method == 'POST':
#         user = query_db('''select * from user where
#             email = ?''', [request.form['email']], one=True)
#         if user is None:
#             error = 'Invalid email'
#
#         elif user['pw_hash'] != request.form['password']:
#             error = 'Invalid password'
#         else:
#             flash(str(user['username']) + "님께서 로그인 하셨습니다.")
#             session['user_id'] = user['user_id']
#             if user['auth'] == 'admin':
#                 return redirect(url_for('feedback_public'))
#             else:
#                 return redirect(url_for('feedback_timeline'))
#             # return redirect(url_for('jd_create'))
#     return render_template('login.html', error=error)
#
# @app.route('/register_page', methods=['GET', 'POST'])
# def register_page():
#     """Registers the user."""
#     # print("******", g.user)
#     if g.user:
#         if g.user['auth'] == 'admin':
#             return render_template('register.html')
#         else:
#             msg = g.user['username'] + '님은 페이지에 권한이 없습니다.'
#             return render_template('register_page.html', msg = msg)
#             # flash()
#     else:
#         msg = "권한이 필요한 페이지입니다."
#         return render_template('register_page.html', msg = msg)
#
# @app.route('/register_user', methods=['GET', 'POST'])
# def register_user():
#     msg = None
#     today = re.sub("-", '', str(datetime.today()))
#     ymd = today.split(" ")[0]
#     ymd = ymd[:4] + "-" + ymd[4:6] + "-" + ymd[6:]
#     # print("line48", ymd)
#     if request.method == 'POST':
#         if not request.form['new_username']:
#             msg = 'You have to enter a username'
#         elif not request.form['new_email'] or \
#                  '@' not in request.form['new_email']:
#             msg = 'You have to enter a valid email address'
#         elif not request.form['new_password']:
#             msg = 'You have to enter a password'
#         elif request.form['new_password'] != request.form['new_password2']:
#             msg = 'The two passwords do not match'
#         elif get_user_id(request.form['new_username']) is not None:
#             msg = 'The username is already taken'
#         else:
#             g.db.execute('''insert into user (
#                 username, email, pw_hash, auth, regi_date) values (?, ?, ?, ?, ?)''',
#                 [request.form['new_username'], request.form['new_email'],
#                  request.form['new_password'], request.form['new_auth'],
#                  ymd])
#             g.db.commit()
#
#             msg = "[" + str(request.form['new_username']) + '] 님을 등록하였습니다. 이제부터 ' + \
#                   "아이디: " + str(request.form['new_email']) + \
#                   " & 비밀번호: " + str(request.form['new_password']) + " 로 로그인 하실 수 있습니다."
#     else:
#         print("@@@@@@: else")
#     return render_template('register_page.html', msg=msg)

# @app.route('/logout')
# def logout():
#     """Logs the user out."""
#     # flash("로그아웃 합니다.")
#     session.pop('user_id', None)
#     # return redirect(url_for('login'))
#     return render_template("logout.html")


################# Route-timeline #################
#
# @app.route('/timeline')
# def timeline():
#     """Shows a users timeline or if no user is logged in it will
#     redirect to the public timeline.  This timeline shows the user's
#     messages as well as all the messages of followed users.
#     """
#     if not g.user:
#         return redirect(url_for('public_timeline'))
#     return render_template('timeline.html', messages=query_db('''
#         select message.*, user.* from message, user
#         where message.author_id = user.user_id and (
#             user.user_id = ?)
#         order by message.pub_date desc limit ?''',
#         [session['user_id'],  PER_PAGE]))
#
#
# @app.route('/public_timeline')
# def public_timeline():
#     """Displays the latest messages of all users."""
#     return render_template('timeline.html', messages=query_db('''
#         select message.*, user.* from message, user
#         where message.author_id = user.user_id
#         order by message.pub_date desc limit ?''', [PER_PAGE]))
#
#
# @app.route('/<username>')
# def user_timeline(username):
#     """Display's a users tweets."""
#     profile_user = query_db('select * from user where username = ?',
#                             [username], one=True)
#     if profile_user is None:
#         abort(404)
#
#     return render_template('timeline.html', messages=query_db('''
#             select message.*, user.* from message, user where
#             user.user_id = message.author_id and user.user_id = ?
#             order by message.pub_date desc limit ?''',
#             [profile_user['user_id'], PER_PAGE]),
#             profile_user=profile_user)
#
#
# @app.route('/add_message', methods=['POST'])
# def add_message():
#     """Registers a new message for the user."""
#     if 'user_id' not in session:
#         abort(401)
#     if request.form['text']:
#         g.db.execute('''insert into
#             message (author_id, text, pub_date)
#             values (?, ?, ?)''', (session['user_id'],
#                                   request.form['text'],
#                                   int(time.time())))
#         g.db.commit()
#         flash('Your message was recorded')
#     return redirect(url_for('timeline'))


# add some filters to jinja
app.jinja_env.filters['datetimeformat'] = format_datetime


if __name__ == '__main__':
    # init_db()
    # init_db_user()
    # init_db_jd()
    # app.run(host='192.168.200.109', threaded=True)
    # app.run(host='192.168.200.109', threaded=True)
    app.run()

    # app.run(host='192.168.200.150', threaded=True)