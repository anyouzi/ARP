c=open('openar_editor.py',encoding='utf-8').read()  
s=c.find('def _refresh_tree')  
e=c.find('def _expand_all',s)  
n=open('_new_tree.txt',encoding='utf-8').read()  
c2=c[:s]+n+c[e:]  
open('openar_editor.py','w',encoding='utf-8').write(c2)  
print('OK',len(c),len(c2)) 
