import os
import sys
import shutil

files = []

for dirpath, dirnames, filenames in os.walk(".", True):
    if dirpath.find(".svn")>=0: continue
    for elem in dirnames:
        if elem.find(".svn") >= 0:
            dirnames.pop(dirnames.index(elem))
    for filename in filenames:
        if filename.endswith(".pyc") or filename.endswith("~"):
            files.append(os.path.join(dirpath, filename))

for file in files:
    if '--really' in sys.argv:
        print "Deleting", file
        os.unlink(file)
    else:
        print file

if '--really' in sys.argv:
    try:
        shutil.rmtree('build')
    except:
        pass
    try:
        shutil.rmtree('dist')
    except:
        pass
    try:
        shutil.rmtree('django_platnosci.egg-info')
    except:
        pass
