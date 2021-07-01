#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Oct 12 15:54:04 2020

@author: descentis
"""

import numpy as np
import matplotlib.pyplot as plt
 
# Make a fake dataset
height = [46, 93.25, 93.60, 95.02, 95.38]
bars = (r'$k = 2$', r'$k = \sqrt{n\left(\dfrac{m-d}{m+d}\right)}$', r'$C = n^2$', r'$k = 1000$', r'$k = n-1$')
y_pos = np.arange(len(bars))

plt.bar(y_pos, height, color=(0.1, 0.1, 0.1, 0.1),  edgecolor='blue')

label = ['93.25%', '93.60%', '95.02%', '95.38%']
plt.text(x=0-0.2, y=46 - 6, s = '46%', size=12)
plt.text(x=1-0.35, y=93.25 - 6, s = '93.25%', size=12)
plt.text(x=2-0.35, y=93.60 - 6, s = '93.60%', size=12)
plt.text(x=3-0.35, y=95.02 - 6, s = '95.02%', size=12)
plt.text(x=4-0.35, y=95.38 - 6, s = '95.38%', size=12)


plt.xticks(y_pos, bars, fontsize=8)
plt.savefig('overall_compression.png', dpi=800)
plt.show()