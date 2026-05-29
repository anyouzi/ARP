# fix tree
import sys
sys.stdout.reconfigure(encoding="utf-8")
c=open("openar_editor.py",encoding="utf-8").read()
start=c.find("def _refresh_tree")
end=c.find("def _expand_all",start)
old=c[start:end]
print("found",start,end)
print("OLD:",repr(old[:100]))
