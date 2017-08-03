from dns.resolver import Resolver
import time

f = time.time()
r = Resolver()
answer = r.query("iqiyi.com")
for _ in answer:
    print _.address
e = time.time()

print e-f
