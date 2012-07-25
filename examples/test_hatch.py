# -*- coding: utf-8 -*-
import matplotlib as mpl
import sys

# lookup and use the backend_pgf module in the parent folder
sys.path.append("..")
mpl.use('module://backend_pgf')

###############################################################################

import matplotlib.pyplot as plt

plt.figure(figsize=[5, 2.7])
bars1 = plt.bar(range(1,5), range(1,5), color='gray', ecolor='black')
bars2 = plt.bar(range(1, 5), [6] * 4, bottom=range(1,5), color='lightgray', ecolor='black')
plt.gca().set_xticks([1.5,2.5,3.5,4.5])

patterns = ('.', '+', 'x', '\\', '*', 'o', 'O', '-')
for bar, pattern in zip(bars1+bars2, patterns):
     bar.set_hatch(pattern)

plt.xticks([], [])
plt.yticks([], [])
plt.tight_layout(pad=.5)
plt.savefig("test_hatch.pdf")
