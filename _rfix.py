# fix
import sys
sys.stdout.reconfigure(encoding="utf-8")
c=open("openar_editor.py",encoding="utf-8").read()
s=c.find("def _refresh_tree")
e=c.find("def _expand_all",s)
print("Section:",s,e)
mid=c[s:e]
print("MID:",repr(mid[:80]),"...")
# find the inner loop start
loop_start=mid.find("for b_idx, block in enumerate(task.get")
loop_end=mid.find("self._expand_all")
print("Loop:",loop_start,loop_end)
