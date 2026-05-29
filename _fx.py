import sys,re  
sys.stdout.reconfigure(encoding='utf-8')  
c=open('openar_editor.py',encoding='utf-8').read() 
old='def _refresh_tree'  
s=c.find(old)  
e=c.find('def _expand_all',s)  
body=c[s:e]  
print('start',s,'end',e) 
new_body = '''            for lg_idx, lg in enumerate(task.get("loop_groups", [])):  
                cnt = lg.get("loop_count", 1)  
                st = "" if lg.get("stop_condition_type", 0) == 0 else "STOP"  
                label = f"\\U0001f501 {lg['loop_name']} (x{cnt} {st})" if st else f"\\U0001f501 {lg['loop_name']} (x{cnt})"  
                lg_id = self.tree.insert(t_id, tk.END, text=label, values=("",))  
                for b_idx, block in enumerate(lg.get("blocks", [])):  
                    b_id = self.tree.insert(lg_id, tk.END, text=f"\\U0001f504 {block['block_name']}", values=("",))  
                    for c_idx, code in enumerate(block.get("codes", [])):  
                        info = self._summary(code)  
                        self.tree.insert(b_id, tk.END, text=f"\\u25b8 \\u6307\\u4ee4{c_idx+1}", values=(info,))  
        self._expand_all()  
        tc = sum(len(b.get('codes',[])) for t in self.data.get('tasks',[]) for lg in t.get('loop_groups',[]) for b in lg.get('blocks',[]))  
        nc = sum(1 for t in self.data.get('tasks',[]) for lg in t.get('loop_groups',[]))  
        nb = sum(len(lg.get('blocks',[])) for t in self.data.get('tasks',[]) for lg in t.get('loop_groups',[]))  
        self.status.config(text=f"\\u4efb\\u52a1:{len(self.data.get('tasks',[]))} | \\u5faa\\u73af:{nc} | Block:{nb} | \\u6307\\u4ee4:{tc}")  
''' 
