import socket
 
host = 'localhost'
# host = '192.168.201.201'
port = 7777
client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
msg = "state"
client.sendto(msg.encode('utf-8'), (host, port))
d = client.recvfrom(1024)
reply = d[0]
addr = d[1]
print ('Server reply: ' + reply.decode('utf-8'))
msg = "charge"
client.sendto(msg.encode('utf-8'), (host, port))
d = client.recvfrom(1024)
reply = d[0]
addr = d[1]
print ('Server reply: ' + reply.decode('utf-8'))
client.close()