import os, json
here = os.path.dirname(os.path.abspath(__file__))
p = here + os.sep + 'final.json'
print('exists:', os.path.exists(p), p)
