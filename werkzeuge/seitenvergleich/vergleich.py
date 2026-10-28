# Vergleich zweier Stände: python3 vergleich.py vorher.json nachher.json (Ausgaben von dump.mjs)
import json,sys
a=json.load(open(sys.argv[1]));b=json.load(open(sys.argv[2]))
d=[k for k in a if a[k]!=b.get(k)]
print(len(a),"Routen,",len(d),"abweichend")
for k in d[:8]:
    x,y=a[k],b.get(k,"")
    i=next((i for i in range(min(len(x),len(y))) if x[i]!=y[i]),min(len(x),len(y)))
    print(k,"\n  vorher:",x[max(0,i-150):i+150],"\n  nachher:",y[max(0,i-150):i+150])
