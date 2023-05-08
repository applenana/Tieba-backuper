import requests
import time
from fake_useragent import UserAgent
from playwright.sync_api import sync_playwright
from playwright.async_api import async_playwright
import asyncio
import os
import json
from bs4 import BeautifulSoup
import time
import logging
import wget
import threading
import re
import aiohttp

logging.basicConfig(level = logging.INFO,format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

if not os.path.exists('cookies.txt'):
    logger.error('未检测到cookie！需要手动登录！')
    p = sync_playwright().start()
    browser = p.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto('http://www.baidu.com')
    page.locator('id=s-top-username').click(timeout=60000)
    cookie=context.cookies()
    logger.info('cookie获取成功！')
    with open('cookies.txt','w',encoding='utf-8') as f:
        f.write(str(cookie))
    logger.info('cookie写入成功')
    context.close()
    browser.close()

async def run(s,e,cookies,browser,tzurl,title,all):
    global count
    count=count
    global thread
    thread+=1
    await asyncio.sleep(thread)
    context =await browser.new_context()
    await context.add_cookies(cookies)
    newpage=await context.new_page()

    pagenum=s
    def hanle_lzl(tid,pid,s):
        complete=True
        i=1
        f=''
        try:
            while complete:
                result=json.loads(requests.get('https://tieba.baidu.com/mg/o/getFloorData?pn='+str(i)+'&rn=30&tid='+str(tid)+'&pid='+str(pid)).text)
                for count in range(len(result['data']['sub_post_list'])):
                    mpic='<img src="https://gss0.bdstatic.com/6LZ1dD3d1sgCo2Kml5_Y_D3/sys/portrait/item/'+result['data']['sub_post_list'][count]['author']['portrait']+'">'
                    mname=result['data']['sub_post_list'][count]['author']['name_show']
                    mcon=result['data']['sub_post_list'][count]['content']
                    text=''
                    for m in mcon:
                        if m['type'] in [0,4]:
                            text+=m['text']
                        elif m['type'] in [1,18]:
                            text+='<a href="'+m['link']+'">'+m['text']+'</a>'
                        elif m['type']==2:
                            text+='<img src="'+m['src']+'">'
                        else:
                            print(m)
                            text+=m
                    mcon=text
                    mtime=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(result['data']['sub_post_list'][count]['time'])))
                    f=f+'<div class:"mall"><div class="mpic">'+str(mpic)+'</div><div class="mcon">'+mname+':'+str(mcon)+'</div><div class="mtime">'+mtime+'</div></div>'+'\n'
                
                complete=result['data']['page']['current_page']!=result['data']['page']['total_page']
                i+=1
                #print('执行任务'+str(pid)+'中……i——'+str(i))
        except Exception as err:
            print(pid,str(err))
            f='---for'+pid+'---'
        global allhtml
        #print(allhtml[s])
        allhtml[s]=allhtml[s].replace('---for'+pid+'---',f)
        #print(allhtml[s])
        #print('执行完成！'+pid)

    while pagenum <= e:
        page=newpage
        try:os.mkdir(title)
        except:pass
        try:os.mkdir('./'+title+'/image')
        except:pass
        try:os.mkdir('./'+title+'/video')
        except:pass
        async def pic_intersept(response):
            if '.baidu.com/forum' in response.url:
                try:name=response.url.split('sign=')[1].split('/')[0]
                except:return ''
                with open('./'+title+'/image/'+name+'.jpg','wb') as f:
                    f.write(await response.body())
                #print(response.url)
            if 'tb-video.bdstatic.com' in response.url:
                try:name=response.url.split('transcode-cae/')[1].split('?')[0]
                except:return ''
                def dovideo(response):
                    wget.download(response.url,out='./'+title+'/video/'+name)
                nt=threading.Thread(target=dovideo,args=(response,))
                nt.start()
                nt.join()
            
        page.on('response',pic_intersept)
        #拦截图片请求，直接获取二进制数据流（这样可以极大的避免后期批量爬取图片导致的ip封禁）

        excluded_resource_types = ["font","stylesheet","script"]
        async def block_aggressively(route):
            if (route.request.resource_type in excluded_resource_types):
                await route.abort()
            elif 'baidu' in str(route.request.url) or 'bdstatic' in str(route.request.url):
                await route.continue_()
            else:
                await route.abort()
        await page.route("**/*", block_aggressively)
        #拦截无用资源的加载

        while True:
            try:await page.goto(tzurl+'?pn='+str(pagenum))
            except Exception as err:
                logger.error('加载失败……可能是网络问题……冷却一分钟')
                print(str(err))
                await asyncio.sleep(60)
                await page.goto(tzurl+'?pn='+str(pagenum))
            else:break

        #设置全页面大小
        width = await page.evaluate("document.documentElement.scrollWidth;")
        height = await page.evaluate("document.documentElement.scrollHeight;")#这两个要注意：不能加return（selenium里面需要加）
        await page.set_viewport_size({"width": width, "height": height})

        logger.info('爬取'+str(pagenum)+'页ing……')

        allhtml[s]=''#接下来html拼接的起源！
        if pagenum==1:
            allhtml[s]+='''
            <head><link rel="stylesheet" type="text/css" href="../tz.css"><meta htt=utf-8" />ontent-Type" content="text/html; charset=utf-8" /></head>
            '''
            allhtml[s]+="<title>"+title+"</title>"+"\n"
            allhtml[s]+="<h1>"+title+"</h1><hr>"+'\n'
        #获取标题并拼接

        pidlist=[]#准备pid的列表以便一会获取

        #获取主要楼层的信息+pid
        floor=0
        for div in BeautifulSoup(await page.content(),'lxml').find_all('div',attrs={'class':'l_post l_post_bright j_l_post clearfix'}):
            floor+=1
            a=div.find('ul',attrs={'class':'p_author'}).find('li',attrs={'class':'d_name'}).find('a',{'alog-group':'p_author'}).get_text()#获取此楼的发楼者
            a_face=div.find('a',attrs={'class':'p_author_face'})#获取此楼的发楼者的头像
            try:a_face.img
            except:a_face=div.find('span',attrs={'class':'p_author_face p_author_face_ip'})
            try:
                if 'data-tb-lazyload' in a_face.img.attrs:
                    a_face.img['src'] = a_face.img['data-tb-lazyload']
            except Exception as err:
                print(a_face)
                print(div)
            maincon=div.find('div',attrs={'class':'d_post_content j_d_post_content'})#获取此楼的主要内容
            #处理图片
            for img in maincon.find_all('img',{'class':'BDE_Image'}):
                url=img.attrs['src']
                try:
                    name=url.split('sign=')[1].split('/')[0]
                    img['src']='./image/'+name+'.jpg'
                except Exception as err:
                    print(url)
                    print(str(err))
                
            #处理视频
            for video in maincon.find_all('video'):
                url=video.attrs['src']
                name=url.split('transcode-cae/')[1].split('?')[0]
                video['src']='./video/'+name   
            meg_location=div.find('div',attrs={'class':'post-tail-wrap'}).find('span').get_text()#获取此楼的发布地点（ip属地)
            try:#尝试以正常方式获取（也就是显示来自xxx客户端）
                meg_floor=div.find('div',attrs={'class':'post-tail-wrap'}).find_all('span',attrs={'class':'tail-info'})[1].get_text()#获取此楼的楼层
                meg_time=div.find('div',attrs={'class':'post-tail-wrap'}).find_all('span',attrs={'class':'tail-info'})[2].get_text()#获取此楼的发布时间
            except:#如果出错（一般就是少了来自xxx客户端，tail-info向前推1即可）
                meg_floor=div.find('div',attrs={'class':'post-tail-wrap'}).find('span',attrs={'class':'tail-info'}).get_text()#获取此楼的楼层
                meg_time=div.find('div',attrs={'class':'post-tail-wrap'}).find_all('span',attrs={'class':'tail-info'})[1].get_text()#获取此楼的发布时间
            pid=div.attrs['data-pid']
            pidlist.append(pid)#本楼的pid
            tid=tzurl.split('/p/')[1]

            async with aiohttp.ClientSession() as session:
                async with session.get('https://tieba.baidu.com/mg/o/getFloorData?pn=1&rn=30&tid='+str(tid)+'&pid='+str(pid)) as response:
                    try:
                        lzlgetresult =json.loads(await response.text())
                        lzlgetresult= lzlgetresult['data']['sub_post_list']
                    except Exception as err:
                        lzlgetresult='NoneType'
                        print(await response.text())
                        print(str(err))

            #print(lzlgetresult)
            if 'NoneType' in str(type(lzlgetresult)) or (int(floor)==1 and int(pagenum)==1):
                #logger.info('此楼无lzl')
                allhtml[s]=allhtml[s]+'\n'+'<table><tr><td class="first-p">'+str(a_face)+'<h4>'+a+'</h4>'+'\n'+'</td><td class="second-p">'+str(maincon)+'\n'+'</td></tr>'+'<tr><td></td><td><div class="msg">'+str(meg_floor)+'|'+str(meg_location)+'|'+str(meg_time)+'</div></td></tr>'+'</table><hr>'
            else:
                #新建一个线程获取楼中楼
                #logger.info('开启新线程爬取楼中楼')
                allhtml[s]=allhtml[s]+'\n'+'<table><tr><td class="first-p">'+str(a_face)+'<h4>'+a+'</h4>'+'\n'+'</td><td class="second-p">'+str(maincon)+'\n'+'</td></tr>'+'<tr><td></td><td><div class="msg">'+str(meg_floor)+'|'+str(meg_location)+'|'+str(meg_time)+'</div></td></tr>'+'<tr><td></td><td class="review">'+'---for'+str(pid)+'---'+"\n"+'</td>'+'</table><hr>'
                #print(str(pagenum),str(floor),str(pid))
                nt=threading.Thread(target=hanle_lzl,args=(str(tid),str(pid),s))
                nt.start()

        while '---for' in allhtml[s]:
            await asyncio.sleep(1)
            '''print(re.findall('---for(.*?)---',allhtml[s]))
            print(len(threading.enumerate()))
            print('等待楼中楼爬取完毕')'''
            logger.info('等待剩余的'+str(len(re.findall('---for(.*?)---',allhtml[s])))+'楼爬取完毕')
        f=open(title+'/'+str(title)+str(pagenum)+'.html','w',encoding='utf-8')
        f.write(allhtml[s].encode('utf-8', 'replace').decode())
        f.close()
        count+=1
        logger.info(str(count)+'/'+str(all)+'|'+str((round((count/all),2))*100)+'%')
        newpage=await context.new_page()
        await page.close()
        await context.clear_cookies()
        await context.add_cookies(cookies)
        pagenum+=1
    await context.close()

