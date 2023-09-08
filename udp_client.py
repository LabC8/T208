import socket
import argparse
from ipaddress import ip_address

def send_request (host: str, msg: str):
    port = 7777
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client.sendto(msg.encode('utf-8'), (host, port))
    reply, (r_ip, r_port) = client.recvfrom(1024)
    print ('Server [' + r_ip + '] replied: ' + reply.decode('utf-8'))
    client.close()

def validate_ip(ipaddr):
    try:
        ip_address(ipaddr)
        return ipaddr
    except ValueError:
        print ('IP validation failed, localhost will be used')
        return 'localhost'

parser = argparse.ArgumentParser(description='Asking T208 server about UPS state', epilog = '\n Without any arguments program asks localhost about it state:')
# parser.add_argument('-r', '--rqst', nargs='?', required=False, default = 'state', choices=['state', 'charge', 'exit', 'reboot', 'poweroff'], help='request of state and control of remoted T208 (state, charge, exit, reboot, poweroff)')
# parser.add_argument('-i', '--ipaddr', nargs='?', type=str, required=False, default = '127.0.0.1', help='IP address of the remote T208')
parser.add_argument('-r', '--rqst', nargs='?', required=False, default = argparse.SUPPRESS, choices=['state', 'charge', 'exit', 'reboot', 'poweroff'], help='request of state and control of remoted T208 (state, charge, exit, reboot, poweroff)')
parser.add_argument('-i', '--ipaddr', nargs='?', type=str, required=False, default = argparse.SUPPRESS, help='IP address of the remote T208')
if __name__ == '__main__':
    # parser.print_help()
    rqst = 'state'
    ipaddr = '127.0.0.1'
    args = parser.parse_args()
    if not ("rqst" in args) and not ("ipaddr" in args):
        parser.print_help()
    else:
        if ("ipaddr" in args): ipaddr = args.ipaddr
        if ("rqst" in args): rqst = args.rqst

    # send_request (validate_ip(args.ipaddr), args.rqst)
    send_request (validate_ip(ipaddr), rqst)