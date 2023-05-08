from playwright.sync_api import sync_playwright
from playwright.async_api import async_playwright
import asyncio
import os
from bs4 import BeautifulSoup
import time
import datetime
import logging
import wget
import threading

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

        excluded_resource_types = ["font","stylesheet"]
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

        #设置全页面大小（为了放回一会点击尽量不出错）（省去了滚动的过程）
        width = await page.evaluate("document.documentElement.scrollWidth;")
        height = await page.evaluate("document.documentElement.scrollHeight;")#这两个要注意：不能加return（selenium里面需要加）
        await page.set_viewport_size({"width": width, "height": height})
        async def checklogin():
            if await page.locator('id=my_tieba_mod').is_visible(timeout=1000):
                #logger.info('登陆成功！')
                pass
            else:
                logger.critical('登录出错！有可能是百度拦截！查看'+str(datetime.datetime.now().strftime("%H-%M-%S"))+'获取详情,尝试清除cookie重新尝试，冷却一秒')
                await page.screenshot(path='./error'+str(datetime.datetime.now().strftime("%H-%M-%S"))+'.jpg',full_page=True)
                await asyncio.sleep(1)
                newpage=await context.new_page()
                await page.close()
                await context.clear_cookies()
                await context.add_cookies(cookies)
                page=newpage
                await page.goto(tzurl+'?pn='+str(pagenum))
                checklogin()

        logger.info('爬取'+str(pagenum)+'页ing……')

        while True:#等待加载完成
            allwait=await page.locator("//img[@class='loading_reply']").all()
            await page.wait_for_timeout(100)
            if allwait == []:
                break
            else:
                #logger.info('等待加载完成中……仍有'+str(len(allwait))+'个区块未加载完成')
                pass
        #logger.info('加载完成开始点击')

        width = await page.evaluate("document.documentElement.scrollWidth;")
        height = await page.evaluate("document.documentElement.scrollHeight;")#这两个要注意：不能加return（selenium里面需要加）
        await page.set_viewport_size({"width": width, "height": height})

        lzl=await page.locator("//a[@class='j_lzl_m']").all()#获取全部“展开楼中楼”按钮的位置
        #logger.info('此页总有'+str(len(lzl))+'个楼中楼需展开')
        for i in lzl:
            while True:
                if await i.is_visible():
                    try:await i.click(force=True)
                    except Exception as e:logger.error('点击出错……重试中'+str(e))
                    else:break
                else:
                    await page.wait_for_timeout(100)
        #logger.info('展开完成！开始爬取所有数据')

        html=''#接下来html拼接的起源！
        if pagenum==1:
            html+='''
            <head><link rel="stylesheet" type="text/css" href="../tz.css"></head>
            '''
            html+="<title>"+title+"</title>"+"\n"
            html+="<h1>"+title+"</h1><hr>"+'\n'
        #获取标题并拼接
        floor=0
        #进入每一个div块开始爬取
        try:
            for div in BeautifulSoup(await page.content(),'lxml').find_all('div',attrs={'class':'l_post l_post_bright j_l_post clearfix'}):
                floor+=1
                #logger.info('爬取'+str(floor)+'楼……')
                a=div.find('ul',attrs={'class':'p_author'}).find('li',attrs={'class':'d_name'}).find('a',{'alog-group':'p_author'}).get_text()#获取此楼的发楼者
                a_face=div.find('a',attrs={'class':'p_author_face'})#获取此楼的发楼者的头像
                maincon=div.find('div',attrs={'class':'d_post_content j_d_post_content'})#获取此楼的主要内容
                #处理图片
                for img in maincon.find_all('img',{'class':'BDE_Image'}):
                    url=img.attrs['src']
                    name=url.split('sign=')[1].split('/')[0]
                    img['src']='./image/'+name+'.jpg'
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
                c=div.find('div',attrs={'class':'core_reply j_lzl_wrapper'})#缩小搜索范围给↓用的
                d=c.find('ul',attrs={'class':'j_lzl_m_w'}).find_all('li')#获取此楼下评论li块
                #logger.info(str(floor)+'楼基本信息获取完成')
                f=''
                #logger.info('开始爬取楼中楼')
                lzlc=0#楼中楼count
                for m in d:
                    if '我也说一句' not in m.get_text():
                        lzlc+=1
                        #logger.info('爬取楼中楼'+str(lzlc))
                        mpic=m.find('a',attrs={'class':'j_user_card lzl_p_p'})#此楼中楼的作者头像
                        mname=eval(m.attrs['data-field'])['showname']#此楼中楼的作者名
                        mcon=m.find('span',attrs={'class':'lzl_content_main'})#此楼中楼的内容
                        mtime=m.find('span',attrs={'class':'lzl_time'}).get_text()#此楼中楼的发布时间
                        f=f+'<div class:"mall"><div class="mpic">'+str(mpic)+'</div><div class="mcon">'+mname+':'+str(mcon)+'</div><div class="mtime">'+mtime+'</div></div>'+'\n' 
                lzlpage=2
                while True:
                    nextone=page.locator("//*[contains(@data-pid,'"+div.attrs['data-pid']+"')]").locator('text=下一页')
                    if await nextone.is_visible():
                        while True:
                            try:await nextone.click(force=True)
                            except Exception as e:logger.error('点击出错，重试中……'+str(e))
                            else:break                           
                    else:break
                    #logger.info('楼中楼第'+str(lzlpage)+'页')
                    lzlpage+=1
                    await page.wait_for_timeout(250)
                    sp=BeautifulSoup(await page.locator("//*[contains(@data-pid,'"+div.attrs['data-pid']+"')]").inner_html(),'lxml')
                    for m in sp.find('ul',attrs={'class':'j_lzl_m_w'}).find_all('li'):
                        
                        if '我也说一句' not in m.get_text():
                            lzlc+=1
                            #logger.info('爬取楼中楼'+str(lzlc))
                            mpic=m.find('a',attrs={'class':'j_user_card lzl_p_p'})#此楼中楼的作者头像
                            mname=eval(m.attrs['data-field'].replace('null','"-n-u-l-l-"'))['showname']#此楼中楼的作者名
                            mcon=m.find('span',attrs={'class':'lzl_content_main'})#此楼中楼的内容
                            mtime=m.find('span',attrs={'class':'lzl_time'}).get_text()#此楼中楼的发布时间
                            f=f+'<div class:"mall"><div class="mpic">'+str(mpic)+'</div><div class="mcon">'+mname+':'+str(mcon)+'</div><div class="mtime">'+mtime+'</div></div>'+'\n'
                if f=='':
                    html=html+'\n'+'<table><tr><td class="first-p">'+str(a_face)+'<h4>'+a+'</h4>'+'\n'+'</td><td class="second-p">'+str(maincon)+'\n'+'</td></tr>'+'<tr><td></td><td><div class="msg">'+str(meg_floor)+'|'+str(meg_location)+'|'+str(meg_time)+'</div></td></tr>'+'</table><hr>'
                else:
                    html=html+'\n'+'<table><tr><td class="first-p">'+str(a_face)+'<h4>'+a+'</h4>'+'\n'+'</td><td class="second-p">'+str(maincon)+'\n'+'</td></tr>'+'<tr><td></td><td><div class="msg">'+str(meg_floor)+'|'+str(meg_location)+'|'+str(meg_time)+'</div></td></tr>'+'<tr><td></td><td class="review">'+str(f)+"\n"+'</td>'+'</table><hr>'
        except Exception as ep:#注意不能是e
            logger.critical('出错！有可能是百度拦截！查看error'+str(datetime.datetime.now().strftime("%H-%M-%S"))+'获取详情,尝试清除cookie重新尝试，冷却一秒')
            print(ep)
            await page.screenshot(path='./error'+str(datetime.datetime.now().strftime("%H-%M-%S")+'.jpg'),full_page=True)
            await asyncio.sleep(1)
            newpage=await context.new_page()
            await page.close()
            await context.clear_cookies()
            await context.add_cookies(cookies)
            page=newpage
            continue  
        
        if html =='':
            logger.fatal('喵的！你这是空的！')
            await page.screenshot(path='error'+str(datetime.datetime.now().strftime("%H-%M-%S"))+'.jpg',full_page=True)
            await asyncio.sleep(1)
            newpage=await context.new_page()
            await page.close()
            await context.clear_cookies()
            await context.add_cookies(cookies)
            page=newpage            
            continue
        f=open(title+'/'+str(title)+str(pagenum)+'.html','w',encoding='utf-8')
        f.write(html.encode('utf-8', 'replace').decode())
        f.close()
        count+=1
        logger.info(str(count)+'/'+str(all)+'|'+str((round((count/all),2))*100)+'%')
        newpage=await context.new_page()
        await page.close()
        await context.clear_cookies()
        await context.add_cookies(cookies)
        pagenum+=1
    await context.close()

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
    tzurl='https://tieba.baidu.com/p/3274444059'
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
    p=int(pagenum)
    tn=2#线程数
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
asyncio.run(main())