def tidyup(title,page):
    text=''
    for i in range(page):
        with open('./'+title+'/'+title+str(i+1)+'.html','r',encoding='utf-8') as f:
            text+=f.read()
    with open('./'+title+'/'+'index.html','w',encoding='utf-8') as f:
        f.write(text)
    

async def main():
    logger.info('测试登陆状态中……')
    p=await async_playwright().start()
    browser = await p.chromium.launch(headless=True)
    context =await  browser.new_context()
    with open('cookies.txt','r',encoding='utf-8') as f:
        cookies=eval(f.read())
    await context.add_cookies(cookies)
    page = await context.new_page()

    #获取页码&登录状态
    tzurl='https://tieba.baidu.com/p/1012328833'
    await page.goto(tzurl)
    if await page.locator('id=my_tieba_mod').is_visible(timeout=1000):
        logger.info('登陆成功！')
    else:
        logger.critical('登录出错！有可能是cookie文件损坏！请尝试删除cookie重新登陆！')
        quit()
    pagenum=BeautifulSoup(await page.content(),'lxml').find('li',{'class':'l_reply_num'}).find_all('span')[1].get_text()
    logger.info('该帖子总有'+str(pagenum)+'页')
    soup=BeautifulSoup(str(await page.content()),'lxml')
    title=soup.find('div',id='j_core_title_wrap').find('h3').get_text().replace('回复：','').replace(' ','')
    logger.info('帖子标题:'+title)
    await context.close()

    global count
    count=0   
    global thread
    thread=0
    global allhtml
    allhtml={}
    p=int(pagenum)
    tn=10#线程数
    threadpools=[]
    if p<tn:
        await run(title=title,tzurl=tzurl,s=1,e=p,all=p,browser=browser,cookies=cookies)
    else:
        s=1
        e=s+p//tn-1
        for i in range(tn):
            threadpools.append(run(title=title,tzurl=tzurl,s=s,e=e,all=p,browser=browser,cookies=cookies))
            s=e+1
            e=s+p//tn-1
        if p%tn!=0:
            e=s+p%tn-1
            threadpools.append(run(title=title,tzurl=tzurl,s=s,e=e,all=p,browser=browser,cookies=cookies))
        await asyncio.gather(*threadpools)
    await browser.close()
    tidyup(title=title,page=pagenum)
#asyncio.run(main())
