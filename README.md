# Tieba-backuper
基于playwright实现防ip封禁，使用百度mobileweb端api快速爬取楼中楼，支持伪多线程的高效备份器
## 依赖安装
①需要playwright,requests,bs4,lxml,wget库  
使用pip install 库名 来安装他们  
②playwright的初始化  
首次使用playwright需要安装浏览器核心，使用命令python -m playwright install来安装所有核心  
## 注意事项
尽管playwright可以防止你的ip被封禁，可是这个防封禁只是体现在不影响正常爬取上  
如果你在短时间内大量爬取，会影响你在本地的使用（使用百度产品需要验证码等等）  
而且会造成暂时无解的playwright不稳定  
⚠所以还是建议大家设置好备份计划，不要同时大量备份  
## ToDo
①咕咕咕  
②咕咕咕咕咕 
