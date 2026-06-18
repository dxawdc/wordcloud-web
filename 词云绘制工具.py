# -*- coding: utf-8 -*-
"""
Created on Fri May 14 10:55:48 2021

@author: 可以叫我才哥
"""
import os   
import stylecloud
from PIL import Image
import jieba
import jieba.analyse
import pandas as pd
import numpy as np
from wordcloud import STOPWORDS
import PySimpleGUI as sg

def ciYun(data,addWords,stopWords,bg,font_path):
    print('正在作图...')
    comment_data = data
    
    for addWord in addWords:
        jieba.add_word(addWord)

    comment_after_split = jieba.cut(str(comment_data), cut_all=False)
    words = ' '.join(comment_after_split)
    
    # 词云停用词 
    stopwords = STOPWORDS.copy()
    for stopWord in stopWords:
        stopwords.add(stopWord)

    # 就下面代码，即可获取满足类型要求的参数
    stylecloud.gen_stylecloud(
                              text=words,
                              size = 800,
                              palette='tableau.BlueRed_6', # 设置配色方案
                              icon_name='fas fa-cloud',# thumbs-up
                              custom_stopwords = stopwords,
                              bg = bg, 
                              font_path=font_path,  # 词云图 字体（中文需要设定为本机有的中文字体）
                             )
    
    print('词云已生成~')
    pic_path = os.getcwd()
    print(f'词云图文件已保存在 {pic_path}')

# 词云图预览
def image_view(pic_path): 
    layout = [[sg.Image(pic_path, key="image",background_color='white',size=(818, 818))]
              ]
    window = sg.Window("词云图预览，作者@微信公众号：可以叫我才哥",layout)
    while True:
        event, values = window.read()
        if event in (None,'关闭'):
            break
    window.close()

# 字体字典
fonts_dict ={
    '仿宋':'simfang.ttf',
    '微软雅黑':'msyh.ttc',
    '宋体':'simsun.ttc',    
    '隶书':'SIMLI.TTF',
    'Times New Roman':'times.ttf', 
    '萌趣':'字魂萌趣软糖体.ttf'
    }

# 主题设置
sg.theme('SystemDefaultForReal')

# 布局设置
layout = [[sg.Text('选择待绘制文件:',font=("微软雅黑", 12)),sg.InputText('可以不选', key='file',size=(60,1),font=("微软雅黑", 10),enable_events=True) ,sg.FileBrowse('打开',file_types=(("Text Files", "*.txt"),),size=(10,1),font=("微软雅黑", 11))],
          [sg.Text('选择停用词文件:',font=("微软雅黑", 12)),sg.InputText('也可以不选',key='stop_file',size=(60,1),font=("微软雅黑", 10),enable_events=True) ,sg.FileBrowse('打开',file_types=(("Text Files", "*.txt"),),size=(10,1),font=("微软雅黑", 11))],
          [sg.Text('输入待绘制的文本(可以直接复制文本到本地，不需求选择文本文件):',justification='center')],
          [sg.Multiline(size=(92, 8),font=("微软雅黑", 10),key='text')], 
          [sg.Text('自\n定\n义\n词',font=("微软雅黑", 12)),sg.Multiline(tooltip='词与词之间用“/”分开',size=(40, 5),font=("微软雅黑", 10),key='add_words'),
           sg.Text('停\n用\n词',font=("微软雅黑", 12)),sg.Multiline(tooltip='词与词之间用“/”分开',size=(40, 5),font=("微软雅黑", 10),key='add_stopwords')],
          [sg.Text('词云字体:',font=("微软雅黑", 12)),sg.Combo(['微软雅黑','宋体','仿宋','隶书','Times New Roman','萌趣'],font=("微软雅黑", 10), default_value='微软雅黑',size=(15, 5),key='fonts'),
           sg.Text('背景图:',font=("微软雅黑", 12)),sg.InputText('也可以不选，选则只能选取.png图片',key='bg_file',size=(40,1),font=("微软雅黑", 10)) ,sg.FileBrowse('打开',file_types=(("Text Files", "*.png"),),size=(10,1),font=("微软雅黑", 11))],
          [sg.Text('程序操作记录:',justification='center')],
          [sg.Output(size=(92, 8),font=("微软雅黑", 10))],  
          [sg.Text('操作说明:',font=("微软雅黑", 12))],
          [sg.Text('①如果是从文本文件进行绘制，则需要先选择待绘制文件\n②如果是一段文本需要进行绘制，将文本复制到待绘制文本框',font=("微软雅黑", 10)),
           sg.Text('',font=("微软雅黑", 12),size=(10, 1)),
           sg.Button('开始绘制',font=("微软雅黑", 12),button_color ='Orange'),
           sg.Button('关闭程序',font=("微软雅黑", 12),button_color ='red')],
          ]      

# 创建窗口
window = sg.Window('词云制作工具，作者@发行中心-综合支持', layout,font=("微软雅黑", 12),default_element_size=(50,1))    

# 事件循环
while True:
    event, values = window.read()
    if event in (None, '关闭程序'):
        break

    if event == '开始绘制':
        fileName = values['file']              # 待绘制词云文本文件
        stop_fileName = values['stop_file']    # 停用词文本文件
        text = values['text']                  # 待绘制词云文本（自己复制粘贴的内容）
        add_words = values['add_words']        # 自定义关键词 
        add_stopwords = values['add_stopwords']# 补充的停用词
        bg_fileName = values['bg_file']        # 词云背景图文件
        fonts = values['fonts']                # 词云字体
        font_path = fonts_dict[fonts]
        
        if os.path.exists(fileName):
            try:
                with open(fileName, "r",) as f:    #打开文件
                    data = f.read()   #读取文件
            except :
                with open(fileName, "r", encoding='utf-8') as f:    #打开文件
                    data = f.read()   #读取文件
        else:
            data = ''
            
        if os.path.exists(stop_fileName):
            stoptxt = pd.read_table(stop_fileName,encoding='utf-8',header=None)
            stoptxt.drop_duplicates(inplace=True)
            stopWords = stoptxt[0].to_list()
        else:
            stopWords = []
            
        if os.path.exists(bg_fileName):
            bg=np.array(Image.open(bg_fileName))
        else:
            bg = ''
        
        # 组合待绘制文本、停用词和自定义关键词
        data = data + text
        stopwords = add_stopwords.rstrip().split('/')
        stopWords.extend(stopwords)
        addWords = add_words.rstrip().split('/')
        
        if len(data)>1:
            ciYun(data,addWords,stopWords,bg,font_path)
            pic_path = os.getcwd()+"\\stylecloud.png"
            image_view(pic_path)
        else:
            print('待绘制词云文本未选择')

window.close()

