import urllib2

# download the pgf backend from the matplotlib repository on github

url = "https://raw.github.com/matplotlib/matplotlib/master/lib/matplotlib/backends/backend_pgf.py"
response = urllib2.urlopen(url)

with open("backend_pgf.py", "w") as fh:
    fh.write(response.read())