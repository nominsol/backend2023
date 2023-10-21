#include <arpa/inet.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <string.h>
#include <unistd.h>
#include <iostream>
#include<string>

using namespace std;

int main() {
    int s = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (s < 0) return 1;

    struct sockaddr_in sin;
    memset(&sin, 0, sizeof(sin));
    sin.sin_family = AF_INET;
    sin.sin_port = htons(20150);
    sin.sin_addr.s_addr = inet_addr("127.0.0.1");

    if (bind(s, (struct sockaddr *)&sin, sizeof(sin)) < 0) {
        cerr << strerror(errno) << endl;
        return 0;
    }

    while (true) {
        char buf[65536];
        struct sockaddr_in cli_addr;
        socklen_t cli_addr_len = sizeof(cli_addr);
        
        int numBytes = recvfrom(s, buf, sizeof(buf), 0, (struct sockaddr *)&cli_addr, &cli_addr_len);
        if (numBytes < 0) {
            return 1;
        }

        cout << buf << endl;

        numBytes = sendto(s, buf, numBytes, 0, (struct sockaddr *)&cli_addr, cli_addr_len);
        
        if (numBytes < 0) {
            cerr << "Send error." << endl;
            close(s);
            return 1;
        }
    }

    close(s);
    return 0;
}
