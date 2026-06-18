# -*- coding: utf-8 -*-
"""
Created on Thu Jun  5 15:07:56 2025

@author: Admin
"""

import matplotlib.pyplot as plt
from wordcloud import WordCloud
import numpy as np
from PIL import Image
import pandas as pd

# 就下面代码，即可获取满足类型要求的参数
bg=np.array(Image.open("big.png"))
mask=bg

# 词云参数设置
wc = WordCloud(
                width=1200,  # 词云图宽
                height=800,  # 词云图高
                mask = mask, # 词云蒙版图
                scale=2,
                max_words = 25,
                random_state=50,
                max_font_size=200,
                min_font_size=10,
                background_color='white', # 词云图背景颜色，默认为黑色
                colormap='Set2',
                font_path='字魂萌趣软糖体.ttf',  # 词云图 字体（中文需要设定为本机有的中文字体）
     ) 
# 词频信息数据，用字典形式传给 generate_from_frequencies

df = pd.read_clipboard()
result_dict = df.set_index('关键词')['权重'].to_dict()  #转字典
frequencies = result_dict
wc.generate_from_frequencies(frequencies) # 根据词频信息数据做词云图

# matplotlib用于显示 词云图
plt.imshow(wc)
plt.axis("off")
plt.savefig('词云.png', dpi=300)
plt.show()


